"""Tests for the repository checks under scripts/.

Every test builds a throwaway repo with just the roles it needs and runs one
check against it; nothing touches the real roles/. The Python checks run
in-process through ``main(argv, root)``. The shell scripts cd to the repo root
relative to their own location, so they are copied into
``<tmp>/scripts/<script>`` and run there.
"""
from __future__ import annotations

import contextlib
import importlib
import io
import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

import check_role_structure

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"

GIT = [
    "git",
    "-c", "user.name=test",
    "-c", "user.email=test@example.invalid",
    "-c", "commit.gpgsign=false",
    "-c", "tag.gpgsign=false",
    "-c", "core.hooksPath=/dev/null",
]


class FakeRepo:
    """A minimal ansible-nas checkout in a temporary directory."""

    def __init__(self, root: Path) -> None:
        self.root = root
        (root / "roles").mkdir()
        (root / "scripts").mkdir()

    def write(self, relative: str, content: str) -> Path:
        """Write *content* (dedented) to a repo-relative path."""
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).lstrip("\n"))
        return path

    def role(self, name: str, defaults: str | None = None, tasks: str | None = None,
             molecule: bool = True) -> None:
        """Create a role that follows the standard anatomy unless overridden."""
        flag = name.replace("-", "_").replace(".", "_") + "_enabled"
        if defaults is None:
            defaults = f"""
                ---
                {flag}: false
                {name.replace('-', '_')}_image_name: "vendor/{name}"
                {name.replace('-', '_')}_image_version: "1.0.0"
                """
        if tasks is None:
            tasks = f"""
                ---
                - name: Start
                  block:
                    - name: Container
                      community.docker.docker_container:
                        name: {name}
                        image: "{{{{ x }}}}"
                  when: {flag} is true

                - name: Stop
                  block:
                    - name: Stop
                      community.docker.docker_container:
                        name: {name}
                        state: absent
                  when: {flag} is false
                """
        self.write(f"roles/{name}/defaults/main.yml", defaults)
        self.write(f"roles/{name}/tasks/main.yml", tasks)
        if molecule:
            for file in ("molecule.yml", "side_effect.yml", "verify.yml", "verify_stopped.yml"):
                self.write(f"roles/{name}/molecule/default/{file}", "---\n")

    def run(self, script: str, *args: str, env: dict[str, str] | None = None
            ) -> subprocess.CompletedProcess[str]:
        """Run scripts/<script> against the fake repo."""
        if script.endswith(".py"):
            module = importlib.import_module(script.removesuffix(".py"))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = module.main(list(args), root=self.root)
            return subprocess.CompletedProcess([script, *args], code, out.getvalue(), "")
        target = self.root / "scripts" / script
        shutil.copy2(SCRIPTS_DIR / script, target)
        return subprocess.run(
            [str(target), *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, **(env or {})},
        )

    def git(self, *args: str) -> None:
        """Run a git command in the fake repo."""
        subprocess.run([*GIT, *args], cwd=self.root, check=True, capture_output=True)


@pytest.fixture(name="repo")
def fixture_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeRepo:
    """An empty fake repository, with no structure exemptions."""
    for name in ("NO_MOLECULE", "NO_DEFAULTS", "NO_ENABLED_FLAG", "NO_START_STOP_BLOCK",
                 "UNCONVENTIONAL_FLAG"):
        monkeypatch.setattr(check_role_structure, name, ())
    return FakeRepo(tmp_path)


# --- check_port_conflicts.py -------------------------------------------------


def test_ports_no_conflict(repo: FakeRepo) -> None:
    """Distinct ports pass."""
    repo.write("roles/a/defaults/main.yml", 'a_port: "8001"\n')
    repo.write("roles/b/defaults/main.yml", 'b_port: "8002"\n')
    result = repo.run("check_port_conflicts.py")
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("value", ['"8080"', "'8080'", "8080", "8080  # web UI"])
def test_ports_conflict_regardless_of_quoting(repo: FakeRepo, value: str) -> None:
    """An unquoted or single-quoted port clashes just like a double-quoted one."""
    repo.write("roles/a/defaults/main.yml", 'a_port: "8080"\n')
    repo.write("roles/b/defaults/main.yml", f"b_port_http: {value}\n")
    result = repo.run("check_port_conflicts.py")
    assert result.returncode == 1
    assert "port 8080" in result.stdout and " a b" in result.stdout


