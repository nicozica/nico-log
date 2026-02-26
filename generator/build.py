#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape

from lib import feeds, notes, now_playing, status, utils, weather


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build static portal output")
    parser.add_argument("--output-dir", default="", help="Output directory for static site")
    parser.add_argument("--cache-dir", default="", help="Cache directory for dynamic data")
    parser.add_argument("--content-dir", default="", help="Content directory")
    parser.add_argument("--templates-dir", default="", help="Templates directory")
    parser.add_argument("--static-dir", default="", help="Static assets directory")
    return parser.parse_args()


def render_template(
    env: Environment,
    template_name: str,
    destination: Path,
    context: dict[str, Any],
) -> None:
    utils.ensure_dir(destination.parent)
    html = env.get_template(template_name).render(**context)
    destination.write_text(html, encoding="utf-8")


def _to_positive_int(raw_value: Any, default: int) -> int:
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return default
    if value <= 0:
        return default
    return value


def main() -> None:
    args = parse_args()

    project_root = Path(__file__).resolve().parents[1]
    content_dir = Path(args.content_dir) if args.content_dir else project_root / "content"
    templates_dir = Path(args.templates_dir) if args.templates_dir else project_root / "templates"
    static_dir = Path(args.static_dir) if args.static_dir else project_root / "static"
    output_dir = Path(args.output_dir) if args.output_dir else project_root / "dist"
    cache_dir = Path(args.cache_dir) if args.cache_dir else project_root / "cache"

    utils.ensure_dir(cache_dir)
    utils.clean_output_dir(output_dir)

    config = utils.load_yaml(content_dir / "config.yaml", default={})
    site = config.get("site", {})
    about = config.get("about", {})
    status_bar = config.get("status_bar", {})
    footer = config.get("footer", {})
    now_playing_settings = config.get("now_playing", {})
    home_settings = config.get("home", {})
    notes_settings = config.get("notes", {})
    tiny_lines = utils.load_lines(content_dir / "tiny.txt")

    if not isinstance(site, dict):
        site = {}
    if not isinstance(status_bar, dict):
        status_bar = {}
    if not isinstance(footer, dict):
        footer = {}
    if not isinstance(now_playing_settings, dict):
        now_playing_settings = {}
    if not isinstance(home_settings, dict):
        home_settings = {}
    if not isinstance(notes_settings, dict):
        notes_settings = {}

    site_power = str(site.get("power", "")).strip()
    if not site_power:
        site_power = str(status_bar.get("power_label", "grid")).strip() or "grid"
    site = {**site, "power": site_power}

    status_bar = {
        "power_label": site_power,
    }
    footer_links = footer.get("links", [])
    if not isinstance(footer_links, list):
        footer_links = []

    normalized_footer_links: list[dict[str, str]] = []
    for item in footer_links:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label", "")).strip()
        href = str(item.get("href", "")).strip()
        if label and href:
            normalized_footer_links.append({"label": label, "href": href})
    footer = {"links": normalized_footer_links}

    all_notes = notes.load_notes(content_dir / "notes")
    all_links, links_source = feeds.fetch_links(
        content_path=content_dir / "feeds.yaml",
        cache_dir=cache_dir,
        ttl_minutes=int(config.get("feeds_ttl_minutes", 30)),
        limit=120,
    )
    weather_data, weather_source = weather.fetch_weather(config, cache_dir)
    status_bundle, _ = status.fetch_status(config, cache_dir)
    now_data, now_history, now_source = now_playing.fetch_now(config, cache_dir, content_dir)

    built_at = datetime.now().astimezone()
    build_id = built_at.strftime("%Y%m%d%H%M%S")
    build_info = {
        "updated_iso": built_at.isoformat(),
        "updated_label": built_at.strftime("%Y-%m-%d %H:%M"),
    }
    now_source_url = str(now_playing_settings.get("source_url", "")).strip()
    now_stream_url = str(now_playing_settings.get("stream_url", "")).strip() or "https://www.blurfm.com/"
    now_api_url = now_source_url
    parsed_now_url = urlparse(now_source_url)
    if parsed_now_url.scheme and parsed_now_url.netloc:
        host = parsed_now_url.netloc.lower()
        if host in {"nico.com.ar", "www.nico.com.ar"}:
            now_api_url = parsed_now_url.path or "/api/now-playing"
            if parsed_now_url.query:
                now_api_url = f"{now_api_url}?{parsed_now_url.query}"
    now_refresh_enabled = now_api_url.startswith("/")
    now_data = {**now_data, "refresh_enabled": now_refresh_enabled}

    latest_notes_title = str(home_settings.get("latest_notes_title", "Últimas notas")).strip() or "Últimas notas"
    latest_notes_subtitle = str(home_settings.get("latest_notes_subtitle", "")).strip()
    latest_notes_limit = _to_positive_int(home_settings.get("latest_notes_limit", 4), default=4)
    notes_page_size = _to_positive_int(notes_settings.get("page_size", 10), default=10)
    status_summary = status_bundle.get("summary", {})
    tiny_thing = utils.pick_tiny_thing(tiny_lines, built_at)

    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    base_context = {
        "site": site,
        "about": about,
        "status_bar": status_bar,
        "footer": footer,
        "build": build_info,
        "status_summary": status_summary,
        "status": status_bundle.get("status", {}),
        "weather": weather_data,
        "now": now_data,
        "data_sources": {
            "links": links_source,
            "weather": weather_source,
            "now": now_source,
            "status": status_bundle.get("status", {}).get("source", "unknown"),
        },
        "build_id": build_id,
        "now_api_url": now_api_url,
        "now_stream_url": now_stream_url,
    }

    render_template(
        env,
        "index.html",
        output_dir / "index.html",
        {
            **base_context,
            "page_title": "Inicio",
            "current_path": "/",
            "latest_notes": all_notes[:latest_notes_limit],
            "links_preview": all_links[:6],
            "latest_notes_title": latest_notes_title,
            "latest_notes_subtitle": latest_notes_subtitle,
            "tiny_thing": tiny_thing,
        },
    )

    total_notes = len(all_notes)
    total_pages = max(1, (total_notes + notes_page_size - 1) // notes_page_size)

    for page in range(1, total_pages + 1):
        start = (page - 1) * notes_page_size
        end = start + notes_page_size
        page_notes = all_notes[start:end]

        if page == 1:
            destination = output_dir / "notes" / "index.html"
            current_path = "/notes/"
        else:
            destination = output_dir / "notes" / "page" / str(page) / "index.html"
            current_path = f"/notes/page/{page}/"

        prev_url = ""
        next_url = ""
        if page > 1:
            prev_url = "/notes/" if page == 2 else f"/notes/page/{page - 1}/"
        if page < total_pages:
            next_url = f"/notes/page/{page + 1}/"

        pagination = {
            "page": page,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "prev_url": prev_url,
            "next_url": next_url,
        }

        render_template(
            env,
            "notes_index.html",
            destination,
            {
                **base_context,
                "page_title": "Notas",
                "current_path": current_path,
                "notes": page_notes,
                "pagination": pagination,
            },
        )

    for note in all_notes:
        render_template(
            env,
            "note_detail.html",
            output_dir / "notes" / note["slug"] / "index.html",
            {
                **base_context,
                "page_title": note["title"],
                "current_path": f"/notes/{note['slug']}/",
                "note": note,
            },
        )

    render_template(
        env,
        "links_index.html",
        output_dir / "links" / "index.html",
        {
            **base_context,
            "page_title": "Links",
            "current_path": "/links/",
            "links": all_links,
        },
    )

    render_template(
        env,
        "now_index.html",
        output_dir / "now" / "index.html",
        {
            **base_context,
            "page_title": "Ahora sonando",
            "current_path": "/now/",
            "history": now_history,
        },
    )

    render_template(
        env,
        "about_index.html",
        output_dir / "about" / "index.html",
        {
            **base_context,
            "page_title": "Acerca",
            "current_path": "/about/",
        },
    )

    utils.ensure_dir(output_dir / "notes")
    (output_dir / "notes" / "rss.xml").write_text(notes.build_rss(all_notes, site), encoding="utf-8")
    (output_dir / "notes" / "atom.xml").write_text(
        notes.build_atom(all_notes, site, built_at), encoding="utf-8"
    )
    (output_dir / "notes" / "feed.json").write_text(
        notes.build_json_feed(all_notes, site), encoding="utf-8"
    )

    utils.copy_static_tree(static_dir, output_dir / "assets")

    favicon_source = static_dir / "favicon.svg"
    if favicon_source.exists():
        (output_dir / "favicon.svg").write_text(favicon_source.read_text(encoding="utf-8"), encoding="utf-8")


if __name__ == "__main__":
    main()
