#!/usr/bin/env python3
"""Prove a mechanical YAML reformat did not change any value.

Parses every YAML file that differs from a git base (default ``HEAD``, so
staged and unstaged edits both count) at the base and in the working tree, and
reports the files whose parsed data differ. A quote-style or whitespace
rewrite passes; changing ``8080`` to ``"8080"`` or ``0.10`` to ``"0.10"`` fails.

Run it on demand (``make check-yaml-unchanged``) before committing a bulk
rewrite. It is not a pre-commit hook: an intended value change would fail it
on every commit.

Files that are not plain YAML at both ends (Jinja templates) are skipped and
listed, because comparing them as YAML says nothing; render them and diff the
output instead. A file that parses at one end only is reported.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Sequence

import yaml

import role_defaults

SUFFIXES = (".yml", ".yaml")


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    ).stdout


def _load(text: str) -> tuple[bool, list[object]]:
    """(parsed, documents); parsed is False when *text* is not plain YAML."""
    try:
        return True, list(yaml.safe_load_all(text))
    except yaml.YAMLError:
        return False, []


def compare(root: Path, base: str) -> tuple[list[str], list[str]]:
    """(files whose data changed, files skipped as unparseable)."""
    changed: list[str] = []
    skipped: list[str] = []
    for name in _git(root, "diff", "--name-only", "--diff-filter=M", base).split():
        if not name.endswith(SUFFIXES):
            continue
        old_ok, old = _load(_git(root, "show", f"{base}:{name}"))
        new_ok, new = _load((root / name).read_text())
        if not old_ok and not new_ok:
            skipped.append(name)
        elif old_ok != new_ok or old != new:
            changed.append(name)
    return changed, skipped


def main(
    argv: Sequence[str] | None = None, root: Path = role_defaults.REPO_ROOT
) -> int:
    """Entry point; the optional argument is the git base."""
    base = (argv or ["HEAD"])[0]
    changed, skipped = compare(root, base)
    for name in skipped:
        print(f"skipped (not plain YAML, render and diff it): {name}")
    for name in changed:
        print(f"{name}: parsed data differs from {base}")
    if changed:
        return 1
    print(f"No YAML file's data changed since {base}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
