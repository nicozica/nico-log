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

FRONT_MATTER_PATTERN = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", re.DOTALL)

LANGUAGE_SETTINGS: dict[str, dict[str, str]] = {
    "es": {
        "code": "es",
        "name": "Español",
        "home_path": "/es/",
        "notes_index_path": "/es/notas/",
        "news_path": "/es/noticias/",
        "about_path": "/es/acerca/",
    },
    "en": {
        "code": "en",
        "name": "English",
        "home_path": "/en/",
        "notes_index_path": "/en/notes/",
        "news_path": "/en/news/",
        "about_path": "/en/about/",
    },
}

DEFAULT_LANGUAGE = "es"
RESERVED_NOTE_SLUGS: dict[str, frozenset[str]] = {
    "es": frozenset({"notas", "noticias", "acerca"}),
    "en": frozenset({"notes", "news", "about"}),
}


def normalize_language(raw_value: Any, default: str = DEFAULT_LANGUAGE) -> str:
    candidate = str(raw_value or default).strip().lower()
    if candidate in LANGUAGE_SETTINGS:
        return candidate
    return default


def language_settings(language: str) -> dict[str, str]:
    return LANGUAGE_SETTINGS[normalize_language(language)]


def note_id_from_filename(filename: str) -> str:
    return filename.removesuffix('.md')


def note_id_from_path(path: Path) -> str:
    return note_id_from_filename(path.name)


def note_id_from_metadata(metadata: dict[str, Any], path: Path) -> str:
    explicit = str(metadata.get('note_id', '')).strip()
    return explicit or note_id_from_path(path)


def note_path(language: str, slug: str) -> str:
    return f"/{normalize_language(language)}/{slug}/"


def section_path(language: str, section: str) -> str:
    return language_settings(language)[section]


def feed_paths(language: str) -> dict[str, str]:
    notes_index = section_path(language, 'notes_index_path').rstrip('/')
    return {
        'rss': f'{notes_index}/rss.xml',
        'atom': f'{notes_index}/atom.xml',
        'json': f'{notes_index}/feed.json',
    }


def _split_front_matter(raw: str) -> tuple[dict[str, Any], str]:
    match = FRONT_MATTER_PATTERN.match(raw)
    if not match:
        return {}, raw

    front_raw, body = match.groups()
    try:
        data = yaml.safe_load(front_raw) or {}
    except yaml.YAMLError:
        return {}, body.strip()
    return data, body.strip()


def _slug_from_path(path: Path) -> str:
    stem = re.sub(r'(?:\.md)+$', '', path.stem, flags=re.IGNORECASE)
    stem = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', stem)
    return utils.slugify(stem)


def _normalized_host(raw_url: str) -> str:
    host = urlparse(raw_url).netloc.lower()
    if host.startswith('www.'):
        return host[4:]
    return host


def _is_external_href(href: str, site_host: str) -> bool:
    candidate = href.strip()
    if not candidate or candidate.startswith(('#', '/', './', '../')):
        return False

    parsed = urlparse(candidate)
    if parsed.scheme not in {'http', 'https'} and not parsed.netloc:
        return False

    target_host = parsed.netloc.lower()
    if target_host.startswith('www.'):
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
        return '' if not serialized else ' ' + ' '.join(serialized)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.parts.append(self._render_tag(tag, attrs, closing=False))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.parts.append(self._render_tag(tag, attrs, closing=True))

    def _render_tag(self, tag: str, attrs: list[tuple[str, str | None]], closing: bool) -> str:
        updated_attrs = attrs
        if tag == 'a':
            attr_map = dict(attrs)
            href = attr_map.get('href') or ''
            if _is_external_href(href, self.site_host):
                attr_map['target'] = '_blank'
                existing_rel = {item for item in (attr_map.get('rel') or '').split() if item}
                existing_rel.update({'noopener', 'noreferrer'})
                attr_map['rel'] = ' '.join(sorted(existing_rel))

                updated_attrs = []
                seen: set[str] = set()
                for key, value in attrs:
                    if key in {'target', 'rel'}:
                        if key in seen:
                            continue
                        seen.add(key)
                    updated_attrs.append((key, attr_map[key]))

                if 'target' not in seen:
                    updated_attrs.append(('target', attr_map['target']))
                if 'rel' not in seen:
                    updated_attrs.append(('rel', attr_map['rel']))

        suffix = ' /' if closing else ''
        return f'<{tag}{self._serialize_attrs(updated_attrs)}{suffix}>'

    def handle_endtag(self, tag: str) -> None:
        self.parts.append(f'</{tag}>')

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_entityref(self, name: str) -> None:
        self.parts.append(f'&{name};')

    def handle_charref(self, name: str) -> None:
        self.parts.append(f'&#{name};')

    def handle_comment(self, data: str) -> None:
        self.parts.append(f'<!--{data}-->')

    def handle_decl(self, decl: str) -> None:
        self.parts.append(f'<!{decl}>')

    def handle_pi(self, data: str) -> None:
        self.parts.append(f'<?{data}>')

    def rewritten_html(self) -> str:
        return ''.join(self.parts)


