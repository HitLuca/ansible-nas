#!/usr/bin/env bash
# Enforces the role anatomy documented in CLAUDE.md: every role has defaults,
# tasks and (unless exempt) a molecule scenario, defaults/main.yml declares the
# role's enabled flag, and tasks/main.yml carries the gated start/stop blocks.
# Catches new roles copied from something other than roles/hello_world/ before
# the drift reaches the playbook.
set -euo pipefail
cd "$(dirname "$0")/../roles"

# Roles that legitimately deviate from the standard anatomy. Keep each list
# sorted so exemptions are easy to audit.
NO_MOLECULE=(
  ansible-nas-docker
  ansible-nas-general
  ansible-nas-users
  ddns_updater
  duplicati
  homepage
  logging
  loki
  minecraft-bedrock-server
  mumble
  promtail
)
NO_DEFAULTS=(ansible-nas-users)
NO_ENABLED_FLAG=(ansible-nas-docker ansible-nas-general)
NO_START_STOP_BLOCK=(ansible-nas-docker ansible-nas-general ansible-nas-users logging stats)
# Roles whose enabled flag is not <role_name>_enabled.
UNCONVENTIONAL_FLAG=(healthchecks.io logging)

MOLECULE_FILES=(molecule.yml side_effect.yml verify.yml verify_stopped.yml)

contains() {
  local needle=$1 item
  shift
  for item in "$@"; do [[ $item == "$needle" ]] && return 0; done
  return 1
}

status=0
fail() {
  echo "roles/$1: $2"
  status=1
}

for dir in */; do
  role=${dir%/}

  [[ -f "$role/tasks/main.yml" ]] || fail "$role" "missing tasks/main.yml"

  if contains "$role" "${NO_MOLECULE[@]}"; then
    :
  else
    for file in "${MOLECULE_FILES[@]}"; do
      [[ -f "$role/molecule/default/$file" ]] || fail "$role" "missing molecule/default/$file"
    done
  fi

  if [[ -d "$role/meta" ]]; then
    fail "$role" "has a meta/ directory; this repo's roles do not use one"
  fi

  if contains "$role" "${NO_DEFAULTS[@]}"; then
    continue
  fi

  if [[ ! -f "$role/defaults/main.yml" ]]; then
    fail "$role" "missing defaults/main.yml"
    continue
  fi

  flag=$(grep -oE '^[a-z0-9_]+_enabled:' "$role/defaults/main.yml" | head -1 | tr -d ':' || true)
  if [[ -z $flag ]]; then
    contains "$role" "${NO_ENABLED_FLAG[@]}" || fail "$role" "defaults/main.yml has no <role>_enabled flag"
    continue
  fi

  base=${role//-/_}
  base=${base//./_}
  if [[ $flag != "${base}_enabled" ]] && ! contains "$role" "${UNCONVENTIONAL_FLAG[@]}"; then
    fail "$role" "enabled flag '$flag' should be '${base}_enabled'"
  fi

  if contains "$role" "${NO_START_STOP_BLOCK[@]}"; then
    continue
  fi
  grep -qE "when: *$flag is true" "$role/tasks/main.yml" \
    || fail "$role" "tasks/main.yml has no 'when: $flag is true' start block"
  grep -qE "when: *$flag is false" "$role/tasks/main.yml" \
    || fail "$role" "tasks/main.yml has no 'when: $flag is false' stop block"
done

# Docker image references: a role that starts containers must take its image
# from defaults, and every *_image_name needs a pin next to it. A literal
# image: in tasks is invisible to renovate.json and to make check-images.
for dir in */; do
  role=${dir%/}
  grep -rq 'docker_container' "$role/tasks" 2>/dev/null || continue

  literal=$(grep -rhoE '^[[:space:]]+image:[[:space:]]*[^"'"'"'{[:space:]][^[:space:]]*' "$role/tasks" 2>/dev/null | sed -E 's/^[[:space:]]+image:[[:space:]]*//' || true)
  if [[ -n $literal ]]; then
    fail "$role" "tasks hardcode an image ($(echo $literal | tr '\n' ' ')); use {{ <role>_image_name }}:{{ <role>_image_version }}"
  fi

  defaults="$role/defaults/main.yml"
  [[ -f $defaults ]] || continue

  if ! grep -qE '^[a-z0-9_]+_(docker_image|image|image_name):' "$defaults"; then
    fail "$role" "defaults/main.yml declares no image for its containers"
    continue
  fi

  while read -r key; do
    prefix=${key%_image_name}
    grep -qE "^${prefix}_(image_version|image_tag):" "$defaults" \
      || fail "$role" "$key has no ${prefix}_image_version pin next to it"
  done < <(grep -oE '^[a-z0-9_]+_image_name:' "$defaults" | tr -d ':' || true)
done

[[ $status -eq 0 ]] && echo "All roles follow the standard structure."
exit $status
