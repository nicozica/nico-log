#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape

try:
    from .lib import feeds, notes, now_playing, status, utils, weather
except ImportError:  # pragma: no cover - script entrypoint fallback
    from lib import feeds, notes, now_playing, status, utils, weather

UI_STRINGS: dict[str, dict[str, Any]] = {
    'es': {
        'code': 'es',
        'language_name': 'Español',
        'skip_link': 'Saltar al contenido',
        'theme_toggle_label': 'Terminal',
        'theme_toggle_aria': 'Cambiar a modo terminal',
        'nav': {
            'home_label': 'Inicio',
            'home_path': '/es/',
            'notes_label': 'Notas',
            'notes_path': '/es/notas/',
            'news_label': 'Noticias',
            'news_path': '/es/noticias/',
            'about_label': 'Acerca',
            'about_path': '/es/acerca/',
        },
        'status': {
            'updated': 'Actualizado',
            'uptime': 'Uptime',
            'cpu_temp': 'Temp CPU',
        },
        'footer': {
            'webring': 'Webring',
            'colophon': 'estático, cacheado, regenerado cada {minutes} min',
        },
        'home': {
            'page_title': 'Inicio',
            'latest_notes_title': 'Últimas notas',
            'latest_notes_subtitle': '',
            'main_label': 'Panel principal',
            'sidebar_label': 'Columna lateral',
            'read_link': 'leer',
            'more_notes': 'Ver más notas',
            'weather_title': 'Clima',
            'weather_condition_sr': 'Condición del clima:',
            'forecast_label': 'Pronóstico breve',
            'now_title': 'Ahora sonando',
            'track_label': 'Tema:',
            'artist_label': 'Artista:',
            'album_label': 'Álbum:',
            'year_label': 'Año:',
            'unavailable': 'No disponible',
            'open_stream': 'Abrir en Blur FM ↗',
            'news_title': 'Noticias',
            'news_more': 'Ver todas',
            'tiny_title': 'Mini del día',
            'empty_notes': 'Todavía no hay notas publicadas en esta versión.',
        },
        'notes': {
            'page_title': 'Notas',
            'intro': 'Bitácora editorial, ordenada de más nueva a más antigua.',
            'newer': 'Más nuevas',
            'older': 'Más antiguas',
            'empty': 'Todavía no hay notas publicadas en esta versión.',
        },
        'note': {
            'translation_link': 'English version →',
            'original_notice': '',
            'original_link': '',
            'back': '← Volver a notas',
        },
        'news': {
            'page_title': 'Noticias',
            'intro': 'Entradas frescas combinadas desde la lista RSS configurada.',
            'description': 'Noticias y enlaces recientes curados desde feeds externos.',
        },
        'about': {
            'page_title': 'Acerca',
            'description': 'Cómo está armado este sitio low-tech y por qué sigue siendo deliberadamente simple.',
            'hero': 'Un proyecto low tech: hosteado en una microSD, con Alpine Linux 64 bit y apenas 512 MB de RAM.',
            'lead': 'Este sitio vive en una máquina mínima, con una idea simple: publicar contenido propio con mínimos recursos, sin abrir puertos innecesarios y sin complejizar lo que debería ser liviano.',
            'scene_one_title': 'Todo empieza en una placa diminuta',
            'scene_one_body': 'Lo que ves acá no corre en infraestructura gigante: corre en una',
            'scene_one_link_title': 'Especificaciones de Raspberry Pi Zero 2 W',
            'scene_one_body_suffix': 'una microcomputadora que sirve archivos estáticos con NGINX. Es una decisión técnica, pero también editorial: menos capas y más control.',
            'runtime_label': 'Runtime actual:',
            'scene_two_title': 'Cómo sale a Internet sin exponerse de más',
            'scene_two_body': 'El servidor no se publica abriendo puertos de entrada. En cambio, mantiene una conexión saliente mediante túnel seguro y responde a través de HTTPS. El objetivo es claro: superficie chica de ataque y operación predecible.',
            'bullet_one': 'Contenido estático generado con Python.',
            'bullet_two': 'Cache local para tolerar fallos de servicios externos.',
            'bullet_three': 'Operación continua en un nodo doméstico, sin doxear detalles sensibles.',
            'photo_one_alt': 'Raspberry Pi Zero 2 W en primer plano',
            'photo_one_caption': 'Raspberry Pi Zero 2 W, una microcomputadora que cabe en el bolsillo.',
            'photo_two_alt': 'Raspberry Pi Zero 2 W montada en su gabinete',
            'photo_two_caption': 'La microcomputadora en su gabinete, lista para quedar encendida 24/7.',
        },
        'feeds': {
            'rss_label': 'RSS',
            'atom_label': 'Atom',
            'json_label': 'Feed JSON',
            'title': 'nico://log · notas en español',
            'description': 'Notas en español de nico://log.',
        },
    },
    'en': {
        'code': 'en',
        'language_name': 'English',
        'skip_link': 'Skip to content',
        'theme_toggle_label': 'Terminal',
        'theme_toggle_aria': 'Switch to terminal mode',
        'nav': {
            'home_label': 'Home',
            'home_path': '/en/',
            'notes_label': 'Notes',
            'notes_path': '/en/notes/',
            'news_label': 'News',
            'news_path': '/en/news/',
            'about_label': 'About',
            'about_path': '/en/about/',
        },
        'status': {
            'updated': 'Updated',
            'uptime': 'Uptime',
            'cpu_temp': 'CPU temp',
        },
        'footer': {
            'webring': 'Webring',
            'colophon': 'static, cached, rebuilt every {minutes} min',
        },
        'home': {
            'page_title': 'Home',
            'latest_notes_title': 'Latest notes',
            'latest_notes_subtitle': 'Current English coverage is intentionally partial during the migration.',
            'main_label': 'Main panel',
            'sidebar_label': 'Sidebar',
            'read_link': 'read',
            'more_notes': 'More notes',
            'weather_title': 'Weather',
            'weather_condition_sr': 'Weather condition:',
            'forecast_label': 'Short forecast',
            'now_title': 'Now playing',
            'track_label': 'Track:',
            'artist_label': 'Artist:',
            'album_label': 'Album:',
            'year_label': 'Year:',
            'unavailable': 'Unavailable',
            'open_stream': 'Open on Blur FM ↗',
            'news_title': 'News',
            'news_more': 'See all',
            'tiny_title': 'Tiny thing of the day',
            'empty_notes': 'No English notes have been published yet.',
        },
        'notes': {
            'page_title': 'Notes',
            'intro': 'Notes and experiments, ordered from newest to oldest.',
            'newer': 'Newer',
            'older': 'Older',
            'empty': 'No English notes have been published yet.',
        },
        'note': {
            'translation_link': 'Versión en español →',
            'original_notice': 'Originally written in Spanish.',
            'original_link': 'Read the original →',
            'back': '← Back to notes',
        },
        'news': {
            'page_title': 'News',
            'intro': 'Fresh links blended from the configured RSS list.',
            'description': 'External news and links collected from the configured feeds.',
        },
        'about': {
            'page_title': 'About',
            'description': 'A brief English placeholder for the low-tech setup behind the site.',
            'hero': 'A low-tech personal site running on tiny hardware.',
            'translation_pending': 'This page is still being translated. For now, the Spanish version remains the canonical editorial reference.',
            'original_link': 'Read the Spanish original',
        },
        'feeds': {
            'rss_label': 'RSS',
            'atom_label': 'Atom',
            'json_label': 'JSON Feed',
            'title': 'nico://log · notes in English',
            'description': 'English notes and translations from nico://log.',
        },
    },
}

