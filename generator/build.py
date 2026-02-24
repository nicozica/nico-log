#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

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
    webring = utils.load_yaml(content_dir / "webring.yaml", default={}).get("ring", [])
    tiny_lines = utils.load_lines(content_dir / "tiny.txt")

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
    build_info = {
        "updated_iso": built_at.isoformat(),
        "updated_label": built_at.strftime("%Y-%m-%d %H:%M"),
    }
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
        "webring": webring,
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
    }

    render_template(
        env,
        "index.html",
        output_dir / "index.html",
        {
            **base_context,
            "page_title": "Home",
            "current_path": "/",
            "latest_notes": all_notes[:3],
            "links_preview": all_links[:10],
            "tiny_thing": tiny_thing,
        },
    )

    render_template(
        env,
        "notes_index.html",
        output_dir / "notes" / "index.html",
        {
            **base_context,
            "page_title": "Notes",
            "current_path": "/notes/",
            "notes": all_notes,
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
            "page_title": "Now Playing",
            "current_path": "/now/",
            "history": now_history,
        },
    )

    render_template(
        env,
        "status_index.html",
        output_dir / "status" / "index.html",
        {
            **base_context,
            "page_title": "Status",
            "current_path": "/status/",
        },
    )

    render_template(
        env,
        "about_index.html",
        output_dir / "about" / "index.html",
        {
            **base_context,
            "page_title": "About",
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


if __name__ == "__main__":
    main()
