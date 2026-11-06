#!/usr/bin/env bash
# Creates the matrix of roles for the GitHub Actions molecule job.
#
# On pull requests only the roles touched by the PR are tested, or every role
# when the shared molecule config changes. Scheduled and manual runs test all roles.
set -euo pipefail

all_roles() {
  for f in roles/*; do
    [[ -d "$f/molecule" ]] && echo "$f"
  done
  return 0
}

if [[ "${GITHUB_EVENT_NAME:-}" == "pull_request" ]]; then
  changed=$(git diff --name-only "origin/${GITHUB_BASE_REF}...HEAD")

  if grep -qE '^tests/molecule/' <<<"$changed"; then
    roles=$(all_roles)
  else
    # roles/<name>/... -> roles/<name>, keeping only roles that still exist and have tests
    roles=$(grep -oE '^roles/[^/]+/' <<<"$changed" | sed 's#/$##' | sort -u |
      while read -r f; do
        [[ -d "$f/molecule" ]] && echo "$f"
      done || true)
  fi
else
  roles=$(all_roles)
fi

matrix=$(jq -R -s -c 'split("\n") | map(select(length > 0))' <<<"$roles")
echo "Roles to test: $matrix"
echo "matrix=$matrix" >> "$GITHUB_OUTPUT"
