"""Run each role's molecule scenario as a pytest test, so VS Code's Testing
panel can run all roles or just a selection. Mirrors the CI step:
    cd roles/<role> && molecule --base-config ../../tests/molecule/base.yml test

The idempotence step is skipped on macOS unless ANSIBLE_NAS_SKIP_IDEMPOTENCE=0;
see SKIP_IDEMPOTENCE below for why.

Roles start their containers through the host's docker socket, so they are
siblings of the molecule instance and `molecule destroy` never removes them.
After each test we remove the containers that appeared during it AND whose
name is a *_container_name from the role's defaults. Any other new container
(e.g. one you started yourself meanwhile) is left alone and reported.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import warnings
from pathlib import Path

import pytest

import role_defaults

REPO = Path(__file__).resolve().parent.parent
# docker_home in tests/molecule/base.yml, shared between host and instance
SHARED = Path("/tmp/ansible-nas")
ROLES = sorted(p.parent for p in (REPO / "roles").glob("*/molecule"))
BASE_CONFIG = REPO / "tests" / "molecule" / "base.yml"
# Docker Desktop stores a single-file bind source as /host_mnt/..., so the
# second converge always looks changed and the idempotence step fails for
# roles that bind a file. That is macOS-only; CI runs on native Linux, where
# the full sequence (idempotence included) always runs. Set
# ANSIBLE_NAS_SKIP_IDEMPOTENCE=0 to force the step locally.
SKIP_IDEMPOTENCE = os.environ.get(
    "ANSIBLE_NAS_SKIP_IDEMPOTENCE", "1" if sys.platform == "darwin" else "0"
) == "1"


def _base_config(tmpdir: Path) -> str:
    """The --base-config to hand molecule.

    With ANSIBLE_NAS_SKIP_IDEMPOTENCE=1 this is a copy of base.yml with the
    idempotence step removed; it is derived from base.yml so the sequence
    stays defined in one place.
    """
    if not SKIP_IDEMPOTENCE:
        return "../../tests/molecule/base.yml"
    stripped = "".join(
        line
        for line in BASE_CONFIG.read_text(encoding="utf-8").splitlines(keepends=True)
        if line.strip() != "- idempotence"
    )
    path = tmpdir / "base.yml"
    path.write_text(stripped, encoding="utf-8")
    return str(path)


def _containers() -> dict[str, str]:
    """Return {container id: name} for every container, running or not."""
    out = subprocess.run(
        ["docker", "ps", "-a", "--no-trunc", "--format", "{{.ID}} {{.Names}}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return dict(line.split(" ", 1) for line in out.splitlines() if line)


def _container_names(role: Path) -> set[str]:
    """Literal *_container_name values from the role's defaults."""
    defaults = role_defaults.load_defaults(role / "defaults" / "main.yml")
    return {
        entry.text
        for key, entry in defaults.items()
        if key.endswith("_container_name") and entry.text and "{{" not in entry.text
    }


def test_base_config_default_keeps_sequence(tmp_path, monkeypatch):
    """Without the flag, molecule gets the real base config."""
    monkeypatch.setitem(globals(), "SKIP_IDEMPOTENCE", False)
    assert _base_config(tmp_path) == "../../tests/molecule/base.yml"


def test_base_config_strips_only_idempotence(tmp_path, monkeypatch):
    """With the flag, the copy differs from base.yml by the idempotence line."""
    monkeypatch.setitem(globals(), "SKIP_IDEMPOTENCE", True)
    original = BASE_CONFIG.read_text(encoding="utf-8").splitlines()
    stripped = Path(_base_config(tmp_path)).read_text(encoding="utf-8").splitlines()
    assert stripped == [line for line in original if line.strip() != "- idempotence"]


@pytest.mark.parametrize("role", ROLES, ids=lambda p: p.name)
def test_role(role: Path):
    """Run the role's molecule scenario and clean up its containers."""
    shutil.rmtree(SHARED, ignore_errors=True)  # no state from earlier runs
    before = set(_containers())
    # Use the tools from the interpreter running pytest (the uv environment).
    bin_dir = str(Path(sys.executable).parent)
    env = {
        **os.environ,
        "PATH": bin_dir + os.pathsep + os.environ.get("PATH", ""),
        "PY_COLORS": "0",
        "ANSIBLE_FORCE_COLOR": "0",
    }
    tmpdir = Path(tempfile.mkdtemp())
    try:
        result = subprocess.run(
            ["molecule", "--base-config", _base_config(tmpdir), "test"],
            cwd=role,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
        shutil.rmtree(SHARED, ignore_errors=True)
        mine = _container_names(role)
        new = {i: n for i, n in _containers().items() if i not in before}
        ours = [i for i, n in new.items() if n in mine]
        if ours:
            subprocess.run(
                ["docker", "rm", "-f", *ours], capture_output=True, check=False
            )
        others = sorted(n for i, n in new.items() if i not in ours)
        if others:
            warnings.warn(f"left alone (not in {role.name} defaults): {others}")
    assert result.returncode == 0, result.stdout[-6000:] + result.stderr[-3000:]