def test_ports_ignore_templated_and_same_role(repo: FakeRepo) -> None:
    """Jinja values are skipped, and one role reusing its own port is no clash."""
    repo.write("roles/a/defaults/main.yml", 'a_port: "8080"\na_port_ui: "8080"\n')
    repo.write("roles/b/defaults/main.yml", 'b_port: "{{ a_port }}"\n')
    result = repo.run("check_port_conflicts.py")
    assert result.returncode == 0, result.stdout


# --- check_enabled_vars.py --------------------------------------------------


def test_enabled_vars_pass(repo: FakeRepo) -> None:
    """A role referring only to its own flag passes."""
    repo.role("alpha")
    result = repo.run("check_enabled_vars.py")
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize(
    "condition",
    [
        "when: alpha_enabled is false or typo_enabled is false",
        "when:\n    - alpha_enabled is true\n    - typo_enabled is true",
        'when: "{{ typo_enabled }}"',
    ],
    ids=["compound", "list-form", "jinja"],
)
def test_enabled_vars_catch_every_reference(repo: FakeRepo, condition: str) -> None:
    """An undefined flag is caught wherever the condition names it."""
    repo.role("alpha")
    repo.write(
        "roles/alpha/tasks/extra.yml",
        f"---\n- name: X\n  ansible.builtin.debug:\n  {condition}\n",
    )
    result = repo.run("check_enabled_vars.py")
    assert result.returncode == 1
    assert "'typo_enabled'" in result.stdout


def test_enabled_vars_skip_attributes_keys_and_comments(repo: FakeRepo) -> None:
    """item.x_enabled, a `x_enabled: true` var and a comment are not references."""
    repo.role("alpha")
    repo.write(
        "roles/alpha/tasks/extra.yml",
        """
        ---
        # nothing_enabled is mentioned in prose only
        - name: X
          ansible.builtin.include_role:
            name: other
          vars:
            other_enabled: true
          when: item.phpmyadmin_enabled | default(false)
        """,
    )
    result = repo.run("check_enabled_vars.py")
    assert result.returncode == 0, result.stdout


# --- check_role_structure.py ------------------------------------------------


def test_structure_pass(repo: FakeRepo) -> None:
    """A role copied from the template passes."""
    repo.role("alpha")
    result = repo.run("check_role_structure.py")
    assert result.returncode == 0, result.stdout


def test_structure_reports_missing_pieces(repo: FakeRepo) -> None:
    """Missing molecule files, a wrong flag name and a meta/ dir are reported."""
    repo.role(
        "alpha",
        defaults='---\nbeta_enabled: false\nalpha_image_name: "x/y"\nalpha_image_version: "1"\n',
        molecule=False,
    )
    repo.write("roles/alpha/meta/main.yml", "---\n")
    result = repo.run("check_role_structure.py")
    assert result.returncode == 1
    assert "missing molecule/default/molecule.yml" in result.stdout
    assert "should be 'alpha_enabled'" in result.stdout
    assert "meta/" in result.stdout


def test_structure_reports_missing_stop_block(repo: FakeRepo) -> None:
    """A role that never removes its container when disabled is reported."""
    repo.role(
        "alpha",
        tasks="""
        ---
        - name: Start
          community.docker.docker_container:
            name: alpha
            image: "{{ alpha_image_name }}:{{ alpha_image_version }}"
          when: alpha_enabled is true
        """,
    )
    result = repo.run("check_role_structure.py")
    assert result.returncode == 1
    assert "'when: alpha_enabled is false' stop block" in result.stdout


@pytest.mark.parametrize("image", ["postgres:16", '"postgres:16"', "'postgres:16'"])
def test_structure_reports_hardcoded_image(repo: FakeRepo, image: str) -> None:
    """A literal image in tasks is reported whether or not it is quoted."""
    repo.role("alpha")
    repo.write(
        "roles/alpha/tasks/db.yml",
        "---\n- name: Db\n  community.docker.docker_container:\n"
        f"    name: db\n    image: {image}\n",
    )
    result = repo.run("check_role_structure.py")
    assert result.returncode == 1
    assert "tasks hardcode an image (postgres:16)" in result.stdout


