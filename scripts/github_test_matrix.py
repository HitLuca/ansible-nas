#!/usr/bin/env python3
"""Create the matrix of roles for the GitHub Actions molecule job.

On pull requests only the roles touched by the PR are tested, or every role
when something every scenario depends on changes: the shared molecule config,
or requirements-dev.txt, which pins molecule and ansible-core. Scheduled and
manual runs test all roles.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent

# Files every scenario depends on: when one changes, test every role.
SHARED = re.compile(r"^(?:tests/molecule/|requirements-dev\.txt$)")
# "roles/<name>/..." -> "roles/<name>".
ROLE_DIR = re.compile(r"^(roles/[^/]+)/")


def all_roles(root: Path) -> list[str]:
    """Every role that has a molecule directory, as ``roles/<name>``."""
    return sorted(
        f"roles/{path.name}"
        for path in (root / "roles").iterdir()
        if path.is_dir() and (path / "molecule").is_dir()
    )


def changed_files(root: Path, base_ref: str) -> list[str]:
    """The files changed between the PR base branch and HEAD."""
    result = subprocess.run(
        ["git", "diff", "--name-only", f"origin/{base_ref}...HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()


def matrix_for(root: Path, event_name: str | None, base_ref: str | None) -> list[str]:
    """The roles to test for this run."""
    if event_name == "pull_request":
        changed = changed_files(root, base_ref or "main")
        if any(SHARED.match(line) for line in changed):
            return all_roles(root)
        touched = {match.group(1) for line in changed if (match := ROLE_DIR.match(line))}
        return sorted(role for role in touched if (root / role / "molecule").is_dir())
    return all_roles(root)


def main(argv: Sequence[str] | None = None, root: Path = REPO_ROOT) -> int:
    """Entry point."""
    del argv  # no options; the signature matches the other checks
    roles = matrix_for(
        root,
        os.environ.get("GITHUB_EVENT_NAME"),
        os.environ.get("GITHUB_BASE_REF"),
    )
    matrix = json.dumps(roles, separators=(",", ":"))
    print(f"Roles to test: {matrix}")
    # Outside Actions (a local dry run) there is no step output file.
    with open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a", encoding="utf-8") as output:
        output.write(f"matrix={matrix}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
