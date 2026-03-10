#!/usr/bin/env bash
set -euo pipefail

# Deploy static output from Pipa to Pizero.
# Pipa is the only build scheduler; Pizero only serves static files.
REMOTE_HOST="${1:-pizero}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE_WWW="/srv/data/www/nico.com.ar"

"$ROOT_DIR/scripts/dev-build.sh"

ssh "$REMOTE_HOST" "sudo mkdir -p '$REMOTE_WWW' && sudo chown -R \"\$(id -un):\$(id -gn)\" '$REMOTE_WWW' && sudo systemctl disable --now pizero-portal-generate.timer >/dev/null 2>&1 || true"

rsync -az --delete "$ROOT_DIR/dist/" "$REMOTE_HOST:$REMOTE_WWW/"

echo "Deploy complete to $REMOTE_HOST"
