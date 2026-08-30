from __future__ import annotations

import hashlib
import hmac
import os
import re
import stat
import tempfile
import threading
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

import yaml
from dateutil import parser as date_parser

from generator.lib.notes import DEFAULT_LANGUAGE, FRONT_MATTER_PATTERN, RESERVED_NOTE_SLUGS, note_id_from_filename, note_path
from generator.lib.utils import slugify


FILENAME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_PREFIX_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})-")
MAX_NOTE_BYTES = 512 * 1024
MAX_TITLE_LENGTH = 200
MAX_SUMMARY_LENGTH = 1_000
MAX_TAGS = 30
MAX_TAG_LENGTH = 60
MAX_SLUG_LENGTH = 120
MAX_NOTE_ID_LENGTH = 200
NOTE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ContentError(Exception):
    """Base error for safe editor content operations."""


class InvalidFilename(ContentError):
    pass


class NoteNotFound(ContentError):
    pass


class ValidationError(ContentError):
    pass


class CollisionError(ContentError):
    pass


class RevisionConflict(ContentError):
    pass


class DraftCleanupError(ContentError):
    pass


@dataclass(frozen=True)
class ParsedDocument:
    metadata: dict[str, Any]
    body: str


@dataclass(frozen=True)
class NoteSummary:
    filename: str
    title: str
    date: str
    tags: tuple[str, ...]
    summary: str
    slug: str
    language: str = DEFAULT_LANGUAGE
    note_id: str = ""
    has_draft: bool = False
    published_exists: bool = False
    validation_error: str = ""


@dataclass(frozen=True)
class EditableNote:
    filename: str
    metadata: dict[str, Any]
    body: str
    source_kind: str
    revision: str
    published_revision: str
    published_exists: bool

    def form_values(self) -> dict[str, str]:
        raw_tags = self.metadata.get("tags", [])
        tags = raw_tags if isinstance(raw_tags, list) else []
        return {
            "title": str(self.metadata.get("title", "")),
            "date": _metadata_value(self.metadata.get("date", "")),
            "tags": ", ".join(str(tag) for tag in tags),
            "summary": str(self.metadata.get("summary", "")),
            "slug": str(self.metadata.get("slug") or slug_from_filename(self.filename)),
            "lang": _language_from_metadata(self.metadata),
            "note_id": _note_id_from_metadata(self.filename, self.metadata),
            "body": self.body,
        }


def _metadata_value(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value or "")


def slug_from_filename(filename: str) -> str:
    stem = filename.removesuffix(".md")
    return DATE_PREFIX_PATTERN.sub("", stem)


def _language_from_metadata(metadata: Mapping[str, Any]) -> str:
    candidate = str(metadata.get("lang", DEFAULT_LANGUAGE) or DEFAULT_LANGUAGE).strip().lower()
    if candidate not in RESERVED_NOTE_SLUGS:
        return DEFAULT_LANGUAGE
    return candidate


def _validated_language(raw_value: Any) -> str:
    candidate = str(raw_value or DEFAULT_LANGUAGE).strip().lower()
    if candidate not in RESERVED_NOTE_SLUGS:
        raise ValidationError("El idioma debe ser es o en.")
    return candidate


def _note_id_from_metadata(filename: str, metadata: Mapping[str, Any]) -> str:
    explicit = str(metadata.get("note_id", "")).strip()
    return explicit or note_id_from_filename(filename)


def parse_document(raw: str) -> ParsedDocument:
    match = FRONT_MATTER_PATTERN.match(raw)
    if not match:
        return ParsedDocument(metadata={}, body=raw)

    front_raw, body = match.groups()
    try:
        metadata = yaml.safe_load(front_raw) or {}
    except yaml.YAMLError as exc:
        raise ValidationError("El frontmatter YAML no es válido.") from exc
    if not isinstance(metadata, dict):
        raise ValidationError("El frontmatter debe ser un objeto YAML.")
    return ParsedDocument(metadata=dict(metadata), body=body)


