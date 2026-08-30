from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from editor.app import _format_date_ar, create_app
from editor.publishing import DeploymentResult


class FakePublisher:
    def deploy(self) -> DeploymentResult:
        return DeploymentResult(True, "ok")


class DateFormatTests(unittest.TestCase):
    def test_iso_to_argentine(self) -> None:
        self.assertEqual(_format_date_ar("2026-08-28"), "28/08/2026")

    def test_empty_returns_empty(self) -> None:
        self.assertEqual(_format_date_ar(""), "")

    def test_invalid_returns_as_is(self) -> None:
        self.assertEqual(_format_date_ar("not-a-date"), "not-a-date")
        self.assertEqual(_format_date_ar("2026-08"), "2026-08")


class PaginationTests(unittest.TestCase):
    PAGE_SIZE = 10

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.notes_dir = self.root / "content" / "notes"
        self.drafts_dir = self.root / "content" / "drafts"
        self.notes_dir.mkdir(parents=True)
        self.drafts_dir.mkdir(parents=True)
        # Write 15 published conceptual notes (ES only) + 1 ES/EN pair (counts as 1 group)
        # Total: 13 solo ES + 1 ES/EN pair = 14... let's do 14 solo + 1 pair = 15 groups
        for i in range(1, 15):
            self._write_note(
                self.notes_dir,
                f"2026-01-{i:02d}-nota-{i:02d}-es.md",
                note_id=f"2026-01-{i:02d}-nota-{i:02d}",
                language="es",
                title=f"Nota {i:02d} ES",
            )
        # Pair: note 15 has ES + EN (same note_id → 1 conceptual group)
        self._write_note(
            self.notes_dir,
            "2026-01-15-nota-15-es.md",
            note_id="2026-01-15-nota-15",
            language="es",
            title="Nota 15 ES",
        )
        self._write_note(
            self.notes_dir,
            "2026-01-15-nota-15-en.md",
            note_id="2026-01-15-nota-15",
            language="en",
            title="Note 15 EN",
        )
        self.app = create_app(self.root, testing=True, publisher=FakePublisher())
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_note(
        self,
        directory: Path,
        filename: str,
        *,
        note_id: str,
        language: str,
        title: str,
        tags: list[str] | None = None,
    ) -> None:
        date = filename[:10]
        directory.joinpath(filename).write_text(
            "\n".join(
                [
                    "---",
                    f"note_id: {note_id}",
                    f"lang: {language}",
                    f"title: {title}",
                    f"date: {date}",
                    "tags:",
                    *(f"  - {tag}" for tag in (tags or [])),
                    f"slug: {note_id}",
                    "summary: test",
                    "---",
                    "",
                    "Body.",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def test_page1_has_10_groups(self) -> None:
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        # 10 note-row note-group-row articles on page 1
        self.assertEqual(resp.data.count(b'class="note-row note-group-row"'), 10)

    def test_page2_has_5_groups(self) -> None:
        resp = self.client.get("/?page=2")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.count(b'class="note-row note-group-row"'), 5)

    def test_es_en_pair_not_split(self) -> None:
        # The ES/EN pair must appear on the same page, never split
        found_es = found_en = False
        for page_num in (1, 2):
            resp = self.client.get(f"/?page={page_num}")
            has_es = b"Nota 15 ES" in resp.data
            has_en = b"Note 15 EN" in resp.data
            if has_es or has_en:
                self.assertTrue(has_es and has_en, f"Pair split across pages; page {page_num} has ES={has_es} EN={has_en}")
                found_es = found_en = True
        self.assertTrue(found_es and found_en, "Pair not found on any page")

    def test_filter_before_pagination(self) -> None:
        # Searching "nota 01" should find only 1 group → page 1, no page 2
        resp = self.client.get("/?q=nota+01")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Nota 01 ES", resp.data)
        self.assertNotIn(b"Siguiente", resp.data)

    def test_query_survives_pagination_links(self) -> None:
        resp = self.client.get("/?page=1")
        self.assertEqual(resp.status_code, 200)
        # Next link must include page=2
        self.assertIn(b"page=2", resp.data)

    def test_drafts_unpaginated(self) -> None:
        # Write 12 drafts
        for i in range(1, 13):
            self._write_note(
                self.drafts_dir,
                f"2025-06-{i:02d}-draft-{i:02d}.md",
                note_id=f"2025-06-{i:02d}-draft-{i:02d}",
                language="es",
                title=f"Draft {i:02d}",
            )
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        # All 12 drafts should appear (no pagination)
        for i in range(1, 13):
            self.assertIn(f"Draft {i:02d}".encode(), resp.data)

    def test_invalid_page_defaults_to_1(self) -> None:
        for bad in ("abc", "-5", "0", ""):
            resp = self.client.get(f"/?page={bad}")
            self.assertEqual(resp.status_code, 200)
            # Should render page 1: contains at least some note-group rows
            self.assertIn(b'class="note-row note-group-row"', resp.data)

    def test_page_beyond_last_clamps(self) -> None:
        resp = self.client.get("/?page=999")
        self.assertEqual(resp.status_code, 200)
        # Should render last page (page 2, 5 groups)
        self.assertEqual(resp.data.count(b'class="note-row note-group-row"'), 5)

    def test_total_count_shows_all_groups(self) -> None:
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        # section-title span shows "15" (total, not page slice)
        self.assertIn(b">15<", resp.data)
