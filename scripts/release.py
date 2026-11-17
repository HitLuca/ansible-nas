#!/usr/bin/env python3
"""Cut a release locally: rename "## Unreleased" in CHANGELOG.md, commit, tag.

    scripts/release.py v2.0.0

Never pushes. Afterwards push the commit and the tag yourself; the Release
workflow then drafts the GitHub release from the new changelog section.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Sequence

import check_breaking_changes as breaking
import role_defaults

VERSION = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
EMPTY = ("", "Nothing yet.")


def parse(version: str) -> tuple[int, int, int]:
    """(major, minor, patch) of a vX.Y.Z tag, or zeros when malformed."""
    match = VERSION.match(version)
    return (int(match[1]), int(match[2]), int(match[3])) if match else (0, 0, 0)


def version_problem(version: str, base: str) -> str:
    """Why *version* is not a valid next release after tag *base*, or empty."""
    if not VERSION.match(version):
        return f"'{version}' is not of the form vX.Y.Z"
    if not base:
        return "no previous tag to release after"
    if parse(version) <= parse(base):
        return f"{version} is not newer than {base}"
    return ""


def state_problem(root: Path, version: str, base: str) -> str:
    """Why the repository is not ready to release *version*, or empty."""
    branch = run_git(root, "branch", "--show-current").stdout.strip()
    if branch != "main":
        return f"releases are cut from main, not '{branch or 'a detached HEAD'}'"
    if run_git(root, "status", "--porcelain").stdout.strip():
        return "the working tree has uncommitted changes"
    if breaking.unreleased(root).strip() in EMPTY:
        return "CHANGELOG.md has nothing under '## Unreleased'"
    if breaking.breaks(root, base) and parse(version)[0] == parse(base)[0]:
        return f"breaking changes since {base} need a major release, not {version}"
    return ""


def problem(root: Path, version: str) -> str:
    """Why *version* cannot be released now, or an empty string."""
    base = breaking.last_tag(root)
    return version_problem(version, base) or state_problem(root, version, base)


def run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run git in *root*."""
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)


def main(argv: Sequence[str] | None = None, root: Path = role_defaults.REPO_ROOT) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("version", help="new release tag, e.g. v2.0.0")
    version = parser.parse_args(argv).version

    if reason := problem(root, version):
        print(f"Not releasing: {reason}", file=sys.stderr)
        return 1

    path = root / breaking.CHANGELOG
    text = path.read_text()
    renamed = re.sub(
        r"^##[ \t]+Unreleased[ \t]*$",
        f"## Unreleased\n\nNothing yet.\n\n## {version} — {date.today().isoformat()}",
        text, count=1, flags=re.MULTILINE,
    )
    path.write_text(renamed)
    for args in (("add", breaking.CHANGELOG), ("commit", "-m", f":bookmark: release {version}"),
                 ("tag", version)):
        result = run_git(root, *args)
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
            return 1
    print(f"Committed and tagged {version}. Push it yourself:")
    print(f"\n  git push && git push origin {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
