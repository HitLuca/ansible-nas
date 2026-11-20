"""Unit tests for role_defaults.py, the defaults loader every check shares."""

from pathlib import Path

import pytest

import role_defaults as rd

DEFAULTS = """\
---
# comment
example_enabled: false
example_port: 8080
example_ui_port: "8081"   # quoted
example_old_port: '8082'
example_image_name: vendor/app
example_image_version: 3.10
example_list:
  - a
  - b
example_empty:
example_memory: 1g
"""


def test_parse_keeps_value_text_and_line() -> None:
    """Values load as YAML; text keeps the scalar as written, minus quotes and comments."""
    entries = rd.parse_defaults(DEFAULTS)
    assert entries["example_port"] == rd.Entry(8080, "8080", 4)
    assert entries["example_ui_port"] == rd.Entry("8081", "8081", 5)
    assert entries["example_old_port"].text == "8082"
    # 3.10 loads as the float 3.1, but the text a version check needs is "3.10".
    assert entries["example_image_version"].value == pytest.approx(3.1)
    assert entries["example_image_version"].text == "3.10"
    assert entries["example_list"] == rd.Entry(["a", "b"], "", 9)
    assert entries["example_empty"].text == ""
    assert list(entries)[0] == "example_enabled"


@pytest.mark.parametrize("text", ["", "---\n", "# only a comment\n"])
def test_parse_empty(text: str) -> None:
    """An empty defaults file has no keys."""
    assert not rd.parse_defaults(text)


@pytest.mark.parametrize("text", ["- a\n- b\n", "key: [unclosed\n"])
def test_parse_rejects_non_mapping(text: str) -> None:
    """A list or broken YAML raises with the file named."""
    with pytest.raises(rd.DefaultsError, match="somewhere.yml"):
        rd.parse_defaults(text, "somewhere.yml")


def test_load_missing_file(tmp_path: Path) -> None:
    """A role without defaults/main.yml has no keys rather than an error."""
    assert not rd.load_defaults(tmp_path / "nope.yml")


def _role(root: Path, name: str, defaults: str | None) -> None:
    (root / "roles" / name / "tasks").mkdir(parents=True)
    if defaults is not None:
        (root / "roles" / name / "defaults").mkdir()
        (root / "roles" / name / "defaults" / "main.yml").write_text(defaults)


def test_discover(tmp_path: Path) -> None:
    """Every role directory is found, sorted, with or without defaults."""
    _role(tmp_path, "speedtest-tracker", "---\nspeedtest_tracker_enabled: false\n")
    _role(tmp_path, "ansible-nas-users", None)
    (tmp_path / "roles" / "README.md").write_text("not a role")
    roles = rd.discover(tmp_path)
    assert [role.name for role in roles] == ["ansible-nas-users", "speedtest-tracker"]
    assert not roles[0].defaults
    assert roles[1].flag == roles[1].conventional_flag == "speedtest_tracker_enabled"
    assert [role.name for role in rd.discover(tmp_path, ["speedtest-tracker"])] == [
        "speedtest-tracker"
    ]


def test_conventional_flag_replaces_dots_and_dashes() -> None:
    """healthchecks.io and dashed names map to an identifier."""
    assert (
        rd.Role("healthchecks.io", Path("x")).conventional_flag
        == "healthchecks_io_enabled"
    )


def test_version_key_prefers_image_version() -> None:
    """_image_version wins over _image_tag; neither gives None."""
    entries = rd.parse_defaults(
        "a_image_tag: '1'\na_image_version: '2'\nb_image_name: x\n"
    )
    assert rd.version_key(entries, "a") == "a_image_version"
    assert rd.version_key(entries, "b") is None


def test_real_roles_parse() -> None:
    """Every role in the repository has loadable defaults."""
    roles = rd.discover()
    assert roles
    assert any(role.defaults for role in roles)
