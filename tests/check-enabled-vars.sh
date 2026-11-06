#!/usr/bin/env bash
# Every `when: <name>_enabled ...` in a role's tasks must refer to a flag
# defined in some role's defaults/main.yml. Catches typos and role renames
# (e.g. speedtest-tracker vs speedtest_tracker) that otherwise only fail at
# deploy time with an undefined-variable error.
set -euo pipefail
cd "$(dirname "$0")/../roles"

defined=$(grep -hoE '^[a-z0-9_]+_enabled:' ./*/defaults/main.yml | tr -d ':' | sort -u)
status=0

for role in */; do
  role=${role%/}
  [[ -d "$role/tasks" ]] || continue
  used=$(grep -rhoE 'when: *[a-z0-9_]+_enabled' "$role/tasks" | sed -E 's/when: *//' | sort -u || true)
  for var in $used; do
    if ! grep -qx "$var" <<<"$defined"; then
      echo "roles/$role/tasks: '$var' is not defined in any role's defaults/main.yml"
      status=1
    fi
  done
done

[[ $status -eq 0 ]] && echo "All role enabled flags are defined."
exit $status
