from __future__ import annotations

import io
import random
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from editor.app import create_app
from editor.images import ImageRejected, ImageStore, figure_html, process_image, slugify


def encode(img: Image.Image, fmt: str, **options: object) -> bytes:
    buffer = io.BytesIO()
    img.save(buffer, fmt, **options)
    return buffer.getvalue()


def photo(width: int, height: int) -> Image.Image:
    rng = random.Random(7)
    img = Image.effect_noise((width, height), 64).convert("RGB")
    return Image.blend(img, Image.new("RGB", (width, height), (90, 140, 200)), 0.5) if rng.random() else img


def screenshot(width: int = 800, height: int = 400) -> Image.Image:
    img = Image.new("RGB", (width, height), "white")
    for y in range(20, height, 40):
        img.paste((20, 20, 20), (20, y, width - 20, y + 6))
    return img


class ProcessImageTests(unittest.TestCase):
    def test_large_jpeg_is_resized_converted_and_stripped(self) -> None:
        exif = Image.Exif()
        exif[0x010F] = "Camera"
        exif[0x8825] = {1: "S"}  # GPS IFD
        data = encode(photo(3200, 2000), "JPEG", exif=exif.tobytes())
        result = process_image(data)
        self.assertEqual((result.width, result.height), (1600, 1000))
        self.assertEqual(result.ext, "webp")
        with Image.open(io.BytesIO(result.data)) as out:
            self.assertEqual(out.format, "WEBP")
            self.assertFalse(out.getexif())
        self.assertTrue(any("Metadatos" in note for note in result.notes))
        self.assertTrue(any("Redimensionada" in note for note in result.notes))

    def test_never_upscales(self) -> None:
        result = process_image(encode(screenshot(400, 200), "PNG"))
        self.assertEqual((result.width, result.height), (400, 200))

    def test_exif_orientation_is_applied(self) -> None:
        exif = Image.Exif()
        exif[0x0112] = 6  # rotate 90° CW to display: stored 400x200 shows as 200x400
        data = encode(photo(400, 200), "JPEG", exif=exif.tobytes())
        result = process_image(data)
        self.assertEqual((result.width, result.height), (200, 400))
        self.assertIn("Orientación corregida", result.notes)

    def test_png_screenshot_stays_lossless(self) -> None:
        source = screenshot()
        result = process_image(encode(source, "PNG"))
        with Image.open(io.BytesIO(result.data)) as out:
            self.assertEqual(list(out.convert("RGB").getdata()), list(source.getdata()))

    def test_png_transparency_is_kept(self) -> None:
        img = Image.new("RGBA", (64, 64), (255, 0, 0, 0))
        img.paste((0, 255, 0, 255), (0, 0, 32, 32))
        result = process_image(encode(img, "PNG"))
        with Image.open(io.BytesIO(result.data)) as out:
            self.assertEqual(out.convert("RGBA").getpixel((60, 60))[3], 0)

    def test_clean_webp_is_not_recompressed(self) -> None:
        data = encode(screenshot(600, 300), "WEBP", lossless=True)
        result = process_image(data)
        self.assertEqual(result.data, data)
        self.assertIn("Sin cambios: ya estaba optimizada", result.notes)

    def test_rejects_non_images_and_unsupported_formats(self) -> None:
        for payload in (b"", b"not an image", b"<svg xmlns='http://www.w3.org/2000/svg'/>", encode(screenshot(), "GIF")):
            with self.assertRaises(ImageRejected):
                process_image(payload)

    def test_rejects_extension_spoofing_by_content(self) -> None:
        with self.assertRaises(ImageRejected):
            process_image(b"MZ\x90\x00" + b"\x00" * 200)

    def test_rejects_truncated_image(self) -> None:
        data = encode(photo(800, 600), "JPEG")
        with self.assertRaises(ImageRejected):
            process_image(data[: len(data) // 2])

    def test_rejects_oversized_dimensions(self) -> None:
        with self.assertRaises(ImageRejected):
            process_image(encode(Image.new("L", (12_500, 10)), "PNG"))

    def test_rejects_animated_webp(self) -> None:
        frames = [Image.new("RGB", (32, 32), color) for color in ("red", "blue")]
        data = encode(frames[0], "WEBP", save_all=True, append_images=frames[1:], duration=100)
        with self.assertRaises(ImageRejected):
            process_image(data)


class HelperTests(unittest.TestCase):
    def test_slugify_is_ascii_and_bounded(self) -> None:
        self.assertEqual(slugify("¡Pipeta, una Raspberry Pi Zero 2 W encendida!"), "pipeta-una-raspberry-pi-zero-2")
        self.assertEqual(slugify("???"), "")

    def test_figure_html_matches_existing_structure_and_escapes(self) -> None:
        html = figure_html("/assets/img/notes/x-0123456789.webp", 'A "quote" & <b>', "Pie <i>", 10, 5)
        self.assertEqual(
            html,
            '<figure class="note-photo">\n'
            '  <img src="/assets/img/notes/x-0123456789.webp" alt="A &quot;quote&quot; &amp; &lt;b&gt;" '
            'width="10" height="5" loading="lazy" />\n'
            "  <figcaption>Pie &lt;i&gt;</figcaption>\n"
            "</figure>",
        )

    def test_figure_without_caption_has_no_figcaption(self) -> None:
        self.assertNotIn("figcaption", figure_html("/a.webp", "alt", "", 1, 1))


class ImageStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.store = ImageStore(root / "public", root / "stage")
        self.data = encode(photo(1200, 800), "JPEG")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_commit_creates_descriptive_hashed_file_and_dedupes_across_languages(self) -> None:
        staged = self.store.stage(self.data, "IMG_0001.JPG")
        self.assertFalse(list(self.store.public_dir.glob("*")) if self.store.public_dir.exists() else [])
        es = self.store.commit(staged["id"], "Una foto de prueba", "Pie ES")
        self.assertRegex(es["src"], r"^/assets/img/notes/una-foto-de-prueba-[0-9a-f]{10}\.(?:webp|jpg)$")
        self.assertFalse(es["reused"])
        again = self.store.stage(self.data, "otra.jpg")
        en = self.store.commit(again["id"], "A test photo", "EN caption")
        self.assertEqual(en["src"], es["src"])
        self.assertTrue(en["reused"])
        self.assertIn("EN caption", en["html"])
        self.assertIn('alt="A test photo"', en["html"])
        self.assertEqual(len(list(self.store.public_dir.iterdir())), 1)

    def test_distinct_images_with_same_alt_do_not_collide(self) -> None:
        first = self.store.commit(self.store.stage(self.data, "a.jpg")["id"], "Misma descripción", "")
        other = encode(photo(900, 900), "JPEG")
        second = self.store.commit(self.store.stage(other, "b.jpg")["id"], "Misma descripción", "")
        self.assertNotEqual(first["src"], second["src"])

    def test_alt_is_required_unless_decorative(self) -> None:
        staged = self.store.stage(self.data, "a.jpg")
        with self.assertRaises(ImageRejected):
            self.store.commit(staged["id"], "   ", "")
        result = self.store.commit(staged["id"], "", "", decorative=True)
        self.assertIn('alt=""', result["html"])

    def test_commit_rejects_unknown_or_malicious_ids(self) -> None:
        for bad in ("../../etc/passwd", "zzzz", "0" * 16):
            with self.assertRaises(ImageRejected):
                self.store.commit(bad, "alt", "")

    def test_reuse_only_accepts_existing_published_names(self) -> None:
        committed = self.store.commit(self.store.stage(self.data, "a.jpg")["id"], "algo", "")
        name = committed["src"].rsplit("/", 1)[1]
        self.assertTrue(self.store.reuse(name, "otro alt", "")["reused"])
        for bad in ("../x.webp", "nope-0123456789.webp", "pipeta-alpine-linux.webp"):
            with self.assertRaises(ImageRejected):
                self.store.reuse(bad, "alt", "")

    def test_existing_assets_are_never_overwritten(self) -> None:
        staged = self.store.stage(self.data, "a.jpg")
        self.store.public_dir.mkdir(parents=True, exist_ok=True)
        target = self.store.public_dir / f"algo-{staged['id'][:10]}.{staged['format']}"
        precious = encode(Image.new("RGB", (4, 4), "red"), "WEBP")
        target.write_bytes(precious)
        self.store.commit(staged["id"], "algo", "")
        self.assertEqual(target.read_bytes(), precious)


class ImageEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "content" / "notes").mkdir(parents=True)
        (self.root / "content" / "drafts").mkdir(parents=True)
        self.client = create_app(self.root, testing=True).test_client()
        self.client.get("/notes/new")
        with self.client.session_transaction() as session:
            self.token = session["_csrf_token"]

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def upload(self, data: bytes, name: str = "foto.jpg", token: str | None = None):
        return self.client.post(
            "/media/stage",
            data={"_csrf_token": self.token if token is None else token, "file": (io.BytesIO(data), name)},
            content_type="multipart/form-data",
        )

    def test_requires_csrf(self) -> None:
        response = self.upload(encode(screenshot(), "PNG"), token="wrong")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())
        self.assertFalse((self.root / "static").exists())

    def test_stage_then_commit_then_serve(self) -> None:
        staged = self.upload(encode(photo(2400, 1200), "JPEG")).get_json()
        self.assertEqual((staged["width"], staged["height"]), (1600, 800))
        self.assertEqual(self.client.get(staged["preview"]).status_code, 200)
        response = self.client.post(
            "/media/commit",
            data={"_csrf_token": self.token, "id": staged["id"], "alt": "Vista del puerto", "caption": "Atardecer"},
        )
        body = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue((self.root / "static" / "img" / "notes" / body["src"].rsplit("/", 1)[1]).is_file())
        self.assertIn("<figcaption>Atardecer</figcaption>", body["html"])
        self.assertEqual(self.client.get(body["src"]).status_code, 200)

    def test_rejects_disguised_file_with_json_error(self) -> None:
        response = self.upload(b"<?php echo 1; ?>", name="evil.jpg")
        self.assertEqual(response.status_code, 415)
        self.assertIn("error", response.get_json())
        self.assertFalse((self.root / "static").exists())

    def test_oversized_upload_returns_json_413(self) -> None:
        response = self.upload(b"\0" * (16 * 1024 * 1024))
        self.assertEqual(response.status_code, 413)
        self.assertIn("error", response.get_json())

    def test_path_traversal_is_blocked(self) -> None:
        for path in ("/media/stage/..%2f..%2fapp.py", "/media/stage/x.webp", "/assets/img/notes/..%2f..%2f..%2frequirements.txt"):
            self.assertEqual(self.client.get(path).status_code, 404)
        response = self.client.post("/media/commit", data={"_csrf_token": self.token, "existing": "../../x", "alt": "a"})
        self.assertEqual(response.status_code, 404)

    def test_other_posts_keep_small_body_limit(self) -> None:
        response = self.client.post("/notes/new", data={"_csrf_token": self.token, "body": "x" * (800 * 1024)})
        self.assertEqual(response.status_code, 413)

    def test_edit_page_offers_images_from_other_language_version(self) -> None:
        notes = self.root / "content" / "notes"
        images = self.root / "static" / "img" / "notes"
        images.mkdir(parents=True)
        (images / "foto-0123456789.webp").write_bytes(b"x")
        for lang, name in (("es", "2026-10-01-hola.md"), ("en", "2026-10-01-hello.md")):
            body = "![x](/assets/img/notes/foto-0123456789.webp)" if lang == "es" else "Hello"
            (notes / name).write_text(
                f"---\ntitle: T\ndate: '2026-10-01'\nlang: {lang}\nnote_id: 2026-10-01-hola\nslug: {name[11:-3]}\n---\n\n{body}\n",
                encoding="utf-8",
            )
        page = self.client.get("/notes/2026-10-01-hello.md/edit").get_data(as_text=True)
        self.assertIn("/assets/img/notes/foto-0123456789.webp", page)
        self.assertIn("data-image-dialog", page)


if __name__ == "__main__":
    unittest.main()
