#!/usr/bin/env python3
"""Fail on unrecorded breaking changes since the last release tag.

A change since the tag that breaks an existing deployment must have an entry
under "## Unreleased" in CHANGELOG.md.

Breaking, for this repo:

* a role directory disappeared (removed, or renamed - same effect: an inventory
  that enables the old name silently deploys nothing)
* a ``<role>_*`` default was deleted (the inventory key stops applying); a
  deleted defaults file deletes every key in it
* a role's ``_port`` / ``_directory`` default changed (moves or remaps a
  container that is already running); quoting changes do not count
* a role's pinned image major changed, in an ``_image_version`` /
  ``_image_tag`` pin or a tag embedded in an ``_image`` / ``_docker_image``
  value (app migrations are forward-only, so an operator cannot roll back by
  checking out the previous commit)

Pass a tag to compare against something other than the last release::

    scripts/check_breaking_changes.py v1.0.0
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterator, Sequence

import role_defaults
from role_defaults import Entry

CHANGELOG = "CHANGELOG.md"
LOCATION_KEY = re.compile(r"(?:_port(?:_[a-z0-9]+)*|_directory)$")
VERSION_KEY = re.compile(r"_image_(?:version|tag)$")
EMBEDDED_IMAGE_KEY = re.compile(r"_(?:docker_)?image$")
MAJOR = re.compile(r"^[vV]?(\d+)")

FOOTER = """
These break existing deployments, so each needs a bullet under "## Unreleased"
in CHANGELOG.md, naming the role in backticks:

  - `<role>` — what changed and what an operator must do about it.

Version bumps are decided when you tag, not per commit: any break in a release
makes it a major release."""


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)


def last_tag(root: Path) -> str:
    """The most recent tag reachable from HEAD, or an empty string."""
    result = _git(root, "describe", "--tags", "--abbrev=0")
    return result.stdout.strip() if result.returncode == 0 else ""


def major(version: str) -> str:
    """Leading number of a version, or empty when "major" means nothing.

    Tags such as "version-6.7.9", "alpine" or a commit sha have no major, and
    neither do date pins ("2026.01.01"), whose year changes without a breaking
    app migration.
    """
    match = MAJOR.match(version)
    if match is None or len(match[1]) >= 4:
        return ""
    return match[1]


def _embedded_tag(text: str) -> str:
    if "{" in text:
        return ""
    return role_defaults.split_repo_tag(text)[1]


def compare(old: dict[str, Entry], new: dict[str, Entry]) -> Iterator[str]:
    """The breaking differences between a role's defaults then and now."""
    for key, before in old.items():
        after = new.get(key)
        if after is None:
            yield (
                f"defaults/main.yml: '{key}' deleted"
                " — an inventory that sets it silently stops applying"
            )
            continue
        if before.text == after.text:
            continue
        if LOCATION_KEY.search(key):
            yield (
                f"defaults/main.yml: '{key}' default changed ({before.text} -> {after.text})"
                " — an existing container is moved or remapped"
            )
        if VERSION_KEY.search(key):
            old_version, new_version = before.text, after.text
        elif EMBEDDED_IMAGE_KEY.search(key):
            old_version, new_version = _embedded_tag(before.text), _embedded_tag(after.text)
        else:
            continue
        old_major, new_major = major(old_version), major(new_version)
        if old_major and new_major and old_major != new_major:
            yield (
                f"defaults/main.yml: '{key}' major image bump {old_version} -> {new_version}"
                " — app migrations are forward-only, back up first"
            )


def breaks(root: Path, base: str) -> list[tuple[str, str]]:
    """(role, message) for every breaking change since *base*."""
    listing = _git(root, "ls-tree", "-d", "--name-only", base, "roles/")
    if listing.returncode != 0:
        raise SystemExit(f"Cannot list roles at {base}: {listing.stderr.strip()}")
    base_roles = {line.removeprefix("roles/") for line in listing.stdout.split()}
    head = {role.name: role for role in role_defaults.discover(root)}

    found: list[tuple[str, str]] = []
    for name in sorted(base_roles - set(head)):
        found.append(
            (
                name,
                f"role removed or renamed — an inventory that enables '{name}' now deploys nothing",
            )
        )
    for name in sorted(base_roles & set(head)):
        shown = _git(root, "show", f"{base}:roles/{name}/defaults/main.yml")
        if shown.returncode != 0:
            continue
        old = role_defaults.parse_defaults(shown.stdout, f"{base}:roles/{name}/defaults/main.yml")
        found += [(name, message) for message in compare(old, head[name].defaults)]
    return found


def unreleased(root: Path) -> str:
    """The text of CHANGELOG.md's "## Unreleased" section, or empty."""
    path = root / CHANGELOG
    if not path.is_file():
        return ""
    lines: list[str] = []
    inside = False
    for line in path.read_text().splitlines():
        if re.match(r"^##[ \t]", line):
            inside = re.match(r"^##[ \t]+Unreleased", line) is not None
            continue
        if inside:
            lines.append(line)
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None, root: Path = role_defaults.REPO_ROOT) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tag", nargs="?", help="compare against this tag (default: the last one)")
    args = parser.parse_args(argv)

    base = args.tag or last_tag(root)
    if not base:
        print("No release tag found — nothing to compare against.")
        return 0

    found = breaks(root, base)
    if not found:
        print(f"No breaking changes since {base}.")
        return 0

    recorded = unreleased(root)
    missing = sorted({(r, m) for r, m in found if f"`{r}`" not in recorded})
    if not missing:
        print(f"Breaking changes since {base} are recorded in {CHANGELOG}.")
        return 0
    for role, message in missing:
        print(f"roles/{role}: {message}")
    print(FOOTER)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