def test_structure_reports_unpinned_image(repo: FakeRepo) -> None:
    """An _image_name with no _image_version next to it is reported."""
    repo.role("alpha", defaults='---\nalpha_enabled: false\nalpha_image_name: "x/y"\n')
    result = repo.run("check_role_structure.py")
    assert result.returncode == 1
    assert "alpha_image_name has no alpha_image_version pin" in result.stdout


# --- check-roles-md.sh ------------------------------------------------------


def test_roles_md_absent_is_skipped(repo: FakeRepo) -> None:
    """Without the local-only ROLES.md the check passes."""
    repo.role("alpha")
    result = repo.run("check-roles-md.sh")
    assert result.returncode == 0
    assert "skipping" in result.stdout


def test_roles_md_in_sync(repo: FakeRepo) -> None:
    """A role on an 'Already covered' line, and existing roles under Replacements, pass."""
    repo.role("alpha")
    repo.role("hello_world")
    repo.write(
        "ROLES.md",
        """
        ## Media

        | Name | Why |
        | --- | --- |
        | `newapp` | candidate |

        Already covered: `alpha`.

        ## Replacements and upstream health

        | `alpha` | fine |
        """,
    )
    result = repo.run("check-roles-md.sh")
    assert result.returncode == 0, result.stdout


def test_roles_md_out_of_sync(repo: FakeRepo) -> None:
    """A role missing from the doc, or still offered as a candidate, is reported."""
    repo.role("alpha")
    repo.role("beta")
    repo.write("ROLES.md", "## Media\n\n| `alpha` | candidate |\n")
    result = repo.run("check-roles-md.sh")
    assert result.returncode == 1
    assert "roles/alpha: still listed as a candidate" in result.stdout
    assert "roles/beta: not mentioned" in result.stdout


# --- github-test-matrix.sh --------------------------------------------------


def test_matrix_lists_roles_with_molecule(repo: FakeRepo, tmp_path: Path) -> None:
    """Outside a PR every role with a molecule scenario is tested."""
    if shutil.which("jq") is None:
        pytest.skip("jq not installed")
    repo.role("alpha")
    repo.role("beta", molecule=False)
    output = tmp_path / "github_output"
    result = repo.run(
        "github-test-matrix.sh",
        env={"GITHUB_EVENT_NAME": "schedule", "GITHUB_OUTPUT": str(output)},
    )
    assert result.returncode == 0, result.stderr
    assert output.read_text() == 'matrix=["roles/alpha"]\n'


