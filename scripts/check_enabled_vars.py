#!/usr/bin/env python3
"""Every ``<name>_enabled`` a role's tasks refer to must be a defined flag.

The flag has to be declared in some role's ``defaults/main.yml``. Catches typos
and role renames (e.g. speedtest-tracker vs speedtest_tracker) that otherwise
only fail at deploy time with an undefined-variable error.

Covers inline ``when: a_enabled is true``, compound conditions
(``a_enabled is false or b_enabled is false``), list-form ``when:`` items and
Jinja expressions. Skips attribute lookups (``item.x_enabled``), mapping keys
(``loki_enabled: true`` as a module or include_role var) and comments.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterator, Sequence

import role_defaults

# A whole identifier ending in _enabled: not part of a longer name or an
# attribute lookup (item.x_enabled), and not a mapping key (x_enabled: true).
REFERENCE = re.compile(
    r"(?<![\w.])([a-z0-9_]*[a-z0-9]_enabled)(?![\w.])(?!\s*:(?:\s|$))"
)
COMMENT = re.compile(r"(?:^|\s)#.*$")


def references(text: str) -> Iterator[str]:
    """The ``*_enabled`` variables referenced in a task file's *text*."""
    for line in text.splitlines():
        yield from REFERENCE.findall(COMMENT.sub("", line))


def problems(roles: Sequence[role_defaults.Role]) -> list[str]:
    """One message per undefined flag reference."""
    defined = {
        key for role in roles for key in role.defaults if key.endswith("_enabled")
    }
    messages: list[str] = []
    for role in roles:
        used = {
            name for path in role.task_files() for name in references(path.read_text())
        }
        messages += [
            f"roles/{role.name}/tasks: '{name}' is not defined in any role's defaults/main.yml"
            for name in sorted(used - defined)
        ]
    return messages


def main(
    argv: Sequence[str] | None = None, root: Path = role_defaults.REPO_ROOT
) -> int:
    """Entry point."""
    del argv  # no options; the signature matches the other checks
    messages = problems(role_defaults.discover(root))
    for message in messages:
        print(message)
    if messages:
        return 1
    print("All role enabled flags are defined.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
