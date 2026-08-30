from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from editor.app import create_app
from editor.publishing import DeploymentResult


PUBLISHED = """---
title: Existing note
date: 2026-08-10
tags:
  - python
custom:
  preserved: true
---

Published body.
"""


class FakePublisher:
    def __init__(self, results: list[DeploymentResult] | None = None) -> None:
        self.calls = 0
        self.results = results or [DeploymentResult(True, "Build y deploy completados correctamente.")]

    def deploy(self) -> DeploymentResult:
        self.calls += 1
        index = min(self.calls - 1, len(self.results) - 1)
        return self.results[index]


class EditorPublishTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.notes_dir = self.root / "content" / "notes"
        self.drafts_dir = self.root / "content" / "drafts"
        self.notes_dir.mkdir(parents=True)
        self.drafts_dir.mkdir(parents=True)
        self.filename = "2026-08-10-existing-note.md"
        (self.notes_dir / self.filename).write_text(PUBLISHED, encoding="utf-8")
        self.publisher = FakePublisher()
        self.app = create_app(self.root, testing=True, publisher=self.publisher)
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["_csrf_token"] = "publish-csrf-token"
        self.repository = self.app.extensions["content_repository"]

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
            "body": "# Draft body\n\n<script>parent.document.body.remove()</script>",
        }
        values.update(overrides)
        return values

    def save_existing_draft(self) -> object:
        opened = self.repository.load_for_edit(self.filename)
        return self.repository.save_draft(self.filename, self.form(), opened.revision)

    def publish(self, filename: str, draft_revision: str, published_revision: str):
        return self.client.post(
            f"/notes/{filename}/publish",
            data={
                "_csrf_token": "publish-csrf-token",
                "draft_revision": draft_revision,
                "published_revision": published_revision,
            },
        )

    def test_publish_directly_from_edit_uses_current_form_state(self) -> None:
        opened = self.repository.load_for_edit(self.filename)
        latest_body = "# Estado visual más reciente\n\nContenido todavía no guardado."

        response = self.client.post(
            f"/notes/{self.filename}/edit",
            data={
                "_csrf_token": "publish-csrf-token",
                "action": "publish",
                "revision": opened.revision,
                "published_revision": opened.published_revision,
                **self.form(body=latest_body),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(latest_body.encode(), (self.notes_dir / self.filename).read_bytes())
        self.assertFalse((self.drafts_dir / self.filename).exists())
        self.assertEqual(self.publisher.calls, 1)

    def test_save_draft_keeps_source_and_paragraphs_independent(self) -> None:
        opened = self.repository.load_for_edit(self.filename)
        published_before = (self.notes_dir / self.filename).read_bytes()
        paragraphs = "Primer párrafo.\n\nSegundo párrafo.\n\nTercer párrafo."

        response = self.client.post(
            f"/notes/{self.filename}/edit",
            data={
                "_csrf_token": "publish-csrf-token",
                "action": "save",
                "revision": opened.revision,
                "published_revision": opened.published_revision,
                **self.form(body=paragraphs),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual((self.notes_dir / self.filename).read_bytes(), published_before)
        reopened = self.repository.load_for_edit(self.filename)
        reopened_body = reopened.form_values()["body"].strip()
        self.assertEqual(reopened_body, paragraphs)
        self.assertEqual(reopened_body.split("\n\n"), [
            "Primer párrafo.",
            "Segundo párrafo.",
            "Tercer párrafo.",
        ])
        self.assertEqual(self.publisher.calls, 0)

    def test_draft_edit_links_to_private_preview_in_new_tab(self) -> None:
        self.save_existing_draft()
        edit = self.client.get(f"/notes/{self.filename}/edit")

        self.assertEqual(edit.status_code, 200)
        self.assertIn(
            f"href=\"/notes/{self.filename}/preview\" target=\"_blank\" rel=\"noopener\"".encode(),
            edit.data,
        )
        preview = self.client.get(f"/notes/{self.filename}/preview")
        self.assertIn(b"sandbox=\"\"", preview.data)

    def test_preview_does_not_mutate_source_and_is_sandboxed(self) -> None:
        draft = self.save_existing_draft()
        published_before = (self.notes_dir / self.filename).read_bytes()
        draft_before = (self.drafts_dir / self.filename).read_bytes()

        page = self.client.get(f"/notes/{self.filename}/preview")
        document = self.client.get(f"/notes/{self.filename}/preview/document")

        self.assertEqual(page.status_code, 200)
        self.assertIn(b'sandbox=""', page.data)
        self.assertIn(b"VISTA PREVIA", page.data)
        self.assertIn(b"<h1>Draft body</h1>", document.data)
        self.assertIn(b"<script>parent.document.body.remove()</script>", document.data)
        self.assertIn("sandbox; default-src 'none'", document.headers["Content-Security-Policy"])
        self.assertNotIn("X-Frame-Options", document.headers)
        self.assertEqual((self.notes_dir / self.filename).read_bytes(), published_before)
        self.assertEqual((self.drafts_dir / self.filename).read_bytes(), draft_before)
        self.assertEqual(draft.source_kind, "draft")
        self.assertEqual(self.publisher.calls, 0)

    def test_published_edit_replaces_source_and_cleans_draft(self) -> None:
        draft = self.save_existing_draft()
        response = self.publish(self.filename, draft.revision, draft.published_revision)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Publicaci", response.data)
        self.assertIn(b"https://www.nico.com.ar/es/existing-note/", response.data)
        self.assertIn(
            b"href=\"https://www.nico.com.ar/es/existing-note/\" target=\"_blank\" rel=\"noopener\"",
            response.data,
        )
        self.assertIn(b"Draft body", (self.notes_dir / self.filename).read_bytes())
        self.assertIn(b"preserved: true", (self.notes_dir / self.filename).read_bytes())
        self.assertFalse((self.drafts_dir / self.filename).exists())
        self.assertEqual(self.publisher.calls, 1)

    def test_new_note_publication_creates_source(self) -> None:
        draft = self.repository.create_draft(
            self.form(title="Brand new", date="2026-08-11", slug="brand-new", body="New body.")
        )
        response = self.publish(draft.filename, draft.revision, draft.published_revision)
        self.assertEqual(response.status_code, 200)
        self.assertTrue((self.notes_dir / draft.filename).is_file())
        self.assertFalse((self.drafts_dir / draft.filename).exists())
        self.assertEqual(self.publisher.calls, 1)

    def test_invalid_metadata_blocks_source_and_deploy(self) -> None:
        filename = "2026-08-12-invalid-tags.md"
        draft_path = self.drafts_dir / filename
        draft_path.write_text(
            "---\ntitle: Invalid\ndate: 2026-08-12\ntags: not-a-list\n---\n\nBody.\n",
            encoding="utf-8",
        )
        draft = self.repository.load_for_edit(filename)
        response = self.publish(filename, draft.revision, draft.published_revision)
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"lista de strings", response.data)
        self.assertFalse((self.notes_dir / filename).exists())
        self.assertTrue(draft_path.exists())
        self.assertEqual(self.publisher.calls, 0)

    def test_malformed_yaml_blocks_source_and_deploy(self) -> None:
        filename = "2026-08-12-invalid-yaml.md"
        draft_path = self.drafts_dir / filename
        draft_path.write_text(
            "---\ntitle: [unterminated\ndate: 2026-08-12\ntags: []\n---\n\nBody.\n",
            encoding="utf-8",
        )
        raw = draft_path.read_bytes()
        revision = f"draft:{hashlib.sha256(raw).hexdigest()}"
        response = self.publish(filename, revision, "published:none")
        self.assertEqual(response.status_code, 400)
        self.assertFalse((self.notes_dir / filename).exists())
        self.assertTrue(draft_path.exists())
        self.assertEqual(self.publisher.calls, 0)

    def test_slug_collision_blocks_publication(self) -> None:
        filename = "2026-08-12-collision.md"
        draft_path = self.drafts_dir / filename
        draft_path.write_text(
            "---\ntitle: Collision\ndate: 2026-08-12\ntags: []\nslug: existing-note\n---\n\nBody.\n",
            encoding="utf-8",
        )
        draft = self.repository.load_for_edit(filename)
        response = self.publish(filename, draft.revision, draft.published_revision)
        self.assertEqual(response.status_code, 409)
        self.assertIn(b"ya est", response.data)
        self.assertFalse((self.notes_dir / filename).exists())
        self.assertTrue(draft_path.exists())
        self.assertEqual(self.publisher.calls, 0)

    def test_revision_conflict_blocks_publication(self) -> None:
        draft = self.save_existing_draft()
        (self.drafts_dir / self.filename).write_text(PUBLISHED.replace("Published", "External"), encoding="utf-8")
        published_before = (self.notes_dir / self.filename).read_bytes()
        response = self.publish(self.filename, draft.revision, draft.published_revision)
        self.assertEqual(response.status_code, 409)
        self.assertEqual((self.notes_dir / self.filename).read_bytes(), published_before)
        self.assertEqual(self.publisher.calls, 0)

    def test_published_source_revision_conflict_blocks_publication(self) -> None:
        draft = self.save_existing_draft()
        externally_changed = PUBLISHED.replace("Published body.", "Changed manually.")
        (self.notes_dir / self.filename).write_text(externally_changed, encoding="utf-8")
        response = self.publish(self.filename, draft.revision, draft.published_revision)
        self.assertEqual(response.status_code, 409)
        self.assertEqual((self.notes_dir / self.filename).read_text(encoding="utf-8"), externally_changed)
        self.assertTrue((self.drafts_dir / self.filename).exists())
        self.assertIn(draft.published_revision.encode(), response.data)
        self.assertEqual(self.publisher.calls, 0)

    def test_deploy_failure_preserves_source_and_allows_retry(self) -> None:
        self.publisher.results = [
            DeploymentResult(False, "El servicio de publicación terminó con error."),
            DeploymentResult(True, "Build y deploy completados correctamente."),
        ]
        draft = self.save_existing_draft()
        response = self.publish(self.filename, draft.revision, draft.published_revision)
        self.assertEqual(response.status_code, 502)
        self.assertTrue((self.notes_dir / self.filename).is_file())
        self.assertFalse((self.drafts_dir / self.filename).exists())
        published_before_retry = (self.notes_dir / self.filename).read_bytes()
        self.assertIn(b"Reintentar actualizaci", response.data)

        retry = self.client.post(
            f"/notes/{self.filename}/deploy",
            data={"_csrf_token": "publish-csrf-token"},
        )
        self.assertEqual(retry.status_code, 200)
        self.assertEqual((self.notes_dir / self.filename).read_bytes(), published_before_retry)
        self.assertEqual(self.publisher.calls, 2)

    def test_publish_and_retry_require_csrf(self) -> None:
        draft = self.save_existing_draft()
        response = self.client.post(
            f"/notes/{self.filename}/publish",
            data={"draft_revision": draft.revision, "published_revision": draft.published_revision},
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue((self.drafts_dir / self.filename).exists())
        self.assertEqual(self.publisher.calls, 0)

    def test_path_payload_cannot_reach_publisher(self) -> None:
        response = self.client.post(
            "/notes/..%2F..%2Fetc%2Fpasswd/publish",
            data={"_csrf_token": "publish-csrf-token"},
        )
        self.assertIn(response.status_code, {404, 405})
        self.assertEqual(self.publisher.calls, 0)


if __name__ == "__main__":
    unittest.main()