def test_matrix_runs_without_github_output(repo: FakeRepo) -> None:
    """A local dry run without GITHUB_OUTPUT prints the matrix instead of failing."""
    if shutil.which("jq") is None:
        pytest.skip("jq not installed")
    repo.role("alpha")
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_OUTPUT", "GITHUB_EVENT_NAME")}
    target = repo.root / "scripts" / "github-test-matrix.sh"
    shutil.copy2(SCRIPTS_DIR / "github-test-matrix.sh", target)
    result = subprocess.run([str(target)], cwd=repo.root, env=env, capture_output=True,
                            text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert '["roles/alpha"]' in result.stdout


# --- check_breaking_changes.py ----------------------------------------------

BASE_DEFAULTS = """
    ---
    alpha_enabled: false
    alpha_port: "8080"
    alpha_data_directory: "{{ docker_home }}/alpha"
    alpha_config_directory: "{{ docker_home }}/alpha/config"
    alpha_image_name: "vendor/alpha"
    alpha_image_version: "1.4.2"
    alpha_side_image: "vendor/side:2.0.0"
    alpha_memory: 1g
    """


@pytest.fixture(name="released")
def fixture_released(repo: FakeRepo) -> FakeRepo:
    """A repo with roles alpha and beta, tagged v1.0.0."""
    repo.role("alpha", defaults=BASE_DEFAULTS)
    repo.role("beta")
    repo.write("CHANGELOG.md", "# Changelog\n\n## Unreleased\n\n## v1.0.0\n\n- `alpha` — old\n")
    repo.git("init", "-q")
    repo.git("add", "-A")
    repo.git("commit", "-q", "-m", "init")
    repo.git("tag", "v1.0.0")
    return repo


def _edit_defaults(repo: FakeRepo, old: str, new: str) -> None:
    path = repo.root / "roles/alpha/defaults/main.yml"
    text = path.read_text()
    assert old in text
    path.write_text(text.replace(old, new))


def test_breaking_no_tag(repo: FakeRepo) -> None:
    """Without a release tag there is nothing to compare against."""
    repo.role("alpha")
    repo.git("init", "-q")
    result = repo.run("check_breaking_changes.py")
    assert result.returncode == 0
    assert "No release tag" in result.stdout


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ('alpha_port: "8080"', "alpha_port: 8080"),
        ('alpha_port: "8080"', "alpha_port: '8080'  # web UI"),
        ("alpha_memory: 1g", "alpha_memory: 2g"),
        ('alpha_image_version: "1.4.2"', 'alpha_image_version: "1.9.0"'),
        ('"vendor/side:2.0.0"', '"vendor/side:2.3.1"'),
        ('alpha_image_version: "1.4.2"', 'alpha_image_version: "2026.01.01"'),
    ],
    ids=["requoted", "single-quoted-comment", "memory", "minor-bump", "embedded-minor",
         "date-pin"],
)
def test_breaking_ignores_safe_changes(released: FakeRepo, old: str, new: str) -> None:
    """Quoting, non-location settings and same-major bumps are not breaking."""
    _edit_defaults(released, old, new)
    result = released.run("check_breaking_changes.py")
    assert result.returncode == 0, result.stdout
    assert "No breaking changes" in result.stdout


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        ('alpha_port: "8080"', 'alpha_port: "8081"', "'alpha_port' default changed"),
        ('alpha_data_directory: "{{ docker_home }}/alpha"',
         'alpha_data_directory: "{{ docker_home }}/alpha2"',
         "'alpha_data_directory' default changed"),
        ('alpha_config_directory: "{{ docker_home }}/alpha/config"',
         'alpha_config_directory: "{{ docker_home }}/alpha/cfg"',
         "'alpha_config_directory' default changed"),
        ("alpha_memory: 1g\n", "", "'alpha_memory' deleted"),
        ('alpha_image_version: "1.4.2"', 'alpha_image_version: "v2.0.0"',
         "'alpha_image_version' major image bump 1.4.2 -> v2.0.0"),
        ('"vendor/side:2.0.0"', '"vendor/side:3.0.0"',
         "'alpha_side_image' major image bump 2.0.0 -> 3.0.0"),
    ],
    ids=["port", "data-dir", "config-dir", "deleted-key", "major-bump", "embedded-major"],
)
def test_breaking_reports_unrecorded(released: FakeRepo, old: str, new: str,
                                     expected: str) -> None:
    """A breaking change with no Unreleased changelog entry fails the check."""
    _edit_defaults(released, old, new)
    result = released.run("check_breaking_changes.py")
    assert result.returncode == 1
    assert f"roles/alpha: defaults/main.yml: {expected}" in result.stdout


def test_breaking_reports_removed_role(released: FakeRepo) -> None:
    """A removed role is reported as removed or renamed."""
    shutil.rmtree(released.root / "roles/beta")
    result = released.run("check_breaking_changes.py")
    assert result.returncode == 1
    assert "roles/beta: role removed or renamed" in result.stdout


def test_breaking_reports_deleted_defaults_file(released: FakeRepo) -> None:
    """Deleting defaults/main.yml deletes every key in it."""
    (released.root / "roles/alpha/defaults/main.yml").unlink()
    result = released.run("check_breaking_changes.py")
    assert result.returncode == 1
    assert "'alpha_enabled' deleted" in result.stdout


def test_breaking_recorded_in_unreleased(released: FakeRepo) -> None:
    """An Unreleased bullet naming the role in backticks records the break."""
    _edit_defaults(released, 'alpha_port: "8080"', 'alpha_port: "8081"')
    released.write(
        "CHANGELOG.md",
        "# Changelog\n\n## Unreleased\n\n### Breaking\n\n- `alpha` — port moved\n\n"
        "## v1.0.0\n",
    )
    result = released.run("check_breaking_changes.py")
    assert result.returncode == 0, result.stdout
    assert "recorded in CHANGELOG.md" in result.stdout


