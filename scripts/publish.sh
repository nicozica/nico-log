#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK_FILE="/tmp/nico-log-build.lock"
REMOTE_DESTINATION="nico@pizero:/srv/data/www/nico.com.ar/"

current_branch="$(git -C "$ROOT_DIR" branch --show-current 2>/dev/null || true)"
if [ "$current_branch" != "main" ]; then
  branch_label="${current_branch:-detached HEAD}"
  echo "Refusing to publish: current branch is '${branch_label}'; production publishing is allowed only from 'main'." >&2
  exit 64
fi

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "Another Nico Log publication is already running." >&2
  exit 75
fi

"$ROOT_DIR/scripts/dev-build.sh"

rsync -rltDzv --delete \
  --no-perms --no-owner --no-group \
  --chmod=Du=rwx,Dgo=rx,Fu=rw,Fgo=r \
  --exclude=/status/ \
  -e "ssh -o BatchMode=yes -o ConnectTimeout=5" \
  "$ROOT_DIR/dist/" \
  "$REMOTE_DESTINATION"

echo "Publish complete: $REMOTE_DESTINATION"
