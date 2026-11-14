#!/usr/bin/env bash
# Fails when something since the last release tag breaks an existing
# deployment and CHANGELOG.md has no entry for it under "## Unreleased".
#
# Breaking, for this repo:
#   - a role directory disappeared (removed, or renamed — same effect: an
#     inventory that enables the old name silently deploys nothing)
#   - a <role>_* default was deleted (the inventory key stops applying)
#   - a role's _port / _data_directory default changed (moves or remaps a
#     container that is already running)
#   - a role's pinned image major changed (app migrations are forward-only, so
#     an operator cannot roll back by checking out the previous commit)
#
# Pass a tag to compare against something other than the last release:
#   tests/check-breaking-changes.sh v1.0.0
set -euo pipefail
cd "$(dirname "$0")/.."

changelog=CHANGELOG.md
base=${1:-$(git describe --tags --abbrev=0 2>/dev/null || true)}

if [[ -z $base ]]; then
  echo "No release tag found — nothing to compare against."
  exit 0
fi

results=$(mktemp)
trap 'rm -f "$results"' EXIT

record() {
  printf '%s\t%s\n' "$1" "$2" >>"$results"
}

# Leading numeric component of a pinned image version, or empty for tags where
# "major" has no meaning ("version-6.7.9", "alpine", a commit sha).
major() {
  local v=$1
  v=${v#\"}
  v=${v%\"}
  v=${v#\'}
  v=${v%\'}
  if [[ $v =~ ^[vV]?([0-9]+) ]]; then
    printf '%s' "${BASH_REMATCH[1]}"
  fi
}

# Differences between the role's defaults at the tag and now, as tab-separated
# records: "deleted <key>", "moved <key> <old> -> <new>", "image <key> <old> <new>".
compare_defaults() {
  awk '
    function key_of(line) {
      if (match(line, /^[a-z0-9_]+:/) == 0) return ""
      return substr(line, 1, RLENGTH - 1)
    }
    function val_of(line) {
      match(line, /^[a-z0-9_]+:/)
      v = substr(line, RLENGTH + 1)
      sub(/^[ \t]+/, "", v)
      sub(/[ \t]+#.*$/, "", v)
      return v
    }
    FNR == NR {
      k = key_of($0)
      if (k != "") oldv[k] = val_of($0)
      next
    }
    {
      k = key_of($0)
      if (k != "") { seen[k] = 1; newv[k] = val_of($0) }
    }
    END {
      for (k in oldv) {
        if (!(k in seen)) {
          printf "deleted\t%s\n", k
          continue
        }
        if (k ~ /(_port(_[a-z0-9]+)*|_data_directory)$/ && oldv[k] != newv[k])
          printf "moved\t%s\t%s -> %s\n", k, oldv[k], newv[k]
        if (k ~ /_image_(version|tag)$/ && oldv[k] != newv[k])
          printf "image\t%s\t%s\t%s\n", k, oldv[k], newv[k]
      }
    }
  ' <(printf '%s\n' "$1") <(printf '%s\n' "$2")
}

base_roles=$(git ls-tree -d --name-only "$base" roles/ | sed 's|^roles/||' | sort)
head_roles=$(find roles -mindepth 1 -maxdepth 1 -type d | sed 's|^roles/||' | sort)

# Removed roles. A rename shows up here as "removed or renamed", which is the
# phrasing the changelog entry needs anyway.
comm -23 <(printf '%s\n' "$base_roles") <(printf '%s\n' "$head_roles") |
  while read -r role; do
    [[ -n $role ]] || continue
    record "$role" "role removed or renamed — an inventory that enables '$role' now deploys nothing"
  done

# Roles in both releases: compare their defaults and pinned image versions.
comm -12 <(printf '%s\n' "$base_roles") <(printf '%s\n' "$head_roles") |
  while read -r role; do
    [[ -n $role ]] || continue
    path="roles/$role/defaults/main.yml"
    [[ -f $path ]] || continue
    old=$(git show "$base:$path" 2>/dev/null || true)
    new=$(cat "$path")

    compare_defaults "$old" "$new" |
      while IFS=$'\t' read -r kind key old_value new_value; do
        case $kind in
          deleted)
            record "$role" "defaults/main.yml: '$key' deleted — an inventory that sets it silently stops applying"
            ;;
          moved)
            record "$role" "defaults/main.yml: '$key' default changed ($old_value) — an existing container is moved or remapped"
            ;;
          image)
            old_major=$(major "$old_value")
            new_major=$(major "$new_value")
            if [[ -z $old_major || -z $new_major ]]; then
              continue
            fi
            # Date-style pins ("2026.01.01") change year without a breaking app
            # migration, and "major" is not meaningful for them.
            if [[ ${#old_major} -ge 4 || ${#new_major} -ge 4 ]]; then
              continue
            fi
            if [[ $old_major == "$new_major" ]]; then
              continue
            fi
            record "$role" "defaults/main.yml: '$key' major image bump $old_value -> $new_value — app migrations are forward-only, back up first"
            ;;
        esac
      done
  done

if [[ ! -s $results ]]; then
  echo "No breaking changes since $base."
  exit 0
fi

unreleased=""
if [[ -f $changelog ]]; then
  unreleased=$(awk '/^##[ \t]+Unreleased/{f=1; next} /^##[ \t]/{f=0} f' "$changelog")
fi

status=0
while IFS=$'\t' read -r role message; do
  if grep -qF '`'"$role"'`' <<<"$unreleased"; then
    continue
  fi
  echo "roles/$role: $message"
  status=1
done < <(sort -u "$results")

if [[ $status -eq 0 ]]; then
  echo "Breaking changes since $base are recorded in $changelog."
  exit 0
fi

cat <<EOF

These break existing deployments, so each needs a bullet under "## Unreleased"
in $changelog, naming the role in backticks:

  - \`<role>\` — what changed and what an operator must do about it.

Version bumps are decided when you tag, not per commit: any break in a release
makes it a major release.
EOF
exit 1
