from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from editor.app import create_app
from editor.publishing import DeploymentResult


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
        (self.root / "content" / "notes").mkdir(parents=True)
        (self.root / "content" / "drafts").mkdir(parents=True)
        self.publisher = FakePublisher()
        self.app = create_app(self.root, testing=True, publisher=self.publisher)
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["_csrf_token"] = "test-csrf-token"

    def tearDown(self) -> None:
        self.temporary.cleanup()

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
        self.assertEqual(self.client.get(response.headers["Location"]).status_code, 200)

    def test_conflict_response_requires_reload(self) -> None:
        filename = "2026-08-16-existing.md"
        published = self.root / "content" / "notes" / filename
        published.write_text(
            "---\ntitle: Existing\ndate: 2026-08-16\ntags: []\n---\n\nOriginal.\n",
            encoding="utf-8",
        )
        repository = self.app.extensions["content_repository"]
        opened = repository.load_for_edit(filename)
        published.write_text(
            "---\ntitle: Existing\ndate: 2026-08-16\ntags: []\n---\n\nChanged elsewhere.\n",
            encoding="utf-8",
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
            },
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn("cambió desde que lo abriste".encode(), response.data)
        self.assertIn(opened.revision.encode(), response.data)
        self.assertFalse((self.root / "content" / "drafts" / filename).exists())

    def test_editor_ux_assets_titles_and_clickable_rows(self) -> None:
        filename = "2026-08-16-existing.md"
        (self.root / "content" / "notes" / filename).write_text(
            "---\ntitle: Existing\ndate: 2026-08-16\ntags: []\n---\n\nOriginal.\n",
            encoding="utf-8",
        )

        index = self.client.get("/")
        self.assertIn(b"<title>Editor \xc2\xb7 Notas</title>", index.data)
        self.assertIn(b'class="note-row"', index.data)
        self.assertIn(f'href="/notes/{filename}/edit"'.encode(), index.data)
        self.assertNotIn(b">Editar</a>", index.data)
        self.assertIn(b"data-theme-toggle", index.data)
        self.assertIn(b'href="/favicon.svg"', index.data)

        edit = self.client.get(f"/notes/{filename}/edit")
        self.assertIn(b"<title>Editor \xc2\xb7 Existing</title>", edit.data)
        self.assertIn(b"toastui-editor-3.2.2/toastui-editor-all.min.js", edit.data)
        self.assertIn(b"data-markdown-source", edit.data)
        self.assertIn(b"data-wysiwyg-editor", edit.data)
        self.assertIn(b">Fecha</label>", edit.data)
        self.assertNotIn(b"Fecha ISO", edit.data)
        self.assertIn(b"placeholder=\"Filtrar por t\xc3\xadtulo, tag o archivo\"", index.data)
        self.assertIn(b"aria-label=\"Filtrar notas\"", index.data)
        self.assertNotIn(b"<label for=\"q\">Buscar</label>", index.data)
        self.assertIn(b"name=\"action\" value=\"save\"", edit.data)
        self.assertIn(b"name=\"action\" value=\"publish\"", edit.data)

        editor_script = (Path(__file__).parents[1] / "editor" / "static" / "editor.js").read_text(encoding="utf-8")
        self.assertIn("if (markdownEditor) body.value = markdownEditor.getMarkdown();", editor_script)
        self.assertNotIn("markdownEditor && editorDirty", editor_script)

        favicon = self.client.get("/favicon.svg")
        self.assertEqual(favicon.status_code, 200)
        favicon.close()

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
        published = self.root / "content" / "notes" / filename
        published.write_text(
            "---\ntitle: Existing\ndate: 2026-08-16\ntags: []\n---\n\nOriginal.\n",
            encoding="utf-8",
        )
        opened = self.app.extensions["content_repository"].load_for_edit(filename)
        save = self.client.post(
            f"/notes/{filename}/edit",
            data={
                "title": "Existing",
                "date": "2026-08-16",
                "tags": "",
                "slug": "existing",
                "body": "Rejected edit.",
                "revision": opened.revision,
            },
        )
        self.assertEqual(save.status_code, 400)
        self.assertFalse((self.root / "content" / "drafts" / filename).exists())


if __name__ == "__main__":
    unittest.main()