def _rewrite_external_links(html_text: str, site_domain: str) -> str:
    parser = _ExternalLinkHTMLRewriter(_normalized_host(site_domain))
    parser.feed(html_text)
    parser.close()
    return parser.rewritten_html()


def render_markdown(body: str, site_domain: str = '', renderer: markdown.Markdown | None = None) -> str:
    active_renderer = renderer or markdown.Markdown(extensions=['extra', 'sane_lists'])
    active_renderer.reset()
    return _rewrite_external_links(active_renderer.convert(body), site_domain)


def _validate_note_slug(language: str, slug: str) -> None:
    if slug in RESERVED_NOTE_SLUGS[language]:
        raise ValueError(f"The slug '{slug}' is reserved for language '{language}'.")


def load_notes(notes_dir: Path, site_domain: str = '') -> list[dict[str, Any]]:
    renderer = markdown.Markdown(extensions=['extra', 'sane_lists'])
    loaded_notes: list[dict[str, Any]] = []
    seen_routes: dict[tuple[str, str], str] = {}

    for path in sorted(notes_dir.glob('*.md')):
        raw = path.read_text(encoding='utf-8')
        metadata, body = _split_front_matter(raw)

        dt = utils.to_datetime(metadata.get('date'))
        language = normalize_language(metadata.get('lang'))
        slug = utils.slugify(str(metadata.get('slug') or _slug_from_path(path)))
        _validate_note_slug(language, slug)

        route_key = (language, slug)
        if route_key in seen_routes:
            raise ValueError(f'Duplicate localized slug for {language}: {slug}')
        seen_routes[route_key] = path.name

        title = str(metadata.get('title') or slug.replace('-', ' ').title())
        raw_tags = metadata.get('tags', [])
        if not isinstance(raw_tags, list):
            raw_tags = []
        tags = [str(tag) for tag in raw_tags]

        rendered_html = render_markdown(body, site_domain, renderer)
        excerpt_html = utils.excerpt_html_from_rendered_html(rendered_html)
        summary = str(metadata.get('summary', '')).strip()
        note_id = note_id_from_metadata(metadata, path)

        loaded_notes.append(
            {
                'filename': path.name,
                'note_id': note_id,
                'language': language,
                'title': title,
                'slug': slug,
                'date': dt,
                'date_iso': dt.isoformat(),
                'date_label': utils.format_date(dt),
                'date_label_en': utils.format_date_en(dt),
                'tags': tags,
                'summary': summary,
                'excerpt': utils.excerpt_from_markdown(body),
                'excerpt_html': excerpt_html,
                'body': body,
                'html': rendered_html,
                'path': note_path(language, slug),
                'notes_index_path': section_path(language, 'notes_index_path'),
                'legacy_path': f"/notes/{slug}/" if language == 'es' else '',
                'translation': None,
                'original': None,
            }
        )

    loaded_notes.sort(key=lambda note: (note['date'], note['filename']), reverse=True)

    notes_by_id: dict[str, dict[str, dict[str, Any]]] = {}
    for note in loaded_notes:
        translations = notes_by_id.setdefault(note['note_id'], {})
        if note['language'] in translations:
            raise ValueError(f"Duplicate translation for note_id={note['note_id']} lang={note['language']}")
        translations[note['language']] = note

    for note in loaded_notes:
        translations = notes_by_id[note['note_id']]
        other_language = 'en' if note['language'] == 'es' else 'es'
        paired = translations.get(other_language)
        if paired is not None:
            note['translation'] = {
                'language': paired['language'],
                'title': paired['title'],
                'path': paired['path'],
                'label': language_settings(paired['language'])['name'],
            }
        if note['language'] == 'en':
            original = translations.get('es')
            if original is not None:
                note['original'] = {
                    'language': 'es',
                    'title': original['title'],
                    'path': original['path'],
                }

    return loaded_notes


