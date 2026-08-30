from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from editor.content import (
    CollisionError,
    ContentRepository,
    InvalidFilename,
    RevisionConflict,
    parse_document,
)


PUBLISHED = """---
title: Existing note
date: 2026-08-10
tags:
  - python
summary: Original summary
custom:
  nested: preserved
---

Published body.
"""


class ContentRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.notes_dir = self.root / "content" / "notes"
        self.drafts_dir = self.root / "content" / "drafts"
        self.notes_dir.mkdir(parents=True)
        self.drafts_dir.mkdir(parents=True)
        self.filename = "2026-08-10-existing-note.md"
        (self.notes_dir / self.filename).write_text(PUBLISHED, encoding="utf-8")
        self.repository = ContentRepository(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def form(**overrides: str) -> dict[str, str]:
        values = {
            "title": "Edited note",
            "date": "2026-08-10",
            "tags": "python, flask",
            "summary": "Draft summary",
            "slug": "existing-note",
            "lang": "es",
            "note_id": "",
            "body": "Draft body.",
        }
        values.update(overrides)
        return values

    def test_lists_published_and_drafts(self) -> None:
        draft = self.repository.create_draft(self.form(title="New", date="2026-08-11", slug="new"))
        published = self.repository.list_published()
        drafts = self.repository.list_drafts()
        self.assertEqual([note.filename for note in published], [self.filename])
        self.assertEqual([note.filename for note in drafts], [draft.filename])
        self.assertEqual(published[0].language, "es")

    def test_create_new_draft(self) -> None:
        note = self.repository.create_draft(self.form(title="New note", date="2026-08-11", slug="new-note"))
        self.assertEqual(note.filename, "2026-08-11-new-note.md")
        self.assertTrue((self.drafts_dir / note.filename).is_file())
        self.assertFalse((self.notes_dir / note.filename).exists())

    def test_edit_published_creates_draft_without_changing_source(self) -> None:
        published_before = (self.notes_dir / self.filename).read_bytes()
        opened = self.repository.load_for_edit(self.filename)
        self.assertEqual(opened.source_kind, "published")
        saved = self.repository.save_draft(self.filename, self.form(), opened.revision)
        self.assertEqual(saved.source_kind, "draft")
        self.assertEqual((self.notes_dir / self.filename).read_bytes(), published_before)
        self.assertIn("Draft body.", (self.drafts_dir / self.filename).read_text(encoding="utf-8"))

    def test_reopen_prefers_existing_draft(self) -> None:
        opened = self.repository.load_for_edit(self.filename)
        self.repository.save_draft(self.filename, self.form(body="Private version."), opened.revision)
        reopened = self.repository.load_for_edit(self.filename)
        self.assertEqual(reopened.source_kind, "draft")
        self.assertIn("Private version.", reopened.body)

    def test_rejects_path_traversal_and_symlink(self) -> None:
        with self.assertRaises(InvalidFilename):
            self.repository.load_for_edit("../config.yaml")
        target = self.root / "outside.md"
        target.write_text(PUBLISHED, encoding="utf-8")
        (self.drafts_dir / "2026-08-12-linked.md").symlink_to(target)
        with self.assertRaises(InvalidFilename):
            self.repository.load_for_edit("2026-08-12-linked.md")

    def test_rejects_filename_collision(self) -> None:
        with self.assertRaises(CollisionError):
            self.repository.create_draft(self.form(title="Existing note", slug="existing-note"))

    def test_reserved_slug_is_rejected_for_language(self) -> None:
        with self.assertRaises(CollisionError):
            self.repository.create_draft(self.form(title="Reserved", date="2026-08-11", slug="notes", lang="en"))

    def test_allows_same_slug_in_other_language(self) -> None:
        note = self.repository.create_draft(
            self.form(
                title="English note",
                date="2026-08-11",
                slug="existing-note",
                lang="en",
                note_id="2026-08-10-existing-note",
            )
        )
        self.assertEqual(note.form_values()["lang"], "en")
        self.assertEqual(note.form_values()["note_id"], "2026-08-10-existing-note")

    def test_detects_revision_conflict(self) -> None:
        opened = self.repository.load_for_edit(self.filename)
        saved = self.repository.save_draft(self.filename, self.form(), opened.revision)
        (self.drafts_dir / self.filename).write_text(PUBLISHED.replace("Published", "External"), encoding="utf-8")
        with self.assertRaises(RevisionConflict):
            self.repository.save_draft(self.filename, self.form(body="Overwrite"), saved.revision)

    def test_frontmatter_round_trip_preserves_unknown_fields(self) -> None:
        opened = self.repository.load_for_edit(self.filename)
        self.repository.save_draft(self.filename, self.form(), opened.revision)
        draft = parse_document((self.drafts_dir / self.filename).read_text(encoding="utf-8"))
        self.assertEqual(draft.metadata["custom"], {"nested": "preserved"})
        self.assertEqual(draft.metadata["title"], "Edited note")


if __name__ == "__main__":
    unittest.main()
