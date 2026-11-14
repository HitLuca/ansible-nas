"""Unit tests for the tag parsing and comparison in check_image_versions.py.

Every tag in these tables is one the roles actually pin, or one a registry
really publishes, so a parser change breaks a test instead of silently
rewriting a role's defaults with ``--patch``.
"""
# pylint: disable=protected-access  # the leading-underscore helpers are the units under test
from pathlib import Path

import pytest

import check_image_versions as civ
import role_defaults


def _tag(text: str) -> civ.Tag:
    """Parse *text*, asserting it is a comparable version tag."""
    parsed = civ._parse_tag(text)
    assert isinstance(parsed, civ.Tag)
    return parsed


def _ref(version: str) -> civ.ImageRef:
    """An ImageRef for a made-up role pinning *version*."""
    return civ.ImageRef(
        role="example",
        path=Path("roles/example/defaults/main.yml"),
        repo_key="example_image_name",
        version_key="example_image_version",
        repo="example/example",
        version=version,
        line=1,
    )


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        ("1.43.5", ("", (1, 43, 5), 0, "", 0)),
        ("v1.5.939", ("", (1, 5, 939), 0, "", 0)),
        ("3.08.00", ("", (3, 8, 0), 0, "", 0)),
        ("2026.11.1", ("", (2026, 11, 1), 0, "", 0)),
        ("20.04-tools", ("", (20, 4), 0, "tools", 0)),
        ("version-v2201.1.0", ("version-", (2201, 1, 0), 0, "", 0)),
        ("v26.3-ls271", ("", (26, 3), 0, "ls", 271)),
        ("2026-07-14c-ls333", ("", (2026, 7, 14), 3, "ls", 333)),
        ("12.4ubu2604-ls59", ("", (12, 4), 0, "ubu2604ls", 59)),
        ("19.5.4-ce.0", ("", (19, 5, 4), 0, "ce", 0)),
        ("develop-0.1.0.768-ls12", ("develop-", (0, 1, 0, 768), 0, "ls", 12)),
        ("2.1.0-rc.2", ("", (2, 1, 0), 0, "rc", 2)),
    ],
)
def test_parse_tag(tag: str, expected: tuple) -> None:
    """A version tag splits into prefix, parts, revision, shape and build."""
    parsed = _tag(tag)
    actual = (parsed.prefix, parsed.parts, parsed.revision, parsed.variant, parsed.build)
    assert actual == expected


@pytest.mark.parametrize(
    ("tag", "status"),
    [
        ("beta", "channel"),
        ("mini", "channel"),
        ("alpine", "channel"),
        ("version-94dcfd13", "commit"),
        ("14-vectorchord0.3.0-pgvectors0.2.0", "composite"),
        ("14-vectorchord0.4.1", "composite"),
        ("!!!", "unrecognized"),
    ],
)
def test_unversioned_status(tag: str, status: str) -> None:
    """Channel, commit and composite tags are classified, not parsed."""
    parsed = civ._parse_tag(tag)
    assert isinstance(parsed, civ.Unversioned)
    assert parsed.status == status


@pytest.mark.parametrize(
    ("current", "candidate"),
    [
        ("2026-07-14c-ls333", "2026-07-14c-ls334"),
        ("2026-07-14c-ls333", "2026-07-14d-ls1"),
        ("19.5.4-ce.0", "19.5.5-ce.0"),
        ("v26.3-ls271", "v26.3-ls272"),
        ("2026.11.1", "2026.12.0"),
        ("2.1.0-rc.2", "2.1.0-rc.3"),
    ],
)
def test_acceptable_upgrade(current: str, candidate: str) -> None:
    """A newer tag of the same shape is accepted."""
    assert civ._acceptable(_tag(current), _tag(candidate), allow_major=False)


@pytest.mark.parametrize(
    ("current", "candidate"),
    [
        ("12.4ubu2604-ls59", "12.1ubu2604-ls50"),
        ("12.4ubu2604-ls59", "12.4ubu2404-ls99"),
        ("19.5.4-ce.0", "19.5.5-ee.0"),
        ("develop-0.1.0.768-ls12", "nightly-0.1.0.816-ls118"),
        ("2026-07-14c-ls333", "version-2026-07-14c"),
        ("2.1.0-rc.2", "2.2.0"),
        ("1.5.939", "2.0.0"),
    ],
)
def test_rejects_upgrade(current: str, candidate: str) -> None:
    """Older, differently shaped, channel-changing or major tags are rejected."""
    assert not civ._acceptable(_tag(current), _tag(candidate), allow_major=False)


