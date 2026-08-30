from __future__ import annotations

import hmac
import os
import secrets
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from flask import Flask, Response, abort, redirect, render_template, request, send_from_directory, session, url_for

from generator.lib.notes import render_markdown

from .content import (
    CollisionError,
    ContentRepository,
    DraftCleanupError,
    EditableNote,
    InvalidFilename,
    NoteNotFound,
    NoteSummary,
    RevisionConflict,
    ValidationError,
)
from .publishing import DeploymentResult, SystemdPublisher


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SITE_URL = "https://www.nico.com.ar"


@dataclass(frozen=True)
class NoteVersionView:
    filename: str
    title: str
    date: str
    tags: tuple[str, ...]
    summary: str
    slug: str
    language: str
    note_id: str
    state_label: str
    state_tone: str
    validation_error: str
    has_draft: bool
    published_exists: bool
    is_active: bool = False


@dataclass(frozen=True)
class NoteGroupView:
    note_id: str
    title: str
    date: str
    tags: tuple[str, ...]
    versions: tuple[NoteVersionView, ...]
    has_validation_error: bool


def _language_label(language: str) -> str:
    return "English" if language == "en" else "Español"


def _language_role(language: str) -> str:
    return "Translation" if language == "en" else "Original"


def _version_state(has_draft: bool, published_exists: bool) -> tuple[str, str]:
    if has_draft and published_exists:
        return "Cambios sin publicar", "draft"
    if has_draft:
        return "Borrador", "draft"
    if published_exists:
        return "Publicada", "published"
    return "Sin publicar", "muted"


def _version_sort_key(version: NoteVersionView) -> tuple[int, str, str]:
    order = {"es": 0, "en": 1}
    return (order.get(version.language, 9), version.date, version.filename)


def _group_note_summaries(published: list[NoteSummary], drafts: list[NoteSummary]) -> list[NoteGroupView]:
    published_by_filename = {note.filename: note for note in published}
    drafts_by_filename = {note.filename: note for note in drafts}

    versions: list[NoteVersionView] = []
    for filename in sorted(set(published_by_filename) | set(drafts_by_filename)):
        draft_note = drafts_by_filename.get(filename)
        published_note = published_by_filename.get(filename)
        base = draft_note or published_note
        if base is None:
            continue
        state_label, state_tone = _version_state(draft_note is not None, published_note is not None)
        versions.append(
            NoteVersionView(
                filename=filename,
                title=base.title,
                date=base.date,
                tags=base.tags,
                summary=base.summary,
                slug=base.slug,
                language=base.language,
                note_id=base.note_id,
                state_label=state_label,
                state_tone=state_tone,
                validation_error=base.validation_error,
                has_draft=draft_note is not None,
                published_exists=published_note is not None,
            )
        )

    grouped: dict[str, list[NoteVersionView]] = {}
    for version in versions:
        grouped.setdefault(version.note_id, []).append(version)

    items: list[NoteGroupView] = []
    for note_id, grouped_versions in grouped.items():
        ordered_versions = tuple(sorted(grouped_versions, key=_version_sort_key))
        spanish = next((version for version in ordered_versions if version.language == "es"), None)
        primary = spanish or ordered_versions[0]
        seen_tags: dict[str, None] = {}
        for version in ordered_versions:
            for tag in version.tags:
                seen_tags.setdefault(tag, None)
        items.append(
            NoteGroupView(
                note_id=note_id,
                title=primary.title,
                date=primary.date,
                tags=tuple(seen_tags),
                versions=ordered_versions,
                has_validation_error=any(version.validation_error for version in ordered_versions),
            )
        )

    items.sort(key=lambda group: (group.date, group.title.lower(), group.note_id), reverse=True)
    return items


def _group_matches(group: NoteGroupView, query: str) -> bool:
    haystack_parts = [group.title, group.note_id, *group.tags]
    for version in group.versions:
        haystack_parts.extend(
            [
                version.title,
                version.filename,
                version.slug,
                version.language,
                version.note_id,
                version.summary,
                *version.tags,
            ]
        )
    haystack = " ".join(part for part in haystack_parts if part).lower()
    return query in haystack


def _groups_for_section(groups: list[NoteGroupView], *, include: str) -> list[NoteGroupView]:
    if include == "published":
        return [group for group in groups if any(version.published_exists for version in group.versions)]
    if include == "drafts":
        return [group for group in groups if any(version.has_draft for version in group.versions)]
    raise ValueError(f"Unknown section: {include}")


