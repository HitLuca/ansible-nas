#!/usr/bin/env bash
# Reports host ports claimed by more than one role's defaults.
#
# Ports are host-wide, so two enabled roles that bind the same host port can't
# run at once. This catches a new role colliding with an existing one at review
# time instead of at deploy time, when docker fails with "port is already
# allocated".
set -euo pipefail
cd "$(dirname "$0")/../roles"

# role -> host port, for every *_port* default whose value is a plain number.
pairings=$(
  grep -H '^[a-z0-9_]*_port[a-z_]*:' ./*/defaults/main.yml |
    awk -F: '{
      file = $1
      value = $0
      sub(/^[^"]*"/, "", value)
      sub(/".*$/, "", value)
      if (value ~ /^[0-9]+$/) {
        split(file, parts, "/")
        print parts[2], value
      }
    }' |
    sort -u
)

conflicts=$(
  printf '%s\n' "$pairings" |
    awk '{ roles[$2] = roles[$2] " " $1 }
         END {
           for (port in roles) {
             n = split(roles[port], names, " ")
             if (n > 1) printf "  port %-6s claimed by%s\n", port, roles[port]
           }
         }' |
    sort -V
)

if [[ -z "$conflicts" ]]; then
  echo "No port conflicts between roles."
  exit 0
fi

echo "Host port conflicts between roles:"
printf '%s\n' "$conflicts"
exit 1
