#!/usr/bin/env bash
set -euo pipefail

# Resolve repo root from the script location.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

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
