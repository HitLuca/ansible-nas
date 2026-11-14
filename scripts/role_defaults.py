"""Load each role's ``defaults/main.yml`` once, for every check under tests/.

The checks used to grep these files with a regex each, and every regex drifted
a little: one missed unquoted ports, another counted a requoted value as a
change. This module parses the YAML properly and keeps, for every top-level
key, three things the checks need:

* ``value`` - the value as YAML loads it (``8080`` is an int, ``"8080"`` a str)
* ``text`` - the scalar exactly as written, minus quotes, so ``3.10`` stays
  ``3.10`` instead of becoming the float ``3.1`` and ``8080``/``"8080"``/
  ``'8080'`` all read ``8080``. Empty for lists and mappings.
* ``line`` - the 1-based line of the key, for reports and in-place patching

``ansible-nas`` defaults are always a flat mapping of ``<role>_*`` keys; only
the top level is indexed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

# Keys naming a container image, with or without an embedded ":tag".
IMAGE_KEY = re.compile(r"^(?P<prefix>.+)_(?:image_name|docker_image_name|image|docker_image)$")
VERSION_SUFFIXES = ("_image_version", "_image_tag")


@dataclass(frozen=True)
class Entry:
    """One top-level ``key: value`` of a defaults file."""

    value: object
    text: str
    line: int


@dataclass
class Role:
    """A directory under roles/ and its parsed defaults."""

    name: str
    path: Path
    defaults: dict[str, Entry] = field(default_factory=dict)

    @property
    def defaults_path(self) -> Path:
        """Where the role's defaults live, whether or not the file exists."""
        return self.path / "defaults" / "main.yml"

    @property
    def conventional_flag(self) -> str:
        """The enabled flag the role should declare: ``<role name>_enabled``."""
        return re.sub(r"[-.]", "_", self.name) + "_enabled"

    @property
    def flag(self) -> str | None:
        """The first ``*_enabled`` key in file order, or None."""
        return next((key for key in self.defaults if key.endswith("_enabled")), None)

    def text(self, key: str) -> str:
        """The scalar text of *key*, or an empty string when it is not set."""
        entry = self.defaults.get(key)
        return entry.text if entry else ""

    def has_molecule(self) -> bool:
        """Whether the role has a molecule directory at all."""
        return (self.path / "molecule").is_dir()

    def task_files(self) -> list[Path]:
        """Every YAML file under tasks/, sorted."""
        tasks = self.path / "tasks"
        if not tasks.is_dir():
            return []
        return sorted(p for p in tasks.rglob("*") if p.suffix in (".yml", ".yaml") and p.is_file())


class DefaultsError(Exception):
    """A defaults file is not a YAML mapping."""


def parse_defaults(text: str, source: str = "<string>") -> dict[str, Entry]:
    """Index the top-level keys of a defaults file's *text*."""
    try:
        node = yaml.compose(text, Loader=yaml.SafeLoader)
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise DefaultsError(f"{source}: {exc}") from exc
    if node is None or data is None:  # no document, or an empty one ("---")
        return {}
    if not isinstance(node, yaml.MappingNode) or not isinstance(data, dict):
        raise DefaultsError(f"{source}: expected a mapping at the top level")
    entries: dict[str, Entry] = {}
    for key_node, value_node in node.value:
        key = str(key_node.value)
        scalar = isinstance(value_node, yaml.ScalarNode)
        entries[key] = Entry(
            value=data.get(key),
            text=str(value_node.value).strip() if scalar else "",
            line=key_node.start_mark.line + 1,
        )
    return entries


def load_defaults(path: Path) -> dict[str, Entry]:
    """Index *path*, or return an empty mapping when the file does not exist."""
    if not path.is_file():
        return {}
    return parse_defaults(path.read_text(), str(path))


def discover(root: Path = REPO_ROOT, only: Iterable[str] = ()) -> list[Role]:
    """Every role under ``<root>/roles``, sorted by name, optionally filtered."""
    wanted = set(only)
    roles: list[Role] = []
    roles_dir = root / "roles"
    for path in sorted(p for p in roles_dir.iterdir() if p.is_dir()):
        if wanted and path.name not in wanted:
            continue
        role = Role(name=path.name, path=path)
        role.defaults = load_defaults(role.defaults_path)
        roles.append(role)
    return roles


def split_repo_tag(value: str) -> tuple[str, str]:
    """Split ``repo:tag`` without breaking a ``host:port/repo`` reference."""
    repo, separator, tag = value.rpartition(":")
    if separator and "/" not in tag:
        return repo, tag
    return value, ""


def version_key(defaults: dict[str, Entry], prefix: str) -> str | None:
    """The ``<prefix>_image_version`` or ``_image_tag`` key pinning an image."""
    return next(
        (prefix + suffix for suffix in VERSION_SUFFIXES if prefix + suffix in defaults), None
    )
