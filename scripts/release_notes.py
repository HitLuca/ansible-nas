#!/usr/bin/env python3
"""Print the GitHub release notes for a tag: its CHANGELOG.md section plus the footer.

    scripts/release_notes.py v2.0.0

The section is everything under the "## v2.0.0 ..." heading up to the next "##"
heading. The footer is .github/release-footer.md. Fails when the section is
missing or empty, so a tag pushed before the changelog was renamed publishes
nothing instead of an empty release.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Sequence

import role_defaults

CHANGELOG = "CHANGELOG.md"
FOOTER = ".github/release-footer.md"


def section(text: str, tag: str) -> str:
    """The body of the changelog section headed by *tag*, or empty."""
    heading = re.compile(rf"^##[ \t]+{re.escape(tag)}(?:[ \t]|$)")
    lines: list[str] = []
    inside = False
    for line in text.splitlines():
        if re.match(r"^##[ \t]", line):
            inside = heading.match(line) is not None
            continue
        if inside:
            lines.append(line)
    return "\n".join(lines).strip()


def main(argv: Sequence[str] | None = None, root: Path = role_defaults.REPO_ROOT) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tag", help="release tag, e.g. v2.0.0")
    args = parser.parse_args(argv)

    body = section((root / CHANGELOG).read_text(), args.tag)
    if not body:
        print(f"{CHANGELOG} has no '## {args.tag}' section with content.", file=sys.stderr)
        return 1
    footer = (root / FOOTER).read_text().strip()
    print(f"{body}\n\n{footer}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
