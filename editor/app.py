from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Any

from flask import Flask, Response, abort, redirect, render_template, request, url_for

from .content import (
    CollisionError,
    ContentRepository,
    InvalidFilename,
    NoteNotFound,
    RevisionConflict,
    ValidationError,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def create_app(project_root: Path | str | None = None, *, testing: bool = False) -> Flask:
    app = Flask(__name__)
    app.config.update(
        MAX_CONTENT_LENGTH=768 * 1024,
        TESTING=testing,
    )
    repository = ContentRepository(project_root or PROJECT_ROOT)
    app.extensions["content_repository"] = repository

    @app.after_request
    def private_editor_headers(response: Response) -> Response:
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self'; "
            "script-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
        )
        return response

    def submitted_form() -> dict[str, str]:
        return {
            "title": request.form.get("title", ""),
            "date": request.form.get("date", ""),
            "tags": request.form.get("tags", ""),
            "summary": request.form.get("summary", ""),
            "slug": request.form.get("slug", ""),
            "body": request.form.get("body", ""),
        }

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
    def new_note() -> str:
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
            try:
                note = repository.create_draft(form)
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
    def edit_note(filename: str) -> str:
        try:
            note = repository.load_for_edit(filename)
        except (InvalidFilename, NoteNotFound):
            abort(404)

        form = note.form_values()
        revision_value = note.revision
        error = ""
        status = 200
        if request.method == "POST":
            form = submitted_form()
            revision_value = request.form.get("revision", "")
            try:
                saved_note = repository.save_draft(
                    filename,
                    form,
                    revision_value,
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
            note=note,
            form=form,
            error=error,
            saved=request.args.get("saved", ""),
            revision_value=revision_value,
        ), status

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
