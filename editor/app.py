from __future__ import annotations

import os
import hmac
import secrets
from datetime import date
from pathlib import Path
from typing import Any

from flask import Flask, Response, abort, redirect, render_template, request, send_from_directory, session, url_for

from generator.lib.notes import render_markdown

from .content import (
    CollisionError,
    ContentRepository,
    DraftCleanupError,
    InvalidFilename,
    NoteNotFound,
    RevisionConflict,
    ValidationError,
)
from .publishing import DeploymentResult, SystemdPublisher


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SITE_URL = "https://www.nico.com.ar"


def create_app(
    project_root: Path | str | None = None,
    *,
    testing: bool = False,
    publisher: SystemdPublisher | None = None,
) -> Flask:
    app = Flask(__name__)
    app.config.update(
        MAX_CONTENT_LENGTH=768 * 1024,
        SECRET_KEY=os.environ.get("NICO_EDITOR_SECRET_KEY") or secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_SECURE=not testing,
        TESTING=testing,
    )
    repository = ContentRepository(project_root or PROJECT_ROOT)
    app.extensions["content_repository"] = repository
    app.extensions["publisher"] = publisher or SystemdPublisher()

    def csrf_token() -> str:
        token = session.get("_csrf_token")
        if not isinstance(token, str):
            token = secrets.token_urlsafe(32)
            session["_csrf_token"] = token
        return token

    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def enforce_csrf() -> None:
        if request.method != "POST":
            return
        expected = session.get("_csrf_token", "")
        submitted = request.form.get("_csrf_token", "")
        if not (
            isinstance(expected, str)
            and expected
            and isinstance(submitted, str)
            and hmac.compare_digest(expected, submitted)
        ):
            abort(400, description="La protección CSRF rechazó la solicitud. Recargá la página.")

    @app.after_request
    def private_editor_headers(response: Response) -> Response:
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        if request.endpoint == "preview_document":
            response.headers["Content-Security-Policy"] = (
                "sandbox; default-src 'none'; img-src https://www.nico.com.ar data:; "
                "style-src 'unsafe-inline'; form-action 'none'; frame-ancestors 'self'; base-uri 'none'"
            )
        else:
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
                "script-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
            )
        return response

    @app.get("/favicon.svg")
    def favicon_svg() -> Response:
        return send_from_directory(PROJECT_ROOT / "static", "favicon.svg", mimetype="image/svg+xml")

    @app.get("/favicon.ico")
    def favicon_ico() -> Response:
        return send_from_directory(PROJECT_ROOT / "static", "favicon.ico", mimetype="image/x-icon")

    def submitted_form() -> dict[str, str]:
        return {
            "title": request.form.get("title", ""),
            "date": request.form.get("date", ""),
            "tags": request.form.get("tags", ""),
            "summary": request.form.get("summary", ""),
            "slug": request.form.get("slug", ""),
            "body": request.form.get("body", ""),
        }

    def complete_publication(
        filename: str,
        draft_revision: str,
        published_revision: str,
    ) -> tuple[str, int]:
        try:
            slug = repository.publish_draft(filename, draft_revision, published_revision)
        except DraftCleanupError as exc:
            slug = repository.published_slug(filename)
            return render_publication_result(
                filename=filename,
                slug=slug,
                result=DeploymentResult(False, str(exc)),
                source_written=True,
            )

        result = app.extensions["publisher"].deploy()
        return render_publication_result(
            filename=filename,
            slug=slug,
            result=result,
            source_written=True,
        )

    @app.get("/")
    def index() -> str:
        query = request.args.get("q", "").strip().lower()
        published = repository.list_published()
        drafts = repository.list_drafts()
        if query:
            def matches(note: Any) -> bool:
                haystack = " ".join((note.title, note.filename, note.slug, *note.tags)).lower()
                return query in haystack

            published = [note for note in published if matches(note)]
            drafts = [note for note in drafts if matches(note)]
        return render_template("index.html", published=published, drafts=drafts, query=query)

    @app.route("/notes/new", methods=["GET", "POST"])
    def new_note() -> str | tuple[str, int]:
        form = {
            "title": "",
            "date": date.today().isoformat(),
            "tags": "",
            "summary": "",
            "slug": "",
            "body": "",
        }
        error = ""
        status = 200
        if request.method == "POST":
            form = submitted_form()
            action = request.form.get("action", "save")
            try:
                if action not in {"save", "publish"}:
                    raise ValidationError("La acción editorial no es válida.")
                note = repository.create_draft(form)
                if action == "publish":
                    return complete_publication(note.filename, note.revision, note.published_revision)
            except CollisionError as exc:
                error = str(exc)
                status = 409
            except ValidationError as exc:
                error = str(exc)
                status = 400
            else:
                return redirect(url_for("edit_note", filename=note.filename, saved="created"))
        return render_template("new.html", form=form, error=error), status

    @app.route("/notes/<filename>/edit", methods=["GET", "POST"])
    def edit_note(filename: str) -> str | tuple[str, int]:
        try:
            note = repository.load_for_edit(filename)
        except (InvalidFilename, NoteNotFound):
            abort(404)

        form = note.form_values()
        revision_value = note.revision
        published_revision_value = note.published_revision
        render_note = note
        error = ""
        status = 200
        if request.method == "POST":
            form = submitted_form()
            action = request.form.get("action", "save")
            revision_value = request.form.get("revision", "")
            published_revision_value = request.form.get("published_revision", "")
            try:
                if action not in {"save", "publish"}:
                    raise ValidationError("La acción editorial no es válida.")
                saved_note = repository.save_draft(filename, form, revision_value)
                render_note = saved_note
                revision_value = saved_note.revision
                if action == "publish":
                    return complete_publication(
                        saved_note.filename,
                        saved_note.revision,
                        published_revision_value,
                    )
            except RevisionConflict as exc:
                error = str(exc)
                status = 409
            except CollisionError as exc:
                error = str(exc)
                status = 409
            except ValidationError as exc:
                error = str(exc)
                status = 400
            else:
                return redirect(url_for("edit_note", filename=saved_note.filename, saved="updated"))

        return render_template(
            "edit.html",
            note=render_note,
            form=form,
            error=error,
            saved=request.args.get("saved", ""),
            revision_value=revision_value,
            publish_published_revision=published_revision_value,
        ), status

    @app.get("/notes/<filename>/preview")
    def preview_note(filename: str) -> str:
        try:
            note = repository.load_for_edit(filename)
        except (InvalidFilename, NoteNotFound):
            abort(404)
        if note.source_kind != "draft":
            abort(404)
        return render_template("preview.html", note=note)

    @app.get("/notes/<filename>/preview/document")
    def preview_document(filename: str) -> str:
        try:
            note = repository.load_for_edit(filename)
        except (InvalidFilename, NoteNotFound):
            abort(404)
        if note.source_kind != "draft":
            abort(404)
        rendered_html = render_markdown(note.body, PUBLIC_SITE_URL)
        return render_template(
            "preview_document.html",
            note=note,
            rendered_html=rendered_html,
            public_site_url=PUBLIC_SITE_URL,
        )

    def render_publication_result(
        *,
        filename: str,
        slug: str,
        result: DeploymentResult,
        source_written: bool,
    ) -> tuple[str, int]:
        public_url = f"{PUBLIC_SITE_URL}/notes/{slug}/"
        status = 200 if result.success else 502
        return render_template(
            "publish_result.html",
            filename=filename,
            public_url=public_url,
            result=result,
            source_written=source_written,
        ), status

    @app.post("/notes/<filename>/publish")
    def publish_note(filename: str) -> tuple[str, int] | str:
        try:
            note = repository.load_for_edit(filename)
        except (InvalidFilename, NoteNotFound):
            abort(404)
        except ValidationError as exc:
            return render_template("error.html", message=str(exc)), 400
        if note.source_kind != "draft":
            abort(404)

        try:
            slug = repository.publish_draft(
                filename,
                request.form.get("draft_revision", ""),
                request.form.get("published_revision", ""),
            )
        except RevisionConflict as exc:
            error, status = str(exc), 409
        except CollisionError as exc:
            error, status = str(exc), 409
        except ValidationError as exc:
            error, status = str(exc), 400
        except DraftCleanupError as exc:
            slug = repository.published_slug(filename)
            return render_publication_result(
                filename=filename,
                slug=slug,
                result=DeploymentResult(False, str(exc)),
                source_written=True,
            )
        else:
            result = app.extensions["publisher"].deploy()
            return render_publication_result(
                filename=filename,
                slug=slug,
                result=result,
                source_written=True,
            )

        return render_template(
            "edit.html",
            note=note,
            form=note.form_values(),
            error=error,
            saved="",
            revision_value=note.revision,
            publish_draft_revision=request.form.get("draft_revision", ""),
            publish_published_revision=request.form.get("published_revision", ""),
        ), status

    @app.post("/notes/<filename>/deploy")
    def retry_deploy(filename: str) -> tuple[str, int]:
        try:
            slug = repository.published_slug(filename)
        except (InvalidFilename, NoteNotFound):
            abort(404)
        except ValidationError as exc:
            return render_template("error.html", message=str(exc)), 400
        result = app.extensions["publisher"].deploy()
        return render_publication_result(
            filename=filename,
            slug=slug,
            result=result,
            source_written=True,
        )

    @app.errorhandler(400)
    def bad_request(error: Exception) -> tuple[str, int]:
        message = getattr(error, "description", "La solicitud no es válida.")
        return render_template("error.html", message=message), 400

    @app.errorhandler(413)
    def request_too_large(_: Exception) -> tuple[str, int]:
        return render_template("error.html", message="La solicitud supera el tamaño máximo permitido."), 413

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.environ.get("NICO_EDITOR_HOST", "127.0.0.1"),
        port=int(os.environ.get("NICO_EDITOR_PORT", "5001")),
        debug=False,
    )
