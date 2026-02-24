from __future__ import annotations

import html
import json
import re
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path
from typing import Any

import markdown
import yaml

from . import utils

FRONT_MATTER_PATTERN = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def _split_front_matter(raw: str) -> tuple[dict[str, Any], str]:
    match = FRONT_MATTER_PATTERN.match(raw)
    if not match:
        return {}, raw

    front_raw, body = match.groups()
    data = yaml.safe_load(front_raw) or {}
    return data, body.strip()


def _slug_from_path(path: Path) -> str:
    stem = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", path.stem)
    return utils.slugify(stem)


def load_notes(notes_dir: Path) -> list[dict[str, Any]]:
    renderer = markdown.Markdown(extensions=["extra", "sane_lists"])
    notes: list[dict[str, Any]] = []

    for path in sorted(notes_dir.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        meta, body = _split_front_matter(raw)

        dt = utils.to_datetime(meta.get("date"))
        slug = utils.slugify(str(meta.get("slug") or _slug_from_path(path)))
        title = str(meta.get("title") or slug.replace("-", " ").title())
        tags = [str(tag) for tag in meta.get("tags", [])]

        # Reset parser state between files.
        renderer.reset()

        notes.append(
            {
                "title": title,
                "slug": slug,
                "date": dt,
                "date_iso": dt.isoformat(),
                "date_label": dt.strftime("%Y-%m-%d"),
                "tags": tags,
                "excerpt": utils.excerpt_from_markdown(body),
                "body": body,
                "html": renderer.convert(body),
            }
        )

    notes.sort(key=lambda note: note["date"], reverse=True)
    return notes


def _site_url(domain: str, path: str) -> str:
    return domain.rstrip("/") + path


def build_rss(notes: list[dict[str, Any]], site: dict[str, Any]) -> str:
    site_title = html.escape(site["title"])
    site_domain = site["domain"]
    description = html.escape(site.get("description", ""))

    items: list[str] = []
    for note in notes[:30]:
        note_url = _site_url(site_domain, f"/notes/{note['slug']}/")
        items.append(
            "\n".join(
                [
                    "<item>",
                    f"<title>{html.escape(note['title'])}</title>",
                    f"<link>{html.escape(note_url)}</link>",
                    f"<guid>{html.escape(note_url)}</guid>",
                    f"<pubDate>{format_datetime(note['date'])}</pubDate>",
                    f"<description>{html.escape(note['excerpt'])}</description>",
                    "</item>",
                ]
            )
        )

    return "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<rss version="2.0">',
            "<channel>",
            f"<title>{site_title}</title>",
            f"<link>{html.escape(site_domain)}</link>",
            f"<description>{description}</description>",
            *items,
            "</channel>",
            "</rss>",
        ]
    )


def build_atom(notes: list[dict[str, Any]], site: dict[str, Any], built_at: datetime) -> str:
    site_domain = site["domain"]
    feed_url = _site_url(site_domain, "/notes/atom.xml")

    entries: list[str] = []
    for note in notes[:30]:
        note_url = _site_url(site_domain, f"/notes/{note['slug']}/")
        entries.append(
            "\n".join(
                [
                    "<entry>",
                    f"<title>{html.escape(note['title'])}</title>",
                    f"<id>{html.escape(note_url)}</id>",
                    f"<link href=\"{html.escape(note_url)}\" />",
                    f"<updated>{note['date'].isoformat()}</updated>",
                    f"<summary>{html.escape(note['excerpt'])}</summary>",
                    "</entry>",
                ]
            )
        )

    return "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<feed xmlns="http://www.w3.org/2005/Atom">',
            f"<title>{html.escape(site['title'])}</title>",
            f"<id>{html.escape(feed_url)}</id>",
            f"<link href=\"{html.escape(feed_url)}\" rel=\"self\" />",
            f"<updated>{built_at.isoformat()}</updated>",
            *entries,
            "</feed>",
        ]
    )


def build_json_feed(notes: list[dict[str, Any]], site: dict[str, Any]) -> str:
    payload = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": site["title"],
        "home_page_url": site["domain"],
        "feed_url": _site_url(site["domain"], "/notes/feed.json"),
        "description": site.get("description", ""),
        "items": [
            {
                "id": _site_url(site["domain"], f"/notes/{note['slug']}/"),
                "url": _site_url(site["domain"], f"/notes/{note['slug']}/"),
                "title": note["title"],
                "content_html": note["html"],
                "summary": note["excerpt"],
                "date_published": note["date_iso"],
                "tags": note["tags"],
            }
            for note in notes[:30]
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
