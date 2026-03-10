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
    echo "If these notes are not pushed to GitHub, autodeploy will not publish them."
  fi
fi

if [ ! -x "$VENV_DIR/bin/pip" ] || [ ! -x "$VENV_DIR/bin/python" ]; then
  rm -rf "$VENV_DIR"
  if ! python3 -m venv "$VENV_DIR"; then
    echo "Failed to create virtualenv. Install python3-venv and retry."
    exit 1
  fi
fi

"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$ROOT_DIR/requirements.txt"
"$VENV_DIR/bin/python" "$ROOT_DIR/generator/build.py"

echo "Build complete: $ROOT_DIR/dist"
