#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK_FILE="/tmp/nico-log-build.lock"
REMOTE_DESTINATION="nico@pizero:/srv/data/www/nico.com.ar/"

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
