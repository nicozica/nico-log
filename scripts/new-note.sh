#!/usr/bin/env bash
set -euo pipefail

# Create a markdown note with timestamp and slug from a title argument.
if [ "$#" -lt 1 ]; then
  echo "Usage: $0 \"Note title\""
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NOTES_DIR="$ROOT_DIR/content/notes"
TITLE="$*"
DATE_NOW="$(date --iso-8601=seconds)"
DATE_FILE="$(date +%Y-%m-%d)"

SLUG="$(printf '%s' "$TITLE" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//')"
if [ -z "$SLUG" ]; then
  SLUG="note"
fi

FILE_PATH="$NOTES_DIR/$DATE_FILE-$SLUG.md"

if [ -f "$FILE_PATH" ]; then
  echo "Note already exists: $FILE_PATH"
  exit 1
fi

cat > "$FILE_PATH" <<NOTE
---
title: $TITLE
date: $DATE_NOW
tags:
  - note
---

Write your note here.
NOTE

echo "Created $FILE_PATH"