def _find_group(groups: list[NoteGroupView], filename: str) -> NoteGroupView | None:
    for group in groups:
        if any(version.filename == filename for version in group.versions):
            return group
    return None


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
            "lang": request.form.get("lang", ""),
            "note_id": request.form.get("note_id", ""),
            "body": request.form.get("body", ""),
        }

    def group_views() -> list[NoteGroupView]:
        return _group_note_summaries(repository.list_published(), repository.list_drafts())

    def language_display(form: dict[str, str]) -> dict[str, str]:
        language = form.get("lang", "") or "es"
        return {
            "language_label": _language_label(language),
            "language_role": _language_role(language),
        }

    def with_fixed_metadata(form: dict[str, str], *, language: str, note_id: str) -> dict[str, str]:
        enriched = dict(form)
        enriched["lang"] = language
        enriched["note_id"] = note_id
        return enriched

    def edit_view_context(note: EditableNote, form: dict[str, str]) -> dict[str, Any]:
        groups = group_views()
        group = _find_group(groups, note.filename)
        versions: tuple[NoteVersionView, ...] = ()
        create_english_url = ""
        if group is not None:
            versions = tuple(
                NoteVersionView(
                    **{**version.__dict__, "is_active": version.filename == note.filename},
                )
                for version in group.versions
            )
            active = next((version for version in versions if version.is_active), None)
            if active is not None and active.language == "es" and all(version.language != "en" for version in versions):
                create_english_url = url_for("new_english_version", filename=note.filename)
        return {
            "note_versions": versions,
            "create_english_url": create_english_url,
            **language_display(form),
        }

    def complete_publication(
        filename: str,
        draft_revision: str,
        published_revision: str,
    ) -> tuple[str, int]:
        try:
            repository.publish_draft(filename, draft_revision, published_revision)
            published = repository.published_note_info(filename)
        except DraftCleanupError as exc:
            published = repository.published_note_info(filename)
            return render_publication_result(
                filename=filename,
                public_path=published["path"],
                result=DeploymentResult(False, str(exc)),
                source_written=True,
            )

        result = app.extensions["publisher"].deploy()
        return render_publication_result(
            filename=filename,
            public_path=published["path"],
            result=result,
            source_written=True,
        )

    @app.get("/")
    def index() -> str:
        query = request.args.get("q", "").strip().lower()
        groups = group_views()
        if query:
            groups = [group for group in groups if _group_matches(group, query)]
        published = _groups_for_section(groups, include="published")
        drafts = _groups_for_section(groups, include="drafts")
        return render_template("index.html", published=published, drafts=drafts, query=query)

    @app.route("/notes/new", methods=["GET", "POST"])
    def new_note() -> str | tuple[str, int]:
        form = {
            "title": "",
            "date": date.today().isoformat(),
            "tags": "",
            "summary": "",
            "slug": "",
            "lang": "es",
            "note_id": "",
            "body": "",
        }
        error = ""
        status = 200
        if request.method == "POST":
            form = with_fixed_metadata(submitted_form(), language="es", note_id="")
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
        return render_template(
            "new.html",
            form=form,
            error=error,
            creation_mode="original",
            source_note=None,
            **language_display(form),
        ), status

    @app.route("/notes/<filename>/translations/en/new", methods=["GET", "POST"])
    def new_english_version(filename: str) -> str | tuple[str, int]:
        try:
            source_note = repository.load_for_edit(filename)
        except (InvalidFilename, NoteNotFound):
            abort(404)

        source_form = source_note.form_values()
        if source_form["lang"] != "es":
            abort(404)

        source_group = _find_group(group_views(), source_note.filename)
        if source_group is not None and any(version.language == "en" for version in source_group.versions):
            return render_template(
                "error.html",
                message="La versión EN de esta nota ya existe.",
            ), 409

        form = {
            "title": "",
            "date": source_form["date"],
            "tags": source_form["tags"],
            "summary": "",
            "slug": "",
            "lang": "en",
            "note_id": source_form["note_id"],
            "body": "",
        }
        error = ""
        status = 200
        if request.method == "POST":
            form = with_fixed_metadata(submitted_form(), language="en", note_id=source_form["note_id"])
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
        return render_template(
            "new.html",
            form=form,
            error=error,
            creation_mode="translation",
            source_note=source_note,
            **language_display(form),
        ), status

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
            form = with_fixed_metadata(submitted_form(), language=note.form_values()["lang"], note_id=note.form_values()["note_id"])
            action = request.form.get("action", "save")
            revision_value = request.form.get("revision", "")
            published_revision_value = request.form.get("published_revision", "")
            try:
                if action not in {"save", "publish"}:
                    raise ValidationError("La acción editorial no es válida.")
                saved_note = repository.save_draft(filename, form, revision_value)
                render_note = saved_note
                revision_value = saved_note.revision
                form = saved_note.form_values()
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
            **edit_view_context(render_note, form),
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
        public_path: str,
        result: DeploymentResult,
        source_written: bool,
    ) -> tuple[str, int]:
        public_url = f"{PUBLIC_SITE_URL}{public_path}"
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
            repository.publish_draft(
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
            published = repository.published_note_info(filename)
            return render_publication_result(
                filename=filename,
                public_path=published["path"],
                result=DeploymentResult(False, str(exc)),
                source_written=True,
            )
        else:
            published = repository.published_note_info(filename)
            result = app.extensions["publisher"].deploy()
            return render_publication_result(
                filename=filename,
                public_path=published["path"],
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
            **edit_view_context(note, note.form_values()),
        ), status

    @app.post("/notes/<filename>/deploy")
    def retry_deploy(filename: str) -> tuple[str, int]:
        try:
            published = repository.published_note_info(filename)
        except (InvalidFilename, NoteNotFound):
            abort(404)
        except ValidationError as exc:
            return render_template("error.html", message=str(exc)), 400
        result = app.extensions["publisher"].deploy()
        return render_publication_result(
            filename=filename,
            public_path=published["path"],
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
    app.run(debug=True)
