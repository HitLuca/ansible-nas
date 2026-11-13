"""Unit tests for the tag parsing and comparison in check_image_versions.py.

Every tag in these tables is one the roles actually pin, or one a registry
really publishes, so a parser change breaks a test instead of silently
rewriting a role's defaults with ``--patch``.
"""
# pylint: disable=protected-access  # the leading-underscore helpers are the units under test
from pathlib import Path

import pytest

import check_image_versions as civ


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