def test_breaking_entry_under_old_release_does_not_count(released: FakeRepo) -> None:
    """A bullet under an already released version does not record a new break."""
    _edit_defaults(released, 'alpha_port: "8080"', 'alpha_port: "8081"')
    result = released.run("check_breaking_changes.py")
    assert result.returncode == 1


def test_breaking_explicit_base(released: FakeRepo) -> None:
    """A tag passed as the first argument is used as the base."""
    released.git("tag", "v0.9.0")
    result = released.run("check_breaking_changes.py", "v0.9.0")
    assert result.returncode == 0
    assert "since v0.9.0" in result.stdout


# --- check_role_structure.py exemptions -------------------------------------


def test_structure_reports_exemption_for_missing_role(repo: FakeRepo,
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    """An exemption naming a role that no longer exists fails."""
    repo.role("alpha")
    monkeypatch.setattr(check_role_structure, "NO_MOLECULE", ("gone",))
    result = repo.run("check_role_structure.py")
    assert result.returncode == 1
    assert "NO_MOLECULE: 'gone' is not a role any more" in result.stdout


def test_structure_reports_exemption_no_longer_needed(repo: FakeRepo,
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    """An exemption for a role that now follows the convention fails."""
    repo.role("alpha")
    monkeypatch.setattr(check_role_structure, "NO_MOLECULE", ("alpha",))
    monkeypatch.setattr(check_role_structure, "NO_START_STOP_BLOCK", ("alpha",))
    result = repo.run("check_role_structure.py")
    assert result.returncode == 1
    assert "NO_MOLECULE: 'alpha' now follows the convention" in result.stdout
    assert "NO_START_STOP_BLOCK: 'alpha' now follows the convention" in result.stdout


def test_structure_exemption_still_needed(repo: FakeRepo,
                                          monkeypatch: pytest.MonkeyPatch) -> None:
    """A role that still deviates keeps its exemption without complaint."""
    repo.role("alpha", molecule=False)
    monkeypatch.setattr(check_role_structure, "NO_MOLECULE", ("alpha",))
    result = repo.run("check_role_structure.py")
    assert result.returncode == 0, result.stdout


def test_real_repo_structure_passes() -> None:
    """The real roles, with the real exemption lists, pass the structure check."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert check_role_structure.main([]) == 0, out.getvalue()


# --- github-test-matrix.sh on pull requests ---------------------------------


@pytest.mark.parametrize(
    ("changed", "expected"),
    [
        ("roles/alpha/tasks/main.yml", '["roles/alpha"]'),
        ("roles/beta/defaults/main.yml", "[]"),
        ("tests/molecule/base.yml", '["roles/alpha","roles/gamma"]'),
        ("requirements-dev.txt", '["roles/alpha","roles/gamma"]'),
        ("README.md", "[]"),
    ],
    ids=["one-role", "role-without-molecule", "shared-config", "requirements", "unrelated"],
)
def test_matrix_on_pull_request(repo: FakeRepo, tmp_path: Path, changed: str,
                                expected: str) -> None:
    """A PR tests the roles it touches, or all of them when shared pins change."""
    if shutil.which("jq") is None:
        pytest.skip("jq not installed")
    repo.role("alpha")
    repo.role("beta", molecule=False)
    repo.role("gamma")
    repo.write("requirements-dev.txt", "molecule==1\n")
    repo.write("tests/molecule/base.yml", "---\n")
    repo.git("init", "-q")
    repo.git("add", "-A")
    repo.git("commit", "-q", "-m", "base")
    repo.git("update-ref", "refs/remotes/origin/main", "HEAD")
    path = repo.root / changed
    path.write_text(path.read_text() + "# changed\n" if path.exists() else "changed\n")
    repo.git("add", "-A")
    repo.git("commit", "-q", "-m", "change")
    output = tmp_path / "github_output"
    result = repo.run(
        "github-test-matrix.sh",
        env={"GITHUB_EVENT_NAME": "pull_request", "GITHUB_BASE_REF": "main",
             "GITHUB_OUTPUT": str(output)},
    )
    assert result.returncode == 0, result.stderr
    assert output.read_text() == f"matrix={expected}\n"
