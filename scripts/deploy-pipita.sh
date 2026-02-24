#!/usr/bin/env bash
set -euo pipefail

# Deploy from Pipa to Pipita and prepare runtime directories/systemd units.
REMOTE_HOST="${1:-pipita}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

REMOTE_REPO="/srv/repos/personal/nico.com.ar"
REMOTE_VENV="$REMOTE_REPO/.venv"
REMOTE_WWW="/srv/data/www/nico.com.ar"
REMOTE_CACHE="/srv/data/nico-portal-cache"
REMOTE_LOGS="/srv/logs/nico-portal"

"$ROOT_DIR/scripts/dev-build.sh"

rsync -az --delete \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude 'dist/' \
  --exclude 'cache/' \
  "$ROOT_DIR/" "$REMOTE_HOST:$REMOTE_REPO/"

ssh "$REMOTE_HOST" "bash -s" <<'REMOTE_EOF'
set -euo pipefail

REMOTE_REPO="/srv/repos/personal/nico.com.ar"
REMOTE_VENV="$REMOTE_REPO/.venv"
REMOTE_WWW="/srv/data/www/nico.com.ar"
REMOTE_CACHE="/srv/data/nico-portal-cache"
REMOTE_LOGS="/srv/logs/nico-portal"
RUN_USER="$(id -un)"
RUN_GROUP="$(id -gn)"

if [ ! -x "$REMOTE_VENV/bin/pip" ] || [ ! -x "$REMOTE_VENV/bin/python" ]; then
  rm -rf "$REMOTE_VENV"
  python3 -m venv "$REMOTE_VENV"
fi

"$REMOTE_VENV/bin/pip" install --upgrade pip
"$REMOTE_VENV/bin/pip" install -r "$REMOTE_REPO/requirements.txt"

sudo mkdir -p "$REMOTE_WWW" "$REMOTE_CACHE" "$REMOTE_LOGS"
sudo chown -R "$RUN_USER:$RUN_GROUP" "$REMOTE_WWW" "$REMOTE_CACHE" "$REMOTE_LOGS"

sudo install -m 0644 "$REMOTE_REPO/systemd/pipita-portal-generate.service" /etc/systemd/system/pipita-portal-generate.service
sudo install -m 0644 "$REMOTE_REPO/systemd/pipita-portal-generate.timer" /etc/systemd/system/pipita-portal-generate.timer

sudo systemctl daemon-reload
sudo systemctl enable --now pipita-portal-generate.timer

"$REMOTE_VENV/bin/python" "$REMOTE_REPO/generator/build.py" \
  --cache-dir "$REMOTE_CACHE" \
  --output-dir "$REMOTE_REPO/dist"

rsync -a --delete "$REMOTE_REPO/dist/" "$REMOTE_WWW/"
REMOTE_EOF

echo "Deploy complete to $REMOTE_HOST"
