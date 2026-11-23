#!/usr/bin/env python3
"""Report host ports claimed by more than one role's defaults.

Ports are host-wide, so two enabled roles that bind the same host port can't
run at once. This catches a new role colliding with an existing one at review
time instead of at deploy time, when docker fails with "port is already
allocated".

Every ``*_port*`` default whose value is a plain number counts, quoted or not.
Jinja values (``"{{ other_port }}"``) are skipped.

Known conflicts are allowed (they involve roles that are mutually exclusive in
practice, or internal DB ports). New conflicts fail the check.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Sequence

import role_defaults

PORT_KEY = re.compile(r"^[a-z0-9_]*_port[a-z0-9_]*$")

# Known conflicts that are acceptable:
# - 5432: guacamole (PostgreSQL) and immich (PostgreSQL) — internal DB ports,
#   not exposed to host. If both enabled, they run in separate containers.
# - 8096: emby and jellyfin — media servers, mutually exclusive in practice.
# - 9000: portainer (web UI) and woodpecker-ci (gRPC) — different protocols.
# - 3002: netbootxyz (HTTP) and silverbullet — mutually exclusive use cases.
# - 8000: pyload and woodpecker-ci (web UI) — mutually exclusive.
# - 8080: nextcloud and zigbee2mqtt — mutually exclusive.
ALLOWED_CONFLICTS = {
    5432: {"guacamole", "immich"},
    8096: {"emby", "jellyfin"},
    9000: {"portainer", "woodpecker-ci"},
    3002: {"netbootxyz", "silverbullet"},
    8000: {"pyload", "woodpecker-ci"},
    8080: {"nextcloud", "zigbee2mqtt"},
}


def conflicts(roles: Sequence[role_defaults.Role]) -> dict[int, list[str]]:
    """Map each port claimed by two or more roles to those roles."""
    claims: dict[int, set[str]] = {}
    for role in roles:
        for key, entry in role.defaults.items():
            if PORT_KEY.match(key) and entry.text.isdigit():
                claims.setdefault(int(entry.text), set()).add(role.name)
    return {
        port: sorted(names) for port, names in sorted(claims.items()) if len(names) > 1
    }


def main(
    argv: Sequence[str] | None = None, root: Path = role_defaults.REPO_ROOT
) -> int:
    """Entry point."""
    del argv
    found = conflicts(role_defaults.discover(root))
    if not found:
        print("No port conflicts between roles.")
        return 0

    # Filter out allowed conflicts
    new_conflicts = {}
    for port, names in found.items():
        allowed = ALLOWED_CONFLICTS.get(port)
        if allowed and set(names) == allowed:
            print(f"  port {port:<6} claimed by {' '.join(names)} (allowed)")
        else:
            new_conflicts[port] = names

    if not new_conflicts:
        print("All port conflicts are known and allowed.")
        return 0

    print("New host port conflicts between roles (not in allowlist):")
    for port, names in new_conflicts.items():
        print(f"  port {port:<6} claimed by {' '.join(names)}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