def serialize_document(metadata: Mapping[str, Any], body: str) -> str:
    frontmatter = yaml.safe_dump(
        dict(metadata),
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    ).strip()
    normalized_body = body.replace("\r\n", "\n").replace("\r", "\n").rstrip()
    return f"---\n{frontmatter}\n---\n\n{normalized_body}\n"


class ContentRepository:
    def __init__(self, project_root: Path | str) -> None:
        self.project_root = Path(project_root).resolve(strict=True)
        self.notes_dir = self._content_directory("notes")
        self.drafts_dir = self._content_directory("drafts")
        self._write_lock = threading.Lock()

    def _content_directory(self, name: str) -> Path:
        path = self.project_root / "content" / name
        if path.is_symlink() or not path.is_dir():
            raise RuntimeError(f"Invalid content directory: {path}")
        resolved = path.resolve(strict=True)
        content_root = (self.project_root / "content").resolve(strict=True)
        if resolved.parent != content_root:
            raise RuntimeError(f"Content directory escapes project root: {path}")
        return resolved

    def _path(self, directory: Path, filename: str) -> Path:
        if not FILENAME_PATTERN.fullmatch(filename):
            raise InvalidFilename("Nombre de archivo inválido.")
        candidate = directory / filename
        if candidate.parent != directory:
            raise InvalidFilename("El archivo queda fuera del directorio permitido.")
        if candidate.is_symlink():
            raise InvalidFilename("No se permiten enlaces simbólicos.")
        if candidate.exists() and not candidate.is_file():
            raise InvalidFilename("El contenido no es un archivo regular.")
        return candidate

    def _read_bytes(self, path: Path) -> bytes:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(path, flags)
        except FileNotFoundError as exc:
            raise NoteNotFound("La nota no existe.") from exc
        except OSError as exc:
            raise InvalidFilename("No se pudo abrir el archivo de forma segura.") from exc

        with os.fdopen(descriptor, "rb") as handle:
            file_stat = os.fstat(handle.fileno())
            if not stat.S_ISREG(file_stat.st_mode):
                raise InvalidFilename("El contenido no es un archivo regular.")
            if file_stat.st_size > MAX_NOTE_BYTES:
                raise ValidationError("La nota supera el tamaño máximo permitido.")
            return handle.read(MAX_NOTE_BYTES + 1)

    def _read(self, path: Path) -> tuple[bytes, ParsedDocument]:
        raw = self._read_bytes(path)
        if len(raw) > MAX_NOTE_BYTES:
            raise ValidationError("La nota supera el tamaño máximo permitido.")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValidationError("La nota no está codificada como UTF-8.") from exc
        return raw, parse_document(text)

    @staticmethod
    def _revision(kind: str, raw: bytes) -> str:
        return f"{kind}:{hashlib.sha256(raw).hexdigest()}"

    def _summaries(self, directory: Path, *, published: bool) -> list[NoteSummary]:
        items: list[NoteSummary] = []
        for path in sorted(directory.glob("*.md")):
            if path.is_symlink() or not path.is_file():
                continue
            try:
                _, document = self._read(path)
                metadata = document.metadata
                raw_tags = metadata.get("tags", [])
                tags = tuple(str(tag) for tag in raw_tags) if isinstance(raw_tags, list) else ()
                item = NoteSummary(
                    filename=path.name,
                    title=str(metadata.get("title") or slug_from_filename(path.name).replace("-", " ").title()),
                    date=_metadata_value(metadata.get("date", "")),
                    tags=tags,
                    summary=str(metadata.get("summary", "")),
                    slug=str(metadata.get("slug") or slug_from_filename(path.name)),
                    language=_language_from_metadata(metadata),
                    note_id=_note_id_from_metadata(path.name, metadata),
                    has_draft=published and (self.drafts_dir / path.name).is_file(),
                    published_exists=(self.notes_dir / path.name).is_file(),
                )
            except ContentError as exc:
                item = NoteSummary(
                    filename=path.name,
                    title=slug_from_filename(path.name).replace("-", " ").title(),
                    date=path.name[:10],
                    tags=(),
                    summary="",
                    slug=slug_from_filename(path.name),
                    language=DEFAULT_LANGUAGE,
                    note_id=note_id_from_filename(path.name),
                    validation_error=str(exc),
                )
            items.append(item)
        items.sort(key=lambda item: (item.date, item.filename), reverse=True)
        return items

    def list_published(self) -> list[NoteSummary]:
        return self._summaries(self.notes_dir, published=True)

    def list_drafts(self) -> list[NoteSummary]:
        return self._summaries(self.drafts_dir, published=False)

    def load_for_edit(self, filename: str) -> EditableNote:
        draft_path = self._path(self.drafts_dir, filename)
        published_path = self._path(self.notes_dir, filename)
        if draft_path.exists():
            source_kind = "draft"
            source_path = draft_path
        elif published_path.exists():
            source_kind = "published"
            source_path = published_path
        else:
            raise NoteNotFound("La nota no existe.")

        raw, document = self._read(source_path)
        return EditableNote(
            filename=filename,
            metadata=document.metadata,
            body=document.body,
            source_kind=source_kind,
            revision=self._revision(source_kind, raw),
            published_revision=self._published_revision(published_path),
            published_exists=published_path.exists(),
        )

    def _published_revision(self, published_path: Path) -> str:
        if not published_path.exists():
            return "published:none"
        raw = self._read_bytes(published_path)
        return self._revision("published", raw)

    def _validated_fields(
        self,
        payload: Mapping[str, str],
        filename: str,
        base_metadata: Mapping[str, Any],
    ) -> tuple[dict[str, Any], str, str]:
        title = str(payload.get("title", "")).strip()
        if not title or len(title) > MAX_TITLE_LENGTH:
            raise ValidationError(f"El título es obligatorio y admite hasta {MAX_TITLE_LENGTH} caracteres.")

        date_value = str(payload.get("date", "")).strip()
        try:
            parsed_date = date_parser.isoparse(date_value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValidationError("La fecha debe usar un formato ISO válido.") from exc

        raw_slug = str(payload.get("slug", "")).strip() or slug_from_filename(filename)
        normalized_slug = slugify(raw_slug)
        if len(normalized_slug) > MAX_SLUG_LENGTH or not SLUG_PATTERN.fullmatch(normalized_slug):
            raise ValidationError("El slug no es válido.")

        language = _validated_language(payload.get("lang", _language_from_metadata(base_metadata)))
        note_id = str(payload.get("note_id", "")).strip() or note_id_from_filename(filename)
        if len(note_id) > MAX_NOTE_ID_LENGTH or not NOTE_ID_PATTERN.fullmatch(note_id):
            raise ValidationError("El ID compartido no es válido.")

        summary = str(payload.get("summary", "")).strip()
        if len(summary) > MAX_SUMMARY_LENGTH:
            raise ValidationError(f"El resumen admite hasta {MAX_SUMMARY_LENGTH} caracteres.")

        raw_tags = str(payload.get("tags", ""))
        tags: list[str] = []
        for raw_tag in raw_tags.split(","):
            tag = raw_tag.strip()
            if not tag or tag in tags:
                continue
            if len(tag) > MAX_TAG_LENGTH:
                raise ValidationError(f"Cada tag admite hasta {MAX_TAG_LENGTH} caracteres.")
            tags.append(tag)
        if len(tags) > MAX_TAGS:
            raise ValidationError(f"Se admiten hasta {MAX_TAGS} tags.")

        body = str(payload.get("body", ""))
        if len(body.encode("utf-8")) > MAX_NOTE_BYTES:
            raise ValidationError("El cuerpo supera el tamaño máximo permitido.")

        metadata = dict(base_metadata)
        metadata["title"] = title
        metadata["date"] = date_value
        metadata["tags"] = tags
        if summary or "summary" in metadata:
            metadata["summary"] = summary
        else:
            metadata.pop("summary", None)

        derived_slug = slug_from_filename(filename)
        if normalized_slug != derived_slug or "slug" in metadata:
            metadata["slug"] = normalized_slug
        else:
            metadata.pop("slug", None)

        if language != DEFAULT_LANGUAGE or "lang" in metadata:
            metadata["lang"] = language
        else:
            metadata.pop("lang", None)

        derived_note_id = note_id_from_filename(filename)
        if note_id != derived_note_id or "note_id" in metadata:
            metadata["note_id"] = note_id
        else:
            metadata.pop("note_id", None)

        return metadata, body, parsed_date.date().isoformat()

    def _ensure_unique_slug(self, slug: str, exclude_filename: str, language: str) -> None:
        if slug in RESERVED_NOTE_SLUGS[language]:
            raise CollisionError("El slug está reservado para rutas del sitio.")

        effective_paths: dict[str, Path] = {}
        for path in self.notes_dir.glob("*.md"):
            if not path.is_symlink():
                effective_paths[path.name] = path
        for path in self.drafts_dir.glob("*.md"):
            if not path.is_symlink():
                effective_paths[path.name] = path

        for filename, path in effective_paths.items():
            if filename == exclude_filename:
                continue
            try:
                _, document = self._read(path)
                existing_language = _language_from_metadata(document.metadata)
                existing_slug = slugify(str(document.metadata.get("slug") or slug_from_filename(filename)))
            except ContentError:
                existing_language = DEFAULT_LANGUAGE
                existing_slug = slug_from_filename(filename)
            if existing_language == language and existing_slug == slug:
                raise CollisionError(f"El slug ya está usado por {filename}.")

    def _atomic_write(self, target: Path, content: bytes, *, replace: bool) -> None:
        if target.parent not in {self.notes_dir, self.drafts_dir}:
            raise InvalidFilename("El destino queda fuera de los directorios permitidos.")
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=target.parent,
        )
        temporary_path = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o664)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            if replace:
                os.replace(temporary_path, target)
            else:
                try:
                    os.link(temporary_path, target)
                except FileExistsError as exc:
                    raise CollisionError("El archivo de destino apareció durante la operación.") from exc
                temporary_path.unlink()
            directory_fd = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

    def create_draft(self, payload: Mapping[str, str]) -> EditableNote:
        title = str(payload.get("title", "")).strip()
        date_value = str(payload.get("date", "")).strip()
        try:
            filename_date = date_parser.isoparse(date_value).date().isoformat()
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValidationError("La fecha debe usar un formato ISO válido.") from exc

        language = _validated_language(payload.get("lang", ""))
        normalized_slug = slugify(str(payload.get("slug", "")).strip() or title)
        if len(normalized_slug) > MAX_SLUG_LENGTH or not SLUG_PATTERN.fullmatch(normalized_slug):
            raise ValidationError("No se pudo generar un slug válido.")
        filename = f"{filename_date}-{normalized_slug}.md"
        draft_path = self._path(self.drafts_dir, filename)
        published_path = self._path(self.notes_dir, filename)

        with self._write_lock:
            if draft_path.exists() or published_path.exists():
                raise CollisionError("Ya existe una nota o borrador con ese nombre.")
            metadata, body, _ = self._validated_fields(payload, filename, {})
            self._ensure_unique_slug(normalized_slug, filename, language)
            serialized = serialize_document(metadata, body).encode("utf-8")
            self._atomic_write(draft_path, serialized, replace=False)
        return self.load_for_edit(filename)

    def save_draft(
        self,
        filename: str,
        payload: Mapping[str, str],
        revision: str,
    ) -> EditableNote:
        draft_path = self._path(self.drafts_dir, filename)
        published_path = self._path(self.notes_dir, filename)
        try:
            source_kind, expected_digest = revision.split(":", 1)
        except ValueError as exc:
            raise RevisionConflict("La revisión enviada no es válida.") from exc
        if source_kind not in {"draft", "published"} or not re.fullmatch(r"[0-9a-f]{64}", expected_digest):
            raise RevisionConflict("La revisión enviada no es válida.")

        with self._write_lock:
            if source_kind == "draft":
                if not draft_path.exists():
                    raise RevisionConflict("El borrador cambió o dejó de existir. Recargá la página.")
                source_path = draft_path
            else:
                if draft_path.exists():
                    raise RevisionConflict("Ya existe un borrador más nuevo. Recargá la página.")
                if not published_path.exists():
                    raise RevisionConflict("La nota publicada cambió o dejó de existir.")
                source_path = published_path

            raw, document = self._read(source_path)
            current_digest = hashlib.sha256(raw).hexdigest()
            if not hmac.compare_digest(current_digest, expected_digest):
                raise RevisionConflict("El contenido cambió desde que lo abriste. Recargá antes de guardar.")

            metadata, body, _ = self._validated_fields(payload, filename, document.metadata)
            effective_slug = str(metadata.get("slug") or slug_from_filename(filename))
            effective_language = _language_from_metadata(metadata)
            self._ensure_unique_slug(effective_slug, filename, effective_language)
            serialized = serialize_document(metadata, body).encode("utf-8")
            self._atomic_write(draft_path, serialized, replace=True)

        return self.load_for_edit(filename)

    @staticmethod
    def _validate_revision_token(revision: str, expected_kind: str) -> str:
        try:
            source_kind, expected_digest = revision.split(":", 1)
        except ValueError as exc:
            raise RevisionConflict("La revisión enviada no es válida.") from exc
        if source_kind != expected_kind or not re.fullmatch(r"[0-9a-f]{64}", expected_digest):
            raise RevisionConflict("La revisión enviada no es válida.")
        return expected_digest

    def _validate_published_revision(self, published_path: Path, revision: str) -> bool:
        if revision == "published:none":
            if published_path.exists():
                raise RevisionConflict("Apareció una nota publicada con ese nombre. Recargá la página.")
            return False
        expected_digest = self._validate_revision_token(revision, "published")
        if not published_path.exists():
            raise RevisionConflict("La nota publicada cambió o dejó de existir. Recargá la página.")
        current_digest = hashlib.sha256(self._read_bytes(published_path)).hexdigest()
        if not hmac.compare_digest(current_digest, expected_digest):
            raise RevisionConflict("La fuente publicada cambió desde que abriste el borrador.")
        return True

    def _strict_publication_metadata(self, filename: str, raw: bytes) -> tuple[ParsedDocument, str, str]:
        try:
            date.fromisoformat(filename[:10])
        except ValueError as exc:
            raise ValidationError("La fecha incluida en el filename no es válida.") from exc
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValidationError("El borrador no está codificado como UTF-8.") from exc
        if not FRONT_MATTER_PATTERN.match(text):
            raise ValidationError("Publicar requiere frontmatter YAML delimitado por ---.")
        document = parse_document(text)
        metadata = document.metadata

        title = metadata.get("title")
        if not isinstance(title, str) or not title.strip() or len(title.strip()) > MAX_TITLE_LENGTH:
            raise ValidationError("El título publicado debe ser un string válido.")

        date_value = metadata.get("date")
        if isinstance(date_value, (date, datetime)):
            pass
        elif isinstance(date_value, str):
            try:
                date_parser.isoparse(date_value)
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValidationError("La fecha publicada debe usar un formato ISO válido.") from exc
        else:
            raise ValidationError("La fecha publicada es obligatoria.")

        tags = metadata.get("tags")
        if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
            raise ValidationError("Los tags publicados deben ser una lista de strings.")
        if len(tags) > MAX_TAGS or any(not tag.strip() or len(tag) > MAX_TAG_LENGTH for tag in tags):
            raise ValidationError("La lista de tags publicada no es válida.")

        if "summary" in metadata and not isinstance(metadata["summary"], str):
            raise ValidationError("El resumen publicado debe ser un string.")
        if isinstance(metadata.get("summary"), str) and len(metadata["summary"]) > MAX_SUMMARY_LENGTH:
            raise ValidationError("El resumen publicado es demasiado largo.")

        language = _validated_language(metadata.get("lang", DEFAULT_LANGUAGE))

        raw_slug = metadata.get("slug", slug_from_filename(filename))
        if not isinstance(raw_slug, str):
            raise ValidationError("El slug publicado debe ser un string.")
        effective_slug = raw_slug.strip()
        if (
            not effective_slug
            or len(effective_slug) > MAX_SLUG_LENGTH
            or not SLUG_PATTERN.fullmatch(effective_slug)
            or slugify(effective_slug) != effective_slug
        ):
            raise ValidationError("El slug publicado no es válido.")
        if effective_slug in RESERVED_NOTE_SLUGS[language]:
            raise ValidationError("El slug publicado está reservado para rutas del sitio.")

        note_id = str(metadata.get("note_id", note_id_from_filename(filename))).strip()
        if len(note_id) > MAX_NOTE_ID_LENGTH or not NOTE_ID_PATTERN.fullmatch(note_id):
            raise ValidationError("El ID compartido publicado no es válido.")
        return document, effective_slug, language

    def _ensure_unique_published_slug(self, slug: str, exclude_filename: str, language: str) -> None:
        if slug in RESERVED_NOTE_SLUGS[language]:
            raise CollisionError("El slug está reservado para rutas del sitio.")

        for path in self.notes_dir.glob("*.md"):
            if path.name == exclude_filename or path.is_symlink() or not path.is_file():
                continue
            try:
                raw = self._read_bytes(path)
                _, existing_slug, existing_language = self._strict_publication_metadata(path.name, raw)
            except ContentError:
                existing_slug = slug_from_filename(path.name)
                existing_language = DEFAULT_LANGUAGE
            if existing_language == language and existing_slug == slug:
                raise CollisionError(f"El slug ya está publicado por {path.name}.")

    def published_slug(self, filename: str) -> str:
        published_path = self._path(self.notes_dir, filename)
        if not published_path.exists():
            raise NoteNotFound("La nota publicada no existe.")
        raw = self._read_bytes(published_path)
        _, slug, _ = self._strict_publication_metadata(filename, raw)
        return slug

    def published_note_info(self, filename: str) -> dict[str, str]:
        published_path = self._path(self.notes_dir, filename)
        if not published_path.exists():
            raise NoteNotFound("La nota publicada no existe.")
        raw = self._read_bytes(published_path)
        _, slug, language = self._strict_publication_metadata(filename, raw)
        return {"slug": slug, "language": language, "path": note_path(language, slug)}

    def publish_draft(
        self,
        filename: str,
        draft_revision: str,
        published_revision: str,
    ) -> str:
        draft_path = self._path(self.drafts_dir, filename)
        published_path = self._path(self.notes_dir, filename)
        expected_draft_digest = self._validate_revision_token(draft_revision, "draft")

        with self._write_lock:
            if not draft_path.exists():
                raise RevisionConflict("El borrador cambió o dejó de existir.")
            raw = self._read_bytes(draft_path)
            current_draft_digest = hashlib.sha256(raw).hexdigest()
            if not hmac.compare_digest(current_draft_digest, expected_draft_digest):
                raise RevisionConflict("El borrador cambió desde que lo abriste. Recargá la página.")

            replace_existing = self._validate_published_revision(published_path, published_revision)
            _, effective_slug, language = self._strict_publication_metadata(filename, raw)
            self._ensure_unique_published_slug(effective_slug, filename, language)
            self._atomic_write(published_path, raw, replace=replace_existing)

            try:
                current_raw = self._read_bytes(draft_path)
                if not hmac.compare_digest(hashlib.sha256(current_raw).hexdigest(), expected_draft_digest):
                    raise DraftCleanupError(
                        "La fuente se publicó, pero el borrador volvió a cambiar y fue preservado."
                    )
                draft_path.unlink()
                directory_fd = os.open(self.drafts_dir, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            except DraftCleanupError:
                raise
            except (OSError, ContentError) as exc:
                raise DraftCleanupError(
                    "La fuente publicada se escribió, pero no se pudo retirar el borrador."
                ) from exc
        return effective_slug
