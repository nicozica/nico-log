#!/usr/bin/env bash
set -euo pipefail

# Resolve repo root from the script location.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

if git -C "$ROOT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  PENDING_NOTES="$(git -C "$ROOT_DIR" status --porcelain -- content/notes 2>/dev/null || true)"
  if [ -n "$PENDING_NOTES" ]; then
    echo "WARNING: You have note files with local git changes:"
    echo "$PENDING_NOTES"
    echo "These local files are included in the build, even when they are not committed."
  fi
fi

if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "Virtualenv not found. Run $ROOT_DIR/scripts/bootstrap.sh first." >&2
  exit 1
fi

if ! "$VENV_DIR/bin/python" -c 'import dateutil, feedparser, jinja2, markdown, requests, yaml' >/dev/null 2>&1; then
  echo "Virtualenv dependencies are incomplete. Run $ROOT_DIR/scripts/bootstrap.sh." >&2
  exit 1
fi

"$VENV_DIR/bin/python" "$ROOT_DIR/generator/build.py"

echo "Build complete: $ROOT_DIR/dist"