def test_hub_credentials_use_the_shared_variables(monkeypatch) -> None:
    """The Docker Hub credentials are the ones scan_images.py already reads."""
    monkeypatch.setenv("DOCKERHUB_USERNAME", "user")
    monkeypatch.setenv("DOCKERHUB_TOKEN", "s3cret")
    assert civ._hub_credentials() == ("user", "s3cret")


@pytest.mark.parametrize(
    "environment",
    [{}, {"DOCKERHUB_USERNAME": "user"}, {"DOCKERHUB_TOKEN": "s3cret"}],
)
def test_hub_credentials_absent_when_incomplete(monkeypatch, environment: dict) -> None:
    """A username without a token queries anonymously instead of sending a blank password."""
    for name in ("DOCKERHUB_USERNAME", "DOCKERHUB_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    assert civ._hub_credentials() is None


def test_best_match_picks_highest() -> None:
    """The newest rebuild wins, ignoring other channels and floating tags."""
    tags = ["2026-07-14c-ls332", "2026-07-14c-ls334", "2025-05-14b-ls308", "latest"]
    assert civ._best_match(_tag("2026-07-14c-ls333"), tags, False) == "2026-07-14c-ls334"


@pytest.mark.parametrize(
    ("page", "expected"),
    [
        (civ.TagPage(["1.9.9"], complete=False), "update"),
        (civ.TagPage(["1.2.3", "1.9.9"], complete=False), "update"),
        (civ.TagPage(["1.2.3"], complete=False), "ok"),
        (civ.TagPage(["1.9.9"], complete=True), "update"),
        (civ.TagPage(["1.2.3"], complete=True), "ok"),
        (civ.TagPage([], complete=True), "ok"),
    ],
)
def test_evaluate_uses_truncation(page: civ.TagPage, expected: str) -> None:
    """A newest-first page proves the pin current once the pin is on it."""
    ref = _ref("1.2.3")
    assert civ._evaluate(ref, {ref.repo: page}, {}, allow_major=False).status == expected


def test_evaluate_flags_missing_pin_on_truncated_page() -> None:
    """A pin absent from a truncated page is not reported as current."""
    ref = _ref("1.2.3")
    page = civ.TagPage(["0.9.0"], complete=False)
    result = civ._evaluate(ref, {ref.repo: page}, {}, allow_major=False)
    assert result.status == "truncated"
    assert result.detail


def test_evaluate_lexical_page_does_not_prove_current() -> None:
    """On a truncated lexically sorted page (ghcr.io) finding the pin proves nothing."""
    ref = _ref("1.2.3")
    page = civ.TagPage(["1.0.0", "1.2.3"], complete=False, newest_first=False)
    assert civ._evaluate(ref, {ref.repo: page}, {}, allow_major=False).status == "truncated"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("linuxserver/heimdall:2.8.4", ("linuxserver/heimdall", "2.8.4")),
        ("postgres", ("postgres", "")),
        ("registry.local:5000/app", ("registry.local:5000/app", "")),
        ("registry.local:5000/app:1.0", ("registry.local:5000/app", "1.0")),
    ],
)
def test_split_repo_tag(value: str, expected: tuple[str, str]) -> None:
    """A registry port is not mistaken for a tag."""
    assert role_defaults.split_repo_tag(value) == expected


@pytest.mark.parametrize(
    ("repo", "expected"),
    [
        ("vendor/app", ("docker.io", "vendor/app")),
        ("ghcr.io/vendor/app", ("ghcr.io", "vendor/app")),
        ("localhost/app", ("localhost", "app")),
        ("postgres", ("docker.io", "postgres")),
    ],
)
def test_split_host(repo: str, expected: tuple[str, str]) -> None:
    """A bare namespace/name defaults to Docker Hub."""
    assert civ.split_host(repo) == expected


