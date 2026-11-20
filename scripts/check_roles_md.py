#!/usr/bin/env python3
"""ROLES.md is the local candidate-role working doc (git-excluded). This checks
it in both directions: every role under roles/ is named in it, and no role
that already exists is still offered in a candidate table row.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

import role_defaults

# Infrastructure and template roles are not applications.
SKIP_EXACT = ("hello_world",)
SKIP_PREFIX = "ansible-nas-"


def _is_application(role: str) -> bool:
    """Whether the doc must cover *role*."""
    return role not in SKIP_EXACT and not role.startswith(SKIP_PREFIX)


def problems(root: Path, doc: Path) -> list[str]:
    """One message per role the doc is missing or still lists as a candidate."""
    text = doc.read_text()
    # "Replacements and upstream health" lists existing roles on purpose; every
    # table above it lists candidates only.
    candidates = text.split("## Replacements and upstream health", 1)[0]

    messages: list[str] = []
    for path in sorted(p for p in (root / "roles").iterdir() if p.is_dir()):
        role = path.name
        if not _is_application(role):
            continue
        if f"`{role}`" not in text:
            messages.append(
                f"roles/{role}: not mentioned in ROLES.md — add it to a section "
                "or an 'Already covered' line"
            )
        if f"| `{role}` |" in candidates:
            messages.append(
                f"roles/{role}: still listed as a candidate row in ROLES.md — "
                "remove it and add it to 'Already covered'"
            )
    return messages


def main(
    argv: Sequence[str] | None = None, root: Path = role_defaults.REPO_ROOT
) -> int:
    """Entry point."""
    del argv  # no options; the signature matches the other checks
    doc = root / "ROLES.md"
    if not doc.is_file():
        print("ROLES.md not found — it is a local-only working doc, skipping.")
        return 0
    messages = problems(root, doc)
    for message in messages:
        print(message)
    if messages:
        return 1
    print("ROLES.md is in sync with roles/.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
