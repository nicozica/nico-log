from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from editor.app import create_app


class EditorAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "content" / "notes").mkdir(parents=True)
        (self.root / "content" / "drafts").mkdir(parents=True)
        self.app = create_app(self.root, testing=True)
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_index_and_new_draft_flow(self) -> None:
        index = self.client.get("/")
        self.assertEqual(index.status_code, 200)
        self.assertEqual(index.headers["Cache-Control"], "no-store")
        response = self.client.post(
            "/notes/new",
            data={
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


if __name__ == "__main__":
    unittest.main()
