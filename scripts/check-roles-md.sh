#!/usr/bin/env bash
# ROLES.md is the local candidate-role working doc (git-excluded). This checks
# it in both directions: every role under roles/ is named in it, and no role
# that already exists is still offered in a candidate table row.
set -euo pipefail
cd "$(dirname "$0")/.."

doc=ROLES.md
if [[ ! -f $doc ]]; then
  echo "ROLES.md not found — it is a local-only working doc, skipping."
  exit 0
fi

# Infrastructure and template roles are not applications.
skip() {
  case $1 in
    ansible-nas-* | hello_world) return 0 ;;
  esac
  return 1
}

# "Replacements and upstream health" lists existing roles on purpose; every
# table above it lists candidates only.
candidates=$(awk '/^## Replacements and upstream health/{exit} {print}' "$doc")

status=0
for dir in roles/*/; do
  role=${dir#roles/}
  role=${role%/}
  skip "$role" && continue

  if ! grep -qF '`'"$role"'`' "$doc"; then
    echo "roles/$role: not mentioned in ROLES.md — add it to a section or an 'Already covered' line"
    status=1
  fi

  if awk -v r="$role" 'index($0, "| `" r "` |") { found = 1 } END { exit !found }' <<<"$candidates"; then
    echo "roles/$role: still listed as a candidate row in ROLES.md — remove it and add it to 'Already covered'"
    status=1
  fi
done

[[ $status -eq 0 ]] && echo "ROLES.md is in sync with roles/."
exit $status
