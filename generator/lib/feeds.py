from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import requests
try:
    import feedparser
except ModuleNotFoundError:  # pragma: no cover - runtime dependency fallback
    feedparser = None

from . import utils

PREVIEW_SOURCE_LIMITS = {
    "Hacker News Frontpage": 1,
    "The Verge": 1,
}


def _safe_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None

    try:
        return utils.to_datetime(value)
    except Exception:
        return None


def _entry_datetime(entry: dict[str, Any]) -> datetime | None:
    for field in ("published", "updated", "date", "created", "issued", "dc_date", "dc:date", "pubDate"):
        parsed_value = _safe_datetime(entry.get(field))
        if parsed_value is not None:
            return parsed_value

    for field in ("published_parsed", "updated_parsed", "created_parsed", "date_parsed"):
        parsed = entry.get(field)
        if parsed:
            return datetime(*parsed[:6], tzinfo=timezone.utc)

    return None


def _parse_xml_fallback(content: bytes) -> list[dict[str, str]]:
    root = ElementTree.fromstring(content)
    entries: list[dict[str, str]] = []

    # RSS style feeds.
    for item in root.findall(".//{*}item"):
        title = (item.findtext("{*}title") or "(untitled)").strip()
        link = (item.findtext("{*}link") or "").strip()
        published = (
            item.findtext("{*}pubDate")
            or item.findtext("{*}published")
            or item.findtext("{*}updated")
            or item.findtext("{http://purl.org/dc/elements/1.1/}date")
            or item.findtext("{*}date")
            or ""
        ).strip()
        if link:
            entries.append({"title": title, "link": link, "published": published})

    # Atom style feeds.
    for entry in root.findall(".//{*}entry"):
        title = (entry.findtext("{*}title") or "(untitled)").strip()
        link = ""
        for link_node in entry.findall("{*}link"):
            href = (link_node.attrib.get("href") or "").strip()
            rel = (link_node.attrib.get("rel") or "alternate").strip()
            if href and rel in {"alternate", ""}:
                link = href
                break
            if href and not link:
                link = href
        published = (
            entry.findtext("{*}published")
            or entry.findtext("{*}updated")
            or entry.findtext("{http://purl.org/dc/elements/1.1/}date")
            or entry.findtext("{*}date")
            or ""
        ).strip()
        if link:
            entries.append({"title": title, "link": link, "published": published})

    return entries


def _fetch_feed(feed_name: str, feed_url: str, timeout_seconds: int = 6) -> list[dict[str, str]]:
    response = requests.get(
        feed_url,
        timeout=timeout_seconds,
        headers={"User-Agent": "pizero-portal/1.0 (+https://nico.com.ar)"},
    )
    response.raise_for_status()

    items: list[dict[str, str]] = []
    if feedparser is not None:
        parsed = feedparser.parse(response.content)
        parsed_entries = parsed.entries[:12]
    else:
        parsed_entries = _parse_xml_fallback(response.content)[:12]

    for entry in parsed_entries:
        link = str(entry.get("link") or "").strip()
        title = html.unescape(str(entry.get("title") or "(untitled)")).strip()
        if not link:
            continue

        published = _entry_datetime(entry)
        items.append(
            {
                "title": title,
                "url": link,
                "source": feed_name,
                "published": published.isoformat() if published is not None else "",
            }
        )

    return items


def _fallback_items(feed_list: list[dict[str, Any]]) -> dict[str, Any]:
    now = datetime.now(tz=timezone.utc)
    links = []
    for index, feed in enumerate(feed_list[:10], start=1):
        links.append(
            {
                "title": f"Offline cached placeholder #{index}",
                "url": feed.get("url", "https://example.com"),
                "source": feed.get("name", "feed"),
                "published": now.isoformat(),
            }
        )

    return {"updated_at": now.isoformat(), "items": links}


def fetch_links(content_path: Path, cache_dir: Path, ttl_minutes: int, limit: int = 120) -> tuple[list[dict[str, Any]], str]:
    feeds_yaml = utils.load_yaml(content_path, default={})
    feed_list = list(feeds_yaml.get("feeds", []))

    def fetcher() -> dict[str, Any]:
        all_items: list[dict[str, str]] = []
        for feed in feed_list:
            name = str(feed.get("name", "feed"))
            url = str(feed.get("url", "")).strip()
            if not url:
                continue
            try:
                all_items.extend(_fetch_feed(name, url))
            except Exception:
                # Individual feed errors are expected in unreliable environments.
                continue

        if not all_items:
            raise RuntimeError("no feed data fetched")

        all_items.sort(
            key=lambda item: _safe_datetime(item.get("published")) or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return {
            "updated_at": datetime.now(tz=timezone.utc).isoformat(),
            "items": all_items[:limit],
        }

    cache_file = cache_dir / "feeds.json"
    payload, source = utils.fetch_json_with_cache(
        cache_file,
        ttl_seconds=ttl_minutes * 60,
        fetcher=fetcher,
        fallback=lambda: _fallback_items(feed_list),
    )

    items = []
    for raw in payload.get("items", [])[:limit]:
        published = _safe_datetime(raw.get("published"))
        items.append(
            {
                "title": html.unescape(str(raw.get("title", "(untitled)"))),
                "url": str(raw.get("url", "#")),
                "source": str(raw.get("source", "feed")),
                "published": published.isoformat() if published is not None else "",
                "published_label": utils.format_date(published) if published is not None else "",
            }
        )

    return items, source


def select_preview_links(items: list[dict[str, Any]], limit: int = 6) -> list[dict[str, Any]]:
    if limit <= 0:
        return []

    preview_candidates = items[: max(limit * 8, 24)]
    selected: list[dict[str, Any]] = []
    selected_urls: set[str] = set()
    source_counts: dict[str, int] = {}

    # First pass: maximize source diversity inside a recent candidate window.
    for item in preview_candidates:
        source = str(item.get("source", "")).strip()
        url = str(item.get("url", "")).strip()
        if not source or not url or url in selected_urls or source_counts.get(source, 0) >= 1:
            continue

        selected.append(item)
        selected_urls.add(url)
        source_counts[source] = source_counts.get(source, 0) + 1
        if len(selected) >= limit:
            return selected

    # Second pass: fill remaining slots by recency with stricter caps on fast-moving sources.
    for item in preview_candidates:
        source = str(item.get("source", "")).strip()
        url = str(item.get("url", "")).strip()
        if not source or not url or url in selected_urls:
            continue

        source_cap = PREVIEW_SOURCE_LIMITS.get(source, 2)
        if source_counts.get(source, 0) >= source_cap:
            continue

        selected.append(item)
        selected_urls.add(url)
        source_counts[source] = source_counts.get(source, 0) + 1
        if len(selected) >= limit:
            return selected

    return selected[:limit]