GATEWAY_COPY = {
    'page_title': 'Idioma / Language',
    'description': 'Choose the Spanish or English version of the site. Automatic root language negotiation is intentionally deferred in this milestone.',
    'title': 'Elegí idioma / Choose a language',
    'body': 'This bilingual migration now has stable language-prefixed URLs. Root-language negotiation is intentionally deferred until deployment policy is reviewed.',
    'es_label': 'Entrar en español',
    'en_label': 'Enter in English',
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Build static portal output')
    parser.add_argument('--output-dir', default='', help='Output directory for static site')
    parser.add_argument('--cache-dir', default='', help='Cache directory for dynamic data')
    parser.add_argument('--content-dir', default='', help='Content directory')
    parser.add_argument('--templates-dir', default='', help='Templates directory')
    parser.add_argument('--static-dir', default='', help='Static assets directory')
    return parser.parse_args()


def render_template(env: Environment, template_name: str, destination: Path, context: dict[str, Any]) -> None:
    utils.ensure_dir(destination.parent)
    html = env.get_template(template_name).render(**context)
    destination.write_text(html, encoding='utf-8')


def route_destination(output_dir: Path, route_path: str) -> Path:
    trimmed = route_path.strip('/')
    if not trimmed:
        return output_dir / 'index.html'
    return output_dir.joinpath(*trimmed.split('/')) / 'index.html'


def _to_positive_int(raw_value: Any, default: int) -> int:
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return default
    if value <= 0:
        return default
    return value


def _localized_site(site: dict[str, Any], language: str) -> dict[str, Any]:
    localized = dict(site)
    if language == 'en':
        localized['tagline'] = str(site.get('tagline_en') or site.get('tagline') or '').strip()
        localized['description'] = str(site.get('description_en') or site.get('description') or '').strip()
    return localized


def _page_context(
    base_context: dict[str, Any],
    *,
    site: dict[str, Any],
    locale: dict[str, Any],
    page_title: str,
    page_description: str,
    current_path: str,
    canonical_path: str,
    alternate_languages: list[dict[str, str]],
    x_default_path: str = '',
    feed_links: list[dict[str, str]] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context = {
        **base_context,
        'site': site,
        'locale': locale,
        'html_lang': locale['code'],
        'page_title': page_title,
        'page_description': page_description,
        'current_path': current_path,
        'canonical_path': canonical_path,
        'alternate_languages': alternate_languages,
        'x_default_path': x_default_path,
        'feed_links': feed_links or [],
    }
    if extra:
        context.update(extra)
    return context


def _localized_feed_links(language: str, locale: dict[str, Any]) -> list[dict[str, str]]:
    paths = notes.feed_paths(language)
    return [
        {
            'href': paths['rss'],
            'type': 'application/rss+xml',
            'label': locale['feeds']['rss_label'],
            'title': locale['feeds']['title'],
        },
        {
            'href': paths['atom'],
            'type': 'application/atom+xml',
            'label': locale['feeds']['atom_label'],
            'title': locale['feeds']['title'],
        },
        {
            'href': paths['json'],
            'type': 'application/feed+json',
            'label': locale['feeds']['json_label'],
            'title': locale['feeds']['title'],
        },
    ]


def _note_alternates(note: dict[str, Any]) -> list[dict[str, str]]:
    alternates = [{'hreflang': note['language'], 'href': note['path']}]
    if note.get('translation'):
        alternates.append(
            {
                'hreflang': note['translation']['language'],
                'href': note['translation']['path'],
            }
        )
    return alternates


def _paired_section_alternates(es_path: str, en_path: str) -> list[dict[str, str]]:
    return [
        {'hreflang': 'es', 'href': es_path},
        {'hreflang': 'en', 'href': en_path},
    ]


def _write_feed_triplet(
    output_dir: Path,
    feed_paths: dict[str, str],
    language_notes: list[dict[str, Any]],
    site: dict[str, Any],
    built_at: datetime,
    locale: dict[str, Any],
) -> None:
    rss_destination = output_dir.joinpath(*feed_paths['rss'].strip('/').split('/'))
    atom_destination = output_dir.joinpath(*feed_paths['atom'].strip('/').split('/'))
    json_destination = output_dir.joinpath(*feed_paths['json'].strip('/').split('/'))

    utils.ensure_dir(rss_destination.parent)
    utils.ensure_dir(atom_destination.parent)
    utils.ensure_dir(json_destination.parent)

    rss_destination.write_text(
        notes.build_rss(
            language_notes,
            site,
            feed_title=locale['feeds']['title'],
            feed_description=locale['feeds']['description'],
        ),
        encoding='utf-8',
    )
    atom_destination.write_text(
        notes.build_atom(
            language_notes,
            site,
            built_at,
            feed_path=feed_paths['atom'],
            feed_title=locale['feeds']['title'],
            feed_description=locale['feeds']['description'],
        ),
        encoding='utf-8',
    )
    json_destination.write_text(
        notes.build_json_feed(
            language_notes,
            site,
            feed_path=feed_paths['json'],
            feed_title=locale['feeds']['title'],
            feed_description=locale['feeds']['description'],
        ),
        encoding='utf-8',
    )


def main() -> None:
    args = parse_args()

    project_root = Path(__file__).resolve().parents[1]
    content_dir = Path(args.content_dir) if args.content_dir else project_root / 'content'
    templates_dir = Path(args.templates_dir) if args.templates_dir else project_root / 'templates'
    static_dir = Path(args.static_dir) if args.static_dir else project_root / 'static'
    output_dir = Path(args.output_dir) if args.output_dir else project_root / 'dist'
    cache_dir = Path(args.cache_dir) if args.cache_dir else project_root / 'cache'

    utils.ensure_dir(cache_dir)
    utils.clean_output_dir(output_dir)

    config = utils.load_yaml(content_dir / 'config.yaml', default={})
    site = config.get('site', {})
    about = config.get('about', {})
    status_bar = config.get('status_bar', {})
    footer = config.get('footer', {})
    now_playing_settings = config.get('now_playing', {})
    home_settings = config.get('home', {})
    notes_settings = config.get('notes', {})
    news_settings = config.get('news', {})
    tiny_lines = utils.load_lines(content_dir / 'tiny.txt')

    if not isinstance(site, dict):
        site = {}
    if not isinstance(about, dict):
        about = {}
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
    if not isinstance(news_settings, dict):
        news_settings = {}

    site_power = str(site.get('power', '')).strip()
    if not site_power:
        site_power = str(status_bar.get('power_label', 'grid')).strip() or 'grid'
    site = {**site, 'power': site_power}

    status_bar = {'power_label': site_power}
    footer_links = footer.get('links', [])
    if not isinstance(footer_links, list):
        footer_links = []

    normalized_footer_links: list[dict[str, str]] = []
    for item in footer_links:
        if not isinstance(item, dict):
            continue
        label = str(item.get('label', '')).strip()
        href = str(item.get('href', '')).strip()
        if label and href:
            normalized_footer_links.append({'label': label, 'href': href})
    footer = {'links': normalized_footer_links}

    all_notes = notes.load_notes(content_dir / 'notes', site_domain=str(site.get('domain', '')))
    notes_by_language = {
        language: [note for note in all_notes if note['language'] == language]
        for language in notes.LANGUAGE_SETTINGS
    }

    all_links, links_source = feeds.fetch_links(
        content_path=content_dir / 'feeds.yaml',
        cache_dir=cache_dir,
        ttl_minutes=int(config.get('feeds_ttl_minutes', 30)),
        limit=120,
        fresh_days=_to_positive_int(news_settings.get('fresh_days', 14), default=14),
    )
    links_preview = feeds.select_preview_links(all_links, limit=6)
    weather_data, weather_source = weather.fetch_weather(config, cache_dir)
    status_bundle, _ = status.fetch_status(config, cache_dir)
    now_data, now_history, now_source = now_playing.fetch_now(config, cache_dir, content_dir)

    built_at = datetime.now().astimezone()
    build_id = built_at.strftime('%Y%m%d%H%M%S')
    build_info = {
        'updated_iso': built_at.isoformat(),
        'updated_label': utils.format_datetime(built_at),
    }
    now_source_url = str(now_playing_settings.get('source_url', '')).strip()
    now_stream_url = str(now_playing_settings.get('stream_url', '')).strip() or 'https://www.blurfm.com/'
    now_player_stream_url = (
        str(now_playing_settings.get('player_stream_url', '')).strip() or 'https://stream.blurfm.com/high'
    )
    now_api_url = now_source_url
    parsed_now_url = urlparse(now_source_url)
    if parsed_now_url.scheme and parsed_now_url.netloc:
        host = parsed_now_url.netloc.lower()
        if host in {'nico.com.ar', 'www.nico.com.ar'}:
            now_api_url = parsed_now_url.path or '/api/now-playing'
            if parsed_now_url.query:
                now_api_url = f"{now_api_url}?{parsed_now_url.query}"
    now_refresh_enabled = now_api_url.startswith('/')
    now_data = {**now_data, 'refresh_enabled': now_refresh_enabled}

    notes_page_size = _to_positive_int(notes_settings.get('page_size', 10), default=10)
    status_summary = status_bundle.get('summary', {})
    tiny_thing = utils.pick_tiny_thing(tiny_lines, built_at)

    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(['html', 'xml']),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    base_context = {
        'about': about,
        'status_bar': status_bar,
        'footer': footer,
        'build': build_info,
        'status_summary': status_summary,
        'status': status_bundle.get('status', {}),
        'weather': weather_data,
        'now': now_data,
        'data_sources': {
            'links': links_source,
            'weather': weather_source,
            'now': now_source,
            'status': status_bundle.get('status', {}).get('source', 'unknown'),
        },
        'build_id': build_id,
        'now_api_url': now_api_url,
        'now_stream_url': now_stream_url,
        'now_player_stream_url': now_player_stream_url,
    }

    render_template(
        env,
        'language_gateway.html',
        output_dir / 'index.html',
        {
            **base_context,
            'site': site,
            'page_title': GATEWAY_COPY['page_title'],
            'page_description': GATEWAY_COPY['description'],
            'gateway': GATEWAY_COPY,
            'alternate_languages': _paired_section_alternates('/es/', '/en/'),
        },
    )

    render_template(
        env,
        '404.html',
        output_dir / '404.html',
        _page_context(
            base_context,
            site=_localized_site(site, 'es'),
            locale=UI_STRINGS['es'],
            page_title='404',
            page_description=GATEWAY_COPY['description'],
            current_path='',
            canonical_path='/404.html',
            alternate_languages=[],
            x_default_path='/',
            feed_links=_localized_feed_links('es', UI_STRINGS['es']),
        ),
    )

    for language, locale in UI_STRINGS.items():
        localized_site = _localized_site(site, language)
        localized_notes = notes_by_language[language]
        localized_feed_links = _localized_feed_links(language, locale)
        latest_notes_limit = _to_positive_int(home_settings.get('latest_notes_limit', 4), default=4)
        latest_notes = localized_notes[:latest_notes_limit]

        render_template(
            env,
            'index.html',
            route_destination(output_dir, locale['nav']['home_path']),
            _page_context(
                base_context,
                site=localized_site,
                locale=locale,
                page_title=locale['home']['page_title'],
                page_description=localized_site.get('description', ''),
                current_path=locale['nav']['home_path'],
                canonical_path=locale['nav']['home_path'],
                alternate_languages=_paired_section_alternates('/es/', '/en/'),
                x_default_path='/',
                feed_links=localized_feed_links,
                extra={
                    'latest_notes': latest_notes,
                    'total_notes_count': len(localized_notes),
                    'links_preview': links_preview,
                    'latest_notes_title': home_settings.get('latest_notes_title', locale['home']['latest_notes_title'])
                    if language == 'es'
                    else locale['home']['latest_notes_title'],
                    'latest_notes_subtitle': home_settings.get('latest_notes_subtitle', locale['home']['latest_notes_subtitle'])
                    if language == 'es'
                    else locale['home']['latest_notes_subtitle'],
                    'tiny_thing': tiny_thing,
                },
            ),
        )

        total_notes = len(localized_notes)
        total_pages = max(1, (total_notes + notes_page_size - 1) // notes_page_size)
        other_language = 'en' if language == 'es' else 'es'
        other_notes_total = len(notes_by_language[other_language])
        other_total_pages = max(1, (other_notes_total + notes_page_size - 1) // notes_page_size)

        for page in range(1, total_pages + 1):
            start = (page - 1) * notes_page_size
            end = start + notes_page_size
            page_notes = localized_notes[start:end]

            if page == 1:
                current_path = locale['nav']['notes_path']
            else:
                current_path = f"{locale['nav']['notes_path']}page/{page}/"

            if page == 1:
                prev_url = ''
            elif page == 2:
                prev_url = locale['nav']['notes_path']
            else:
                prev_url = f"{locale['nav']['notes_path']}page/{page - 1}/"
            next_url = f"{locale['nav']['notes_path']}page/{page + 1}/" if page < total_pages else ''

            pagination = {
                'page': page,
                'total_pages': total_pages,
                'has_prev': page > 1,
                'has_next': page < total_pages,
                'prev_url': prev_url,
                'next_url': next_url,
                'label': f"Page {page} of {total_pages}" if language == 'en' else f"Página {page} de {total_pages}",
            }

            alternates = [{'hreflang': language, 'href': current_path}]
            if page <= other_total_pages:
                counterpart = UI_STRINGS[other_language]['nav']['notes_path']
                if page > 1:
                    counterpart = f"{counterpart}page/{page}/"
                alternates.append({'hreflang': other_language, 'href': counterpart})

            render_template(
                env,
                'notes_index.html',
                route_destination(output_dir, current_path),
                _page_context(
                    base_context,
                    site=localized_site,
                    locale=locale,
                    page_title=locale['notes']['page_title'],
                    page_description=localized_site.get('description', ''),
                    current_path=current_path,
                    canonical_path=current_path,
                    alternate_languages=alternates,
                    feed_links=localized_feed_links,
                    extra={
                        'notes': page_notes,
                        'notes_total': total_notes,
                        'notes_total_label': f"{total_notes} published notes." if language == 'en' else f"{total_notes} notas publicadas.",
                        'pagination': pagination,
                    },
                ),
            )

        for note in localized_notes:
            note_description = note['summary'] or note['excerpt'] or localized_site.get('description', '')
            render_template(
                env,
                'note_detail.html',
                route_destination(output_dir, note['path']),
                _page_context(
                    base_context,
                    site=localized_site,
                    locale=locale,
                    page_title=note['title'],
                    page_description=note_description,
                    current_path=note['path'],
                    canonical_path=note['path'],
                    alternate_languages=_note_alternates(note),
                    feed_links=localized_feed_links,
                    extra={'note': note},
                ),
            )

        render_template(
            env,
            'links_index.html',
            route_destination(output_dir, locale['nav']['news_path']),
            _page_context(
                base_context,
                site=localized_site,
                locale=locale,
                page_title=locale['news']['page_title'],
                page_description=locale['news']['description'],
                current_path=locale['nav']['news_path'],
                canonical_path=locale['nav']['news_path'],
                alternate_languages=_paired_section_alternates('/es/noticias/', '/en/news/'),
                feed_links=localized_feed_links,
                extra={'links': all_links},
            ),
        )

        render_template(
            env,
            'about_index.html',
            route_destination(output_dir, locale['nav']['about_path']),
            _page_context(
                base_context,
                site=localized_site,
                locale=locale,
                page_title=locale['about']['page_title'],
                page_description=locale['about']['description'],
                current_path=locale['nav']['about_path'],
                canonical_path=locale['nav']['about_path'],
                alternate_languages=_paired_section_alternates('/es/acerca/', '/en/about/'),
                feed_links=localized_feed_links,
            ),
        )

        _write_feed_triplet(output_dir, notes.feed_paths(language), localized_notes, site, built_at, locale)

    render_template(
        env,
        'now_index.html',
        output_dir / 'now' / 'index.html',
        _page_context(
            base_context,
            site=_localized_site(site, 'es'),
            locale=UI_STRINGS['es'],
            page_title='Ahora sonando',
            page_description='Tema actual en vivo desde Blur FM.',
            current_path='/now/',
            canonical_path='/now/',
            alternate_languages=[],
            feed_links=_localized_feed_links('es', UI_STRINGS['es']),
            extra={'history': now_history},
        ),
    )

    spanish_locale = UI_STRINGS['es']
    spanish_site = _localized_site(site, 'es')

    render_template(
        env,
        'redirect.html',
        route_destination(output_dir, '/notes/'),
        {
            **base_context,
            'site': spanish_site,
            'page_title': 'Notas',
            'redirect_url': '/es/notas/',
            'html_lang': 'es',
        },
    )

    spanish_pages = max(1, (len(notes_by_language['es']) + notes_page_size - 1) // notes_page_size)
    for page in range(2, spanish_pages + 1):
        render_template(
            env,
            'redirect.html',
            route_destination(output_dir, f'/notes/page/{page}/'),
            {
                **base_context,
                'site': spanish_site,
                'page_title': 'Notas',
                'redirect_url': f'/es/notas/page/{page}/',
                'html_lang': 'es',
            },
        )

    for note in notes_by_language['es']:
        render_template(
            env,
            'redirect.html',
            route_destination(output_dir, note['legacy_path']),
            {
                **base_context,
                'site': spanish_site,
                'page_title': note['title'],
                'redirect_url': note['path'],
                'html_lang': 'es',
            },
        )

    for legacy_path, target_path, title in [
        ('/links/', '/es/noticias/', 'Noticias'),
        ('/noticias/', '/es/noticias/', 'Noticias'),
        ('/about/', '/es/acerca/', 'Acerca'),
    ]:
        render_template(
            env,
            'redirect.html',
            route_destination(output_dir, legacy_path),
            {
                **base_context,
                'site': spanish_site,
                'page_title': title,
                'redirect_url': target_path,
                'html_lang': 'es',
            },
        )

    legacy_feed_paths = {
        'rss': '/notes/rss.xml',
        'atom': '/notes/atom.xml',
        'json': '/notes/feed.json',
    }
    _write_feed_triplet(output_dir, legacy_feed_paths, notes_by_language['es'], site, built_at, spanish_locale)

    utils.copy_static_tree(static_dir, output_dir / 'assets')

    favicon_svg_source = static_dir / 'favicon.svg'
    if favicon_svg_source.exists():
        favicon_svg = favicon_svg_source.read_text(encoding='utf-8')
        (output_dir / 'favicon.svg').write_text(favicon_svg, encoding='utf-8')
        (output_dir / 'favicon-v2.svg').write_text(favicon_svg, encoding='utf-8')

    favicon_ico_source = static_dir / 'favicon.ico'
    if favicon_ico_source.exists():
        (output_dir / 'favicon.ico').write_bytes(favicon_ico_source.read_bytes())


if __name__ == '__main__':
    main()