def _site_url(domain: str, path: str) -> str:
    return domain.rstrip('/') + path


def build_rss(
    notes: list[dict[str, Any]],
    site: dict[str, Any],
    *,
    feed_title: str,
    feed_description: str,
) -> str:
    site_domain = site['domain']

    items: list[str] = []
    for note in notes[:30]:
        note_url = _site_url(site_domain, note['path'])
        items.append(
            '\n'.join(
                [
                    '<item>',
                    f"<title>{html.escape(note['title'])}</title>",
                    f"<link>{html.escape(note_url)}</link>",
                    f"<guid>{html.escape(note_url)}</guid>",
                    f"<pubDate>{format_datetime(note['date'])}</pubDate>",
                    f"<description>{html.escape(note['summary'] or note['excerpt'])}</description>",
                    '</item>',
                ]
            )
        )

    return '\n'.join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<rss version="2.0">',
            '<channel>',
            f"<title>{html.escape(feed_title)}</title>",
            f"<link>{html.escape(site_domain)}</link>",
            f"<description>{html.escape(feed_description)}</description>",
            *items,
            '</channel>',
            '</rss>',
        ]
    )


def build_atom(
    notes: list[dict[str, Any]],
    site: dict[str, Any],
    built_at: datetime,
    *,
    feed_path: str,
    feed_title: str,
    feed_description: str,
) -> str:
    site_domain = site['domain']
    feed_url = _site_url(site_domain, feed_path)

    entries: list[str] = []
    for note in notes[:30]:
        note_url = _site_url(site_domain, note['path'])
        entries.append(
            '\n'.join(
                [
                    '<entry>',
                    f"<title>{html.escape(note['title'])}</title>",
                    f"<id>{html.escape(note_url)}</id>",
                    f'<link href="{html.escape(note_url)}" />',
                    f"<updated>{note['date'].isoformat()}</updated>",
                    f"<summary>{html.escape(note['summary'] or note['excerpt'])}</summary>",
                    '</entry>',
                ]
            )
        )

    return '\n'.join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<feed xmlns="http://www.w3.org/2005/Atom">',
            f"<title>{html.escape(feed_title)}</title>",
            f"<subtitle>{html.escape(feed_description)}</subtitle>",
            f"<id>{html.escape(feed_url)}</id>",
            f'<link href="{html.escape(feed_url)}" rel="self" />',
            f"<updated>{built_at.isoformat()}</updated>",
            *entries,
            '</feed>',
        ]
    )


def build_json_feed(
    notes: list[dict[str, Any]],
    site: dict[str, Any],
    *,
    feed_path: str,
    feed_title: str,
    feed_description: str,
) -> str:
    payload = {
        'version': 'https://jsonfeed.org/version/1.1',
        'title': feed_title,
        'home_page_url': site['domain'],
        'feed_url': _site_url(site['domain'], feed_path),
        'description': feed_description,
        'items': [
            {
                'id': _site_url(site['domain'], note['path']),
                'url': _site_url(site['domain'], note['path']),
                'title': note['title'],
                'content_html': note['html'],
                'summary': note['summary'] or note['excerpt'],
                'date_published': note['date_iso'],
                'tags': note['tags'],
            }
            for note in notes[:30]
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
