#!/usr/bin/env bash
set -euo pipefail

# Compatibility wrapper. All publications use scripts/publish.sh.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ "$#" -gt 1 ] || { [ "$#" -eq 1 ] && [ "$1" != "pizero" ]; }; then
  echo "Usage: $0 [pizero]" >&2
  exit 2
fi

exec "$ROOT_DIR/scripts/publish.sh"
