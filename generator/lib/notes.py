from __future__ import annotations

import html
import json
import re
from datetime import datetime
from email.utils import format_datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

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


def _normalized_host(raw_url: str) -> str:
    host = urlparse(raw_url).netloc.lower()
    if host.startswith("www."):
        return host[4:]
    return host


def _is_external_href(href: str, site_host: str) -> bool:
    candidate = href.strip()
    if not candidate or candidate.startswith(("#", "/", "./", "../")):
        return False

    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} and not parsed.netloc:
        return False

    target_host = parsed.netloc.lower()
    if target_host.startswith("www."):
        target_host = target_host[4:]

    if not target_host:
        return False
    if not site_host:
        return True
    return target_host != site_host


class _ExternalLinkHTMLRewriter(HTMLParser):
    def __init__(self, site_host: str) -> None:
        super().__init__(convert_charrefs=False)
        self.site_host = site_host
        self.parts: list[str] = []

    def _serialize_attrs(self, attrs: list[tuple[str, str | None]]) -> str:
        serialized: list[str] = []
        for key, value in attrs:
            if value is None:
                serialized.append(key)
            else:
                serialized.append(f'{key}="{html.escape(value, quote=True)}"')
        return "" if not serialized else " " + " ".join(serialized)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.parts.append(self._render_tag(tag, attrs, closing=False))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.parts.append(self._render_tag(tag, attrs, closing=True))

    def _render_tag(self, tag: str, attrs: list[tuple[str, str | None]], closing: bool) -> str:
        updated_attrs = attrs
        if tag == "a":
            attr_map = dict(attrs)
            href = attr_map.get("href") or ""
            if _is_external_href(href, self.site_host):
                attr_map["target"] = "_blank"
                existing_rel = {item for item in (attr_map.get("rel") or "").split() if item}
                existing_rel.update({"noopener", "noreferrer"})
                attr_map["rel"] = " ".join(sorted(existing_rel))

                updated_attrs = []
                seen: set[str] = set()
                for key, value in attrs:
                    if key in {"target", "rel"}:
                        if key in seen:
                            continue
                        seen.add(key)
                    updated_attrs.append((key, attr_map[key]))

                if "target" not in seen:
                    updated_attrs.append(("target", attr_map["target"]))
                if "rel" not in seen:
                    updated_attrs.append(("rel", attr_map["rel"]))

        suffix = " /" if closing else ""
        return f"<{tag}{self._serialize_attrs(updated_attrs)}{suffix}>"

    def handle_endtag(self, tag: str) -> None:
        self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_entityref(self, name: str) -> None:
        self.parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.parts.append(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        self.parts.append(f"<!--{data}-->")

    def handle_decl(self, decl: str) -> None:
        self.parts.append(f"<!{decl}>")

    def handle_pi(self, data: str) -> None:
        self.parts.append(f"<?{data}>")

    def rewritten_html(self) -> str:
        return "".join(self.parts)


def _rewrite_external_links(html_text: str, site_domain: str) -> str:
    parser = _ExternalLinkHTMLRewriter(_normalized_host(site_domain))
    parser.feed(html_text)
    parser.close()
    return parser.rewritten_html()


def load_notes(notes_dir: Path, site_domain: str = "") -> list[dict[str, Any]]:
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
        rendered_html = _rewrite_external_links(renderer.convert(body), site_domain)

        notes.append(
            {
                "title": title,
                "slug": slug,
                "date": dt,
                "date_iso": dt.isoformat(),
                "date_label": utils.format_date(dt),
                "tags": tags,
                "excerpt": utils.excerpt_from_markdown(body),
                "body": body,
                "html": rendered_html,
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