def _write_role(tmp_path: Path, text: str) -> role_defaults.Role:
    path = tmp_path / "example"
    (path / "defaults").mkdir(parents=True)
    (path / "defaults" / "main.yml").write_text(text)
    defaults = role_defaults.load_defaults(path / "defaults" / "main.yml")
    return role_defaults.Role("example", path, defaults)


def test_refs_in_role(tmp_path: Path) -> None:
    """Paired pins, embedded tags and templated names are all handled."""
    role = _write_role(
        tmp_path,
        "---\n"
        'example_image_name: "vendor/app"\n'
        'example_image_version: "1.2.3"  # pinned\n'
        "example_db_image: postgres:16.4\n"
        'example_proxy_image: "{{ example_image_name }}"\n',
    )
    refs = {ref.repo_key: ref for ref in civ._refs_in_role(role)}
    assert set(refs) == {"example_image_name", "example_db_image"}
    assert (refs["example_image_name"].version, refs["example_image_name"].line) == ("1.2.3", 3)
    assert refs["example_image_name"].version_key == "example_image_version"
    assert (refs["example_db_image"].repo, refs["example_db_image"].version) == ("postgres", "16.4")


def test_patch_rewrites_pins_and_keeps_quotes(tmp_path: Path, monkeypatch) -> None:
    """--patch keeps each line's quoting and comment, and skips a pin it cannot place."""
    monkeypatch.setattr(civ, "REPO_ROOT", tmp_path)
    role = _write_role(
        tmp_path,
        "---\n"
        "example_image_name: vendor/app\n"
        "example_image_version: '1.2.3'  # pinned\n"
        "example_db_image: postgres:16.4\n",
    )
    refs = {ref.repo_key: ref for ref in civ._refs_in_role(role)}
    results = [
        civ.Result(refs["example_image_name"], "update", latest="1.3.0"),
        civ.Result(refs["example_db_image"], "update", latest="16.5"),
    ]
    changes = civ.patch(results)
    text = role.defaults_path.read_text()
    assert "example_image_version: '1.3.0'  # pinned\n" in text
    assert "example_db_image: postgres:16.5\n" in text
    assert len(changes) == 2


def test_patch_does_not_report_a_change_it_did_not_make(tmp_path: Path, monkeypatch,
                                                        capsys) -> None:
    """A pin edited since discovery is reported as unpatched, not as patched."""
    monkeypatch.setattr(civ, "REPO_ROOT", tmp_path)
    role = _write_role(
        tmp_path, "---\nexample_image_name: vendor/app\nexample_image_version: 1.2.3\n"
    )
    ref = civ._refs_in_role(role)[0]
    role.defaults_path.write_text(
        "---\nexample_image_name: vendor/app\nexample_image_version: 9.9.9\n"
    )
    assert not civ.patch([civ.Result(ref, "update", latest="1.3.0")])
    assert "could not patch" in capsys.readouterr().err


class _Response:
    """A stand-in for the object urlopen returns."""

    def __init__(self, body: bytes) -> None:
        self.body = body
        self.headers = {"Content-Type": "text/html"}

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        """The response body."""
        return self.body


def test_fetch_non_json_is_a_registry_error(monkeypatch) -> None:
    """An HTML page answering 200 fails one repository, not the whole run."""
    monkeypatch.setattr(civ.urllib.request, "urlopen",
                        lambda *_args, **_kwargs: _Response(b"<html>login</html>"))
    with pytest.raises(civ.RegistryError, match="non-JSON"):
        civ._fetch("https://registry.invalid/v2/tags")


def test_fetch_all_reports_errors_per_repo(monkeypatch) -> None:
    """A failing repository lands in errors while the others still resolve."""
    def fake(repo: str) -> civ.TagPage:
        if repo == "bad/repo":
            raise civ.RegistryError("HTTP 404", 404)
        return civ.TagPage(["1.0.0"], complete=True)

    monkeypatch.setattr(civ, "fetch_tags", fake)
    tags, errors = civ._fetch_all(["bad/repo", "good/repo"], jobs=2)
    assert list(tags) == ["good/repo"]
    assert errors == {"bad/repo": "HTTP 404"}
