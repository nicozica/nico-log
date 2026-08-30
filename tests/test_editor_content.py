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


SHARED_NOTE_ID = "2026-08-28-cuando-una-herramienta-deja-de-ser-un-experimento"
PUBLISHED_ES = f"""---
note_id: {SHARED_NOTE_ID}
lang: es
title: Cuando una herramienta deja de ser un experimento
date: 2026-08-28
tags:
  - automation
summary: Original summary
custom:
  nested: preserved
slug: cuando-una-herramienta-deja-de-ser-un-experimento
---

Publicado en espanol.
"""
PUBLISHED_EN = f"""---
note_id: {SHARED_NOTE_ID}
lang: en
title: When a Tool Stops Being an Experiment
date: 2026-08-28
tags:
  - automation
summary: English summary
slug: when-a-tool-stops-being-an-experiment
---

Published in English.
"""


class ContentRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.notes_dir = self.root / "content" / "notes"
        self.drafts_dir = self.root / "content" / "drafts"
        self.notes_dir.mkdir(parents=True)
        self.drafts_dir.mkdir(parents=True)
        self.es_filename = "2026-08-28-cuando-una-herramienta-deja-de-ser-un-experimento.md"
        self.en_filename = "2026-08-28-when-a-tool-stops-being-an-experiment.md"
        (self.notes_dir / self.es_filename).write_text(PUBLISHED_ES, encoding="utf-8")
        (self.notes_dir / self.en_filename).write_text(PUBLISHED_EN, encoding="utf-8")
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
            "slug": "edited-note",
            "lang": "es",
            "note_id": "",
            "body": "Draft body.",
        }
        values.update(overrides)
        return values

    def test_existing_english_note_loads_language_and_note_id(self) -> None:
        opened = self.repository.load_for_edit(self.en_filename)
        form = opened.form_values()
        self.assertEqual(form["lang"], "en")
        self.assertEqual(form["note_id"], SHARED_NOTE_ID)

    def test_existing_spanish_note_loads_language_and_note_id(self) -> None:
        opened = self.repository.load_for_edit(self.es_filename)
        form = opened.form_values()
        self.assertEqual(form["lang"], "es")
        self.assertEqual(form["note_id"], SHARED_NOTE_ID)

    def test_matching_files_expose_same_note_id(self) -> None:
        published = {note.filename: note for note in self.repository.list_published()}
        self.assertEqual(published[self.es_filename].note_id, SHARED_NOTE_ID)
        self.assertEqual(published[self.en_filename].note_id, SHARED_NOTE_ID)

    def test_save_preserves_existing_language_and_note_id_when_omitted(self) -> None:
        opened = self.repository.load_for_edit(self.en_filename)
        saved = self.repository.save_draft(
            self.en_filename,
            self.form(
                title="Edited English",
                date="2026-08-28",
                tags="automation, ai",
                summary="Updated summary",
                slug="when-a-tool-stops-being-an-experiment",
                lang="",
                note_id="",
                body="Updated English draft.",
            ),
            opened.revision,
        )
        draft = parse_document((self.drafts_dir / self.en_filename).read_text(encoding="utf-8"))
        self.assertEqual(saved.form_values()["lang"], "en")
        self.assertEqual(saved.form_values()["note_id"], SHARED_NOTE_ID)
        self.assertEqual(draft.metadata["lang"], "en")
        self.assertEqual(draft.metadata["note_id"], SHARED_NOTE_ID)

    def test_rejects_second_english_counterpart_for_same_note_id(self) -> None:
        with self.assertRaises(CollisionError):
            self.repository.create_draft(
                self.form(
                    title="Second English",
                    date="2026-08-29",
                    slug="second-english-version",
                    lang="en",
                    note_id=SHARED_NOTE_ID,
                    body="Another English body.",
                )
            )

    def test_create_new_draft(self) -> None:
        note = self.repository.create_draft(self.form(title="New note", date="2026-08-11", slug="new-note"))
        self.assertEqual(note.filename, "2026-08-11-new-note.md")
        self.assertTrue((self.drafts_dir / note.filename).is_file())
        self.assertFalse((self.notes_dir / note.filename).exists())

    def test_edit_published_creates_draft_without_changing_source(self) -> None:
        published_before = (self.notes_dir / self.es_filename).read_bytes()
        opened = self.repository.load_for_edit(self.es_filename)
        self.assertEqual(opened.source_kind, "published")
        saved = self.repository.save_draft(
            self.es_filename,
            self.form(
                title="Cuando una herramienta deja de ser un experimento",
                date="2026-08-28",
                tags="automation",
                summary="Original summary",
                slug="cuando-una-herramienta-deja-de-ser-un-experimento",
                body="Borrador privado.",
            ),
            opened.revision,
        )
        self.assertEqual(saved.source_kind, "draft")
        self.assertEqual((self.notes_dir / self.es_filename).read_bytes(), published_before)
        self.assertIn("Borrador privado.", (self.drafts_dir / self.es_filename).read_text(encoding="utf-8"))

    def test_reopen_prefers_existing_draft(self) -> None:
        opened = self.repository.load_for_edit(self.es_filename)
        self.repository.save_draft(
            self.es_filename,
            self.form(
                title="Cuando una herramienta deja de ser un experimento",
                date="2026-08-28",
                tags="automation",
                summary="Original summary",
                slug="cuando-una-herramienta-deja-de-ser-un-experimento",
                body="Private version.",
            ),
            opened.revision,
        )
        reopened = self.repository.load_for_edit(self.es_filename)
        self.assertEqual(reopened.source_kind, "draft")
        self.assertIn("Private version.", reopened.body)

    def test_rejects_path_traversal_and_symlink(self) -> None:
        with self.assertRaises(InvalidFilename):
            self.repository.load_for_edit("../config.yaml")
        target = self.root / "outside.md"
        target.write_text(PUBLISHED_ES, encoding="utf-8")
        (self.drafts_dir / "2026-08-12-linked.md").symlink_to(target)
        with self.assertRaises(InvalidFilename):
            self.repository.load_for_edit("2026-08-12-linked.md")

    def test_reserved_slug_is_rejected_for_language(self) -> None:
        with self.assertRaises(CollisionError):
            self.repository.create_draft(self.form(title="Reserved", date="2026-08-11", slug="notes", lang="en"))

    def test_allows_same_slug_in_other_language(self) -> None:
        note = self.repository.create_draft(
            self.form(
                title="Another English note",
                date="2026-08-11",
                slug="cuando-una-herramienta-deja-de-ser-un-experimento",
                lang="en",
                note_id="2026-08-11-another-english-note",
            )
        )
        self.assertEqual(note.form_values()["lang"], "en")
        self.assertEqual(note.form_values()["note_id"], "2026-08-11-another-english-note")

    def test_detects_revision_conflict(self) -> None:
        opened = self.repository.load_for_edit(self.es_filename)
        saved = self.repository.save_draft(
            self.es_filename,
            self.form(
                title="Cuando una herramienta deja de ser un experimento",
                date="2026-08-28",
                tags="automation",
                summary="Original summary",
                slug="cuando-una-herramienta-deja-de-ser-un-experimento",
            ),
            opened.revision,
        )
        (self.drafts_dir / self.es_filename).write_text(PUBLISHED_ES.replace("Publicado", "Externo"), encoding="utf-8")
        with self.assertRaises(RevisionConflict):
            self.repository.save_draft(
                self.es_filename,
                self.form(
                    title="Cuando una herramienta deja de ser un experimento",
                    date="2026-08-28",
                    tags="automation",
                    summary="Original summary",
                    slug="cuando-una-herramienta-deja-de-ser-un-experimento",
                    body="Overwrite",
                ),
                saved.revision,
            )

    def test_frontmatter_round_trip_preserves_unknown_fields(self) -> None:
        opened = self.repository.load_for_edit(self.es_filename)
        self.repository.save_draft(
            self.es_filename,
            self.form(
                title="Cuando una herramienta deja de ser un experimento",
                date="2026-08-28",
                tags="automation",
                summary="Original summary",
                slug="cuando-una-herramienta-deja-de-ser-un-experimento",
            ),
            opened.revision,
        )
        draft = parse_document((self.drafts_dir / self.es_filename).read_text(encoding="utf-8"))
        self.assertEqual(draft.metadata["custom"], {"nested": "preserved"})
        self.assertEqual(draft.metadata["title"], "Cuando una herramienta deja de ser un experimento")


if __name__ == "__main__":
    unittest.main()
