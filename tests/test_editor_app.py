from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from editor.app import create_app
from editor.content import parse_document
from editor.publishing import DeploymentResult


PAIR_NOTE_ID = "2026-08-28-cuando-una-herramienta-deja-de-ser-un-experimento"
UNPAIRED_NOTE_ID = "2026-08-19-fallback-4g-a-lo-croto"


class FakePublisher:
    def __init__(self) -> None:
        self.calls = 0

    def deploy(self) -> DeploymentResult:
        self.calls += 1
        return DeploymentResult(True, "Build y deploy de prueba completados.")


class EditorAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.notes_dir = self.root / "content" / "notes"
        self.drafts_dir = self.root / "content" / "drafts"
        self.notes_dir.mkdir(parents=True)
        self.drafts_dir.mkdir(parents=True)
        self.publisher = FakePublisher()
        self._write_note(
            self.notes_dir,
            "2026-08-28-cuando-una-herramienta-deja-de-ser-un-experimento.md",
            note_id=PAIR_NOTE_ID,
            language="es",
            title="Cuando una herramienta deja de ser un experimento",
            slug="cuando-una-herramienta-deja-de-ser-un-experimento",
            summary="Resumen ES",
            body="Cuerpo ES.",
            tags=["automation", "drupal"],
        )
        self._write_note(
            self.notes_dir,
            "2026-08-28-when-a-tool-stops-being-an-experiment.md",
            note_id=PAIR_NOTE_ID,
            language="en",
            title="When a Tool Stops Being an Experiment",
            slug="when-a-tool-stops-being-an-experiment",
            summary="Summary EN",
            body="Body EN.",
            tags=["automation", "drupal"],
        )
        self._write_note(
            self.notes_dir,
            "2026-08-19-fallback-4g-a-lo-croto.md",
            note_id=UNPAIRED_NOTE_ID,
            language="es",
            title="Fallback 4G a lo croto",
            slug="fallback-4g-a-lo-croto",
            summary="Resumen fallback",
            body="Cuerpo fallback.",
            tags=["networking"],
        )
        self.app = create_app(self.root, testing=True, publisher=self.publisher)
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["_csrf_token"] = "test-csrf-token"

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
        slug: str,
        summary: str,
        body: str,
        tags: list[str],
    ) -> None:
        directory.joinpath(filename).write_text(
            "\n".join(
                [
                    "---",
                    f"note_id: {note_id}",
                    f"lang: {language}",
                    f"title: {title}",
                    f"date: {filename[:10]}",
                    "tags:",
                    *(f"  - {tag}" for tag in tags),
                    f"slug: {slug}",
                    f"summary: {summary}",
                    "---",
                    "",
                    body,
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def test_index_and_new_draft_flow(self) -> None:
        index = self.client.get("/")
        self.assertEqual(index.status_code, 200)
        self.assertEqual(index.headers["Cache-Control"], "no-store")
        response = self.client.post(
            "/notes/new",
            data={
                "_csrf_token": "test-csrf-token",
                "title": "From Flask",
                "date": "2026-08-16",
                "tags": "flask, editor",
                "summary": "Private",
                "slug": "from-flask",
                "body": "Draft only.",
            },
        )
        self.assertEqual(response.status_code, 302)
        draft = self.root / "content" / "drafts" / "2026-08-16-from-flask.md"
        self.assertTrue(draft.is_file())
        self.assertFalse((self.root / "content" / "notes" / draft.name).exists())
        parsed = parse_document(draft.read_text(encoding="utf-8"))
        self.assertNotIn("lang", parsed.metadata)
        self.assertEqual(self.app.extensions["content_repository"].load_for_edit(draft.name).form_values()["lang"], "es")
        self.assertEqual(self.client.get(response.headers["Location"]).status_code, 200)

    def test_conflict_response_requires_reload(self) -> None:
        filename = "2026-08-16-existing.md"
        self._write_note(
            self.notes_dir,
            filename,
            note_id="2026-08-16-existing",
            language="es",
            title="Existing",
            slug="existing",
            summary="",
            body="Original.",
            tags=[],
        )
        repository = self.app.extensions["content_repository"]
        opened = repository.load_for_edit(filename)
        self._write_note(
            self.notes_dir,
            filename,
            note_id="2026-08-16-existing",
            language="es",
            title="Existing",
            slug="existing",
            summary="",
            body="Changed elsewhere.",
            tags=[],
        )
        response = self.client.post(
            f"/notes/{filename}/edit",
            data={
                "_csrf_token": "test-csrf-token",
                "title": "Existing",
                "date": "2026-08-16",
                "tags": "",
                "summary": "",
                "slug": "existing",
                "body": "My edit.",
                "revision": opened.revision,
                "published_revision": opened.published_revision,
            },
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn("cambió desde que lo abriste".encode(), response.data)
        self.assertIn(opened.revision.encode(), response.data)
        self.assertFalse((self.root / "content" / "drafts" / filename).exists())

    def test_index_groups_paired_and_unpaired_notes(self) -> None:
        index = self.client.get("/")
        self.assertEqual(index.status_code, 200)
        self.assertEqual(index.data.count(b'class="note-row note-group-row"'), 2)
        self.assertIn(b'<h2>Publicadas</h2>', index.data)
        self.assertIn(b'<span>2</span>', index.data)
        self.assertIn(b'href="/notes/2026-08-28-cuando-una-herramienta-deja-de-ser-un-experimento.md/edit"', index.data)
        self.assertIn(b'href="/notes/2026-08-28-when-a-tool-stops-being-an-experiment.md/edit"', index.data)
        self.assertIn(b'href="/notes/2026-08-19-fallback-4g-a-lo-croto.md/edit"', index.data)

    def test_filtering_finds_group_using_either_language_title(self) -> None:
        english = self.client.get("/?q=experiment")
        spanish = self.client.get("/?q=herramienta")
        self.assertEqual(english.status_code, 200)
        self.assertEqual(spanish.status_code, 200)
        self.assertEqual(english.data.count(b'class="note-row note-group-row"'), 1)
        self.assertEqual(spanish.data.count(b'class="note-row note-group-row"'), 1)
        self.assertIn(b'When a Tool Stops Being an Experiment', english.data)
        self.assertIn(b'Cuando una herramienta deja de ser un experimento', spanish.data)

    def test_edit_page_shows_version_switch_and_read_only_language(self) -> None:
        edit = self.client.get("/notes/2026-08-28-when-a-tool-stops-being-an-experiment.md/edit")
        self.assertIn(b'When a Tool Stops Being an Experiment', edit.data)
        self.assertIn(b'href="/notes/2026-08-28-cuando-una-herramienta-deja-de-ser-un-experimento.md/edit"', edit.data)
        self.assertIn(b'class="badge version-lang-badge">EN<', edit.data)
        self.assertIn(b'class="badge version-lang-badge">ES<', edit.data)
        self.assertNotIn(b'<select id="lang"', edit.data)
        self.assertNotIn(b'name="note_id"', edit.data)
        self.assertNotIn(b'ID compartido', edit.data)

    def test_existing_note_submission_preserves_language_and_note_id_without_fields(self) -> None:
        repository = self.app.extensions["content_repository"]
        filename = "2026-08-28-when-a-tool-stops-being-an-experiment.md"
        opened = repository.load_for_edit(filename)
        response = self.client.post(
            f"/notes/{filename}/edit",
            data={
                "_csrf_token": "test-csrf-token",
                "action": "save",
                "title": "When a Tool Stops Being an Experiment",
                "date": "2026-08-28",
                "tags": "automation, drupal",
                "summary": "Updated summary",
                "slug": "when-a-tool-stops-being-an-experiment",
                "body": "Updated English draft.",
                "revision": opened.revision,
                "published_revision": opened.published_revision,
            },
        )
        self.assertEqual(response.status_code, 302)
        draft = parse_document((self.drafts_dir / filename).read_text(encoding="utf-8"))
        self.assertEqual(draft.metadata["lang"], "en")
        self.assertEqual(draft.metadata["note_id"], PAIR_NOTE_ID)

    def test_version_switch_targets_correct_editor_urls(self) -> None:
        edit = self.client.get("/notes/2026-08-28-cuando-una-herramienta-deja-de-ser-un-experimento.md/edit")
        self.assertIn(b'action="/notes/2026-08-28-cuando-una-herramienta-deja-de-ser-un-experimento.md/edit"', edit.data)
        self.assertIn(b'href="/notes/2026-08-28-when-a-tool-stops-being-an-experiment.md/edit"', edit.data)

    def test_create_english_version_gets_same_note_id(self) -> None:
        route = "/notes/2026-08-19-fallback-4g-a-lo-croto.md/translations/en/new"
        page = self.client.get(route)
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'Crear versi\xc3\xb3n EN', page.data)
        self.assertIn(b'Fallback 4G a lo croto', page.data)

        response = self.client.post(
            route,
            data={
                "_csrf_token": "test-csrf-token",
                "action": "save",
                "title": "Redundant Internet on a Budget",
                "date": "2026-08-19",
                "tags": "networking",
                "summary": "English summary",
                "slug": "redundant-internet-on-a-budget",
                "body": "English body only.",
            },
        )
        self.assertEqual(response.status_code, 302)
        draft_path = self.drafts_dir / "2026-08-19-redundant-internet-on-a-budget.md"
        self.assertTrue(draft_path.exists())
        draft = parse_document(draft_path.read_text(encoding="utf-8"))
        self.assertEqual(draft.metadata["lang"], "en")
        self.assertEqual(draft.metadata["note_id"], UNPAIRED_NOTE_ID)
        self.assertEqual(draft.body.strip(), "English body only.")

    def test_duplicate_english_creation_is_rejected(self) -> None:
        response = self.client.get("/notes/2026-08-28-cuando-una-herramienta-deja-de-ser-un-experimento.md/translations/en/new")
        self.assertEqual(response.status_code, 409)
        self.assertIn(b'La versi\xc3\xb3n EN de esta nota ya existe.', response.data)

    def test_index_shows_independent_publication_states(self) -> None:
        repository = self.app.extensions["content_repository"]
        repository.create_draft(
            {
                "title": "Redundant Internet on a Budget",
                "date": "2026-08-19",
                "tags": "networking",
                "summary": "English summary",
                "slug": "redundant-internet-on-a-budget",
                "lang": "en",
                "note_id": UNPAIRED_NOTE_ID,
                "body": "English draft.",
            }
        )
        index = self.client.get(f"/?q={UNPAIRED_NOTE_ID}")
        self.assertEqual(index.status_code, 200)
        self.assertIn(b'Publicada', index.data)
        self.assertIn(b'Borrador', index.data)
        self.assertIn(b'Redundant Internet on a Budget', index.data)
        self.assertIn(b'Fallback 4G a lo croto', index.data)

    def test_production_session_cookie_is_secure(self) -> None:
        production_app = create_app(self.root, publisher=self.publisher)
        self.assertTrue(production_app.config["SESSION_COOKIE_SECURE"])
        self.assertTrue(production_app.config["SESSION_COOKIE_HTTPONLY"])
        self.assertEqual(production_app.config["SESSION_COOKIE_SAMESITE"], "Strict")

    def test_state_changing_routes_require_csrf(self) -> None:
        with self.client.session_transaction() as session:
            session.pop("_csrf_token", None)
        response = self.client.post(
            "/notes/new",
            data={"title": "Rejected", "date": "2026-08-16", "slug": "rejected"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"CSRF", response.data)
        self.assertEqual(list((self.root / "content" / "drafts").iterdir()), [])

        filename = "2026-08-16-existing.md"
        self._write_note(
            self.notes_dir,
            filename,
            note_id="2026-08-16-existing",
            language="es",
            title="Existing",
            slug="existing",
            summary="",
            body="Original.",
            tags=[],
        )
        opened = self.app.extensions["content_repository"].load_for_edit(filename)
        save = self.client.post(
            f"/notes/{filename}/edit",
            data={
                "title": "Existing",
                "date": "2026-08-16",
                "tags": "",
                "summary": "",
                "slug": "existing",
                "body": "Rejected edit.",
                "revision": opened.revision,
                "published_revision": opened.published_revision,
            },
        )
        self.assertEqual(save.status_code, 400)
        self.assertFalse((self.root / "content" / "drafts" / filename).exists())


if __name__ == "__main__":
    unittest.main()
