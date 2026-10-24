from __future__ import annotations

import hashlib
import io
import json
import os
import re
import time
import unicodedata
import uuid
from dataclasses import dataclass
from html import escape
from pathlib import Path

from PIL import Image, ImageCms, ImageOps


PUBLIC_PREFIX = "/assets/img/notes/"
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_PIXELS = 60_000_000
MAX_SIDE = 12_000
MAX_WIDTH = 1600
LOSSY_QUALITY = 82
SCREENSHOT_QUALITY = 88
LOSSLESS_PREMIUM = 2.5  # lossless wins over lossy for PNG/WebP unless it costs this many times more
KEEP_ORIGINAL_UNLESS_SAVES = 0.15
STAGE_TTL_SECONDS = 24 * 3600
MAX_ALT = 300
MAX_CAPTION = 500

SOURCE_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
STAGED_NAME = re.compile(r"^[0-9a-f]{16}\.(?:webp|png|jpg)$")
PUBLIC_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}-[0-9a-f]{10}\.(?:webp|png|jpg)$")
REUSABLE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}\.(?:webp|png|jpe?g)$")  # includes older, unhashed images


class ImageRejected(ValueError):
    """Raised with a user-facing (Spanish) message when an upload cannot be accepted."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class Processed:
    data: bytes
    ext: str
    width: int
    height: int
    source_format: str
    source_bytes: int
    source_width: int
    source_height: int
    notes: tuple[str, ...]


def _has_alpha(img: Image.Image) -> bool:
    return img.mode == "RGBA" and img.getchannel("A").getextrema()[0] < 255


def _encode(img: Image.Image, fmt: str, **options: object) -> bytes:
    buffer = io.BytesIO()
    img.save(buffer, fmt, **options)
    return buffer.getvalue()


def _to_srgb(img: Image.Image, icc: bytes) -> tuple[Image.Image, bool]:
    try:
        profile = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        if "srgb" in ImageCms.getProfileDescription(profile).lower():
            return img, False
        converted = ImageCms.profileToProfile(img, profile, ImageCms.createProfile("sRGB"), outputMode=img.mode)
        return (converted, True) if converted is not None else (img, False)
    except (ImageCms.PyCMSError, OSError, ValueError):
        return img, False


def process_image(data: bytes) -> Processed:
    """Validate by content, normalize orientation/colour/size and pick the smallest suitable encoding."""
    if not data:
        raise ImageRejected("El archivo está vacío.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ImageRejected(f"La imagen supera el máximo de {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.", 413)

    try:
        img = Image.open(io.BytesIO(data))
        fmt = img.format or ""
        if fmt not in SOURCE_FORMATS:
            raise ImageRejected("Formato no admitido. Usá JPEG, PNG o WebP.", 415)
        width, height = img.size
        if width < 1 or height < 1 or width > MAX_SIDE or height > MAX_SIDE or width * height > MAX_PIXELS:
            raise ImageRejected(
                f"Las dimensiones superan el límite ({MAX_SIDE}px por lado, {MAX_PIXELS // 1_000_000} megapíxeles)."
            )
        if getattr(img, "n_frames", 1) > 1:
            raise ImageRejected("Las imágenes animadas no están admitidas.", 415)
        img.load()
    except ImageRejected:
        raise
    except (OSError, SyntaxError, ValueError, Image.DecompressionBombError) as exc:
        raise ImageRejected("No se pudo leer la imagen: el archivo está dañado o no es una imagen válida.", 415) from exc

    notes: list[str] = []
    info = dict(img.info)
    orientation = img.getexif().get(0x0112, 1)
    has_metadata = bool(info.get("exif") or info.get("xmp") or info.get("XML:com.adobe.xmp") or img.getexif())
    changed = False

    if orientation not in (None, 1):
        img = ImageOps.exif_transpose(img)
        notes.append("Orientación corregida")
        changed = True

    if img.mode.startswith("I"):
        img = img.point(lambda value: value * (1 / 256)).convert("L")
        changed = True
    if img.mode not in ("RGB", "RGBA"):
        transparent = img.mode in ("LA", "PA") or "transparency" in info
        img = img.convert("RGBA" if transparent else "RGB")
        changed = True
    if img.mode == "RGBA" and not _has_alpha(img):
        img = img.convert("RGB")
        changed = True

    if info.get("icc_profile"):
        img, converted = _to_srgb(img, info["icc_profile"])
        if converted:
            notes.append("Perfil de color convertido a sRGB")
            changed = True

    if img.width > MAX_WIDTH:
        new_height = max(1, round(img.height * MAX_WIDTH / img.width))
        img = img.resize((MAX_WIDTH, new_height), Image.Resampling.LANCZOS)
        notes.append(f"Redimensionada de {width}×{height} a {img.width}×{img.height}")
        changed = True

    if has_metadata:
        notes.append("Metadatos (EXIF/GPS) eliminados")

    original = data if not changed and not has_metadata else None
    candidates: dict[str, bytes] = {}
    photographic = fmt == "JPEG" or img.convert("RGB").getcolors(65536) is None
    if fmt == "JPEG":
        candidates["webp"] = _encode(img, "WEBP", quality=LOSSY_QUALITY, method=6)
    else:
        lossless = _encode(img, "WEBP", lossless=True, quality=100, method=4)
        if photographic:
            lossy = _encode(img, "WEBP", quality=SCREENSHOT_QUALITY, method=6)
            candidates["webp"] = lossless if len(lossless) <= len(lossy) * LOSSLESS_PREMIUM else lossy
        else:
            candidates["webp"] = lossless
        if fmt == "PNG":
            candidates["png"] = _encode(img, "PNG", optimize=True)

    ext, best = min(candidates.items(), key=lambda item: len(item[1]))
    if original is not None:
        # Already clean and in-bounds: only re-encode when it clearly pays off.
        if fmt == "WEBP" or len(best) > len(original) * (1 - KEEP_ORIGINAL_UNLESS_SAVES):
            ext, best = SOURCE_FORMATS[fmt], original
            notes.append("Sin cambios: ya estaba optimizada")

    if ext != SOURCE_FORMATS[fmt]:
        notes.append("Convertida a WebP" if ext == "webp" else f"Recomprimida sin pérdida como {ext.upper()}")

    return Processed(
        data=best,
        ext=ext,
        width=img.width,
        height=img.height,
        source_format=fmt,
        source_bytes=len(data),
        source_width=width,
        source_height=height,
        notes=tuple(notes),
    )


def slugify(text: str, *, max_words: int = 6, max_length: int = 48) -> str:
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    words = re.findall(r"[a-z0-9]+", folded)[:max_words]
    return "-".join(words)[:max_length].strip("-")


def figure_html(src: str, alt: str, caption: str, width: int, height: int) -> str:
    """Same structure as the existing `.note-photo` figures; no figcaption when there is no caption."""
    lines = [
        '<figure class="note-photo">',
        f'  <img src="{escape(src, quote=True)}" alt="{escape(alt, quote=True)}" '
        f'width="{width}" height="{height}" loading="lazy" />',
    ]
    if caption:
        lines.append(f"  <figcaption>{escape(caption, quote=False)}</figcaption>")
    lines.append("</figure>")
    return "\n".join(lines)


def _clean_line(value: str, limit: int) -> str:
    return " ".join(value.split())[:limit]


class ImageStore:
    """Processed uploads wait in a private staging directory until the author commits them with alt text."""

    def __init__(self, public_dir: Path, stage_dir: Path) -> None:
        self.public_dir = public_dir
        self.stage_dir = stage_dir

    def stage(self, data: bytes, original_name: str) -> dict[str, object]:
        processed = process_image(data)
        stage_id = hashlib.sha256(data).hexdigest()[:16]
        self.stage_dir.mkdir(parents=True, exist_ok=True)
        self._prune()
        name = f"{stage_id}.{processed.ext}"
        meta = {
            "id": stage_id,
            "file": name,
            "original_name": original_name[:200],
            "width": processed.width,
            "height": processed.height,
        }
        self._atomic_write(self.stage_dir / name, processed.data)
        self._atomic_write(self.stage_dir / f"{stage_id}.json", json.dumps(meta).encode())
        return {
            **meta,
            "preview": f"/media/stage/{name}",
            "bytes": len(processed.data),
            "source": {
                "format": processed.source_format,
                "bytes": processed.source_bytes,
                "width": processed.source_width,
                "height": processed.source_height,
            },
            "format": processed.ext,
            "notes": list(processed.notes),
        }

    def commit(self, stage_id: str, alt: str, caption: str, *, decorative: bool = False) -> dict[str, object]:
        alt, caption = _clean_line(alt, MAX_ALT), _clean_line(caption, MAX_CAPTION)
        if not alt and not decorative:
            raise ImageRejected("Escribí un texto alternativo o marcá la imagen como decorativa.")
        if not re.fullmatch(r"[0-9a-f]{16}", stage_id):
            raise ImageRejected("Identificador de imagen no válido.")
        try:
            meta = json.loads((self.stage_dir / f"{stage_id}.json").read_text(encoding="utf-8"))
            source = self.stage_dir / meta["file"]
            payload = source.read_bytes()
        except (OSError, ValueError, KeyError) as exc:
            raise ImageRejected("La imagen subida venció. Volvé a subirla.", 404) from exc
        if not STAGED_NAME.fullmatch(meta["file"]):
            raise ImageRejected("Identificador de imagen no válido.")

        suffix = stage_id[:10]
        existing = next(self._public_matches(suffix), None)
        reused = existing is not None
        if existing is None:
            stem = slugify(alt) or slugify(Path(meta["original_name"]).stem) or "imagen"
            name = f"{stem}-{suffix}.{meta['file'].rsplit('.', 1)[1]}"
            self.public_dir.mkdir(parents=True, exist_ok=True)
            self._publish_new(self.public_dir / name, payload)
        else:
            name = existing.name
        return self._result(name, alt, caption, reused)

    def reuse(self, name: str, alt: str, caption: str, *, decorative: bool = False) -> dict[str, object]:
        alt, caption = _clean_line(alt, MAX_ALT), _clean_line(caption, MAX_CAPTION)
        if not alt and not decorative:
            raise ImageRejected("Escribí un texto alternativo o marcá la imagen como decorativa.")
        if not REUSABLE_NAME.fullmatch(name) or not (self.public_dir / name).is_file():
            raise ImageRejected("La imagen elegida no existe.", 404)
        return self._result(name, alt, caption, True)

    def _result(self, name: str, alt: str, caption: str, reused: bool) -> dict[str, object]:
        with Image.open(self.public_dir / name) as img:
            width, height = img.size
        src = f"{PUBLIC_PREFIX}{name}"
        return {
            "src": src,
            "width": width,
            "height": height,
            "reused": reused,
            "html": figure_html(src, alt, caption, width, height),
        }

    def _public_matches(self, suffix: str):
        if self.public_dir.is_dir():
            for path in sorted(self.public_dir.glob(f"*-{suffix}.*")):
                if PUBLIC_NAME.fullmatch(path.name) and path.is_file():
                    yield path

    def _atomic_write(self, target: Path, payload: bytes) -> None:
        temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
        try:
            with open(temporary, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)

    def _publish_new(self, target: Path, payload: bytes) -> None:
        """Write without ever replacing an existing asset (hard link fails if the name is taken)."""
        temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
        try:
            with open(temporary, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o664)
            try:
                os.link(temporary, target)
            except FileExistsError:
                pass  # same name means same content hash: an identical asset is already there
        finally:
            temporary.unlink(missing_ok=True)

    def _prune(self) -> None:
        cutoff = time.time() - STAGE_TTL_SECONDS
        for path in self.stage_dir.iterdir():
            try:
                if path.is_file() and path.stat().st_mtime < cutoff:
                    path.unlink()
            except OSError:
                continue
