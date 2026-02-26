from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from . import utils

LOG_PREFIX = "[now-playing]"


def _log(message: str) -> None:
    print(f"{LOG_PREFIX} {message}")


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _unavailable_now() -> dict[str, Any]:
    return {
        "track": "No disponible",
        "artist": "",
        "url": "",
        "started_at": "",
        "started_label": "",
        "available": False,
        "live": False,
    }


def _normalize_now(item: dict[str, Any], *, live: bool) -> dict[str, Any]:
    started_raw = item.get("started_at")
    started_label = ""
    started_at = ""

    if started_raw:
        parsed_started = utils.to_datetime(started_raw)
        started_at = parsed_started.isoformat()
        started_label = parsed_started.strftime("%Y-%m-%d %H:%M")

    return {
        "track": str(item.get("track", "No disponible")),
        "artist": str(item.get("artist", "")).strip(),
        "url": str(item.get("url", "")).strip(),
        "started_at": started_at,
        "started_label": started_label,
        "available": True,
        "live": live,
    }


def _normalize_history(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in history[:30]:
        played_at_raw = item.get("played_at")
        played_label = ""
        played_at = ""
        if played_at_raw:
            parsed_played = utils.to_datetime(played_at_raw)
            played_at = parsed_played.isoformat()
            played_label = parsed_played.strftime("%Y-%m-%d %H:%M")

        rows.append(
            {
                "track": str(item.get("track", "Desconocido")),
                "artist": str(item.get("artist", "Desconocido")),
                "url": str(item.get("url", "")),
                "played_at": played_at,
                "played_label": played_label,
            }
        )
    return rows


def _fetch_json_with_diagnostics(url: str, timeout_sec: float) -> dict[str, Any]:
    _log(f"request_url={url}")
    response = requests.get(url, timeout=timeout_sec)
    _log(f"status_code={response.status_code}")
    response.raise_for_status()
    try:
        payload = response.json()
        _log("json_parse=true")
        return payload
    except ValueError:
        _log("json_parse=false")
        raise


def _resolve_source_url(config: dict[str, Any], source_url: str) -> str:
    if not source_url.startswith("/"):
        return source_url

    site = config.get("site", {})
    if not isinstance(site, dict):
        site = {}
    domain = str(site.get("domain", "")).strip().rstrip("/")
    if not domain:
        return ""
    return f"{domain}{source_url}"


def _read_local_json(path: Path, default: Any) -> Any:
    data = utils.read_json(path, None)
    if data is None:
        return default
    return data


def _normalize_mount(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    if parsed.scheme and parsed.netloc:
        raw = parsed.path
    if not raw.startswith("/"):
        raw = f"/{raw}"
    normalized = raw.rstrip("/")
    return normalized or "/"


def _split_title(value: str) -> tuple[str, str]:
    cleaned = value.strip()
    for separator in (" - ", " – ", " — "):
        if separator in cleaned:
            artist, track = cleaned.split(separator, 1)
            return artist.strip(), track.strip()
    return "", cleaned


def _extract_now_payload(record: dict[str, Any], default_url: str = "") -> dict[str, Any]:
    title = _clean_text(record.get("title"))
    track = _clean_text(record.get("track") or record.get("song"))
    artist = _clean_text(record.get("artist") or record.get("server_name") or record.get("dj"))

    if title and (not track or not artist):
        parsed_artist, parsed_track = _split_title(title)
        if not artist and parsed_artist:
            artist = parsed_artist
        if not track:
            track = parsed_track or title

    track = track or title
    artist = artist or "Desconocido"
    stream_url = _clean_text(
        record.get("url")
        or record.get("listenurl")
        or record.get("server_url")
        or default_url
        or ""
    )

    started_at = (
        record.get("started_at")
        or record.get("stream_start")
        or record.get("started")
        or record.get("timestamp")
        or ""
    )

    return {
        "track": track,
        "artist": artist,
        "url": stream_url,
        "started_at": started_at,
    }


def _extract_history_payload(record: dict[str, Any], default_url: str = "") -> dict[str, Any]:
    now_payload = _extract_now_payload(record, default_url=default_url)
    played_at = (
        record.get("played_at")
        or record.get("started_at")
        or record.get("stream_start")
        or record.get("timestamp")
        or ""
    )
    return {
        "track": now_payload["track"],
        "artist": now_payload["artist"],
        "url": now_payload["url"],
        "played_at": played_at,
    }


def _extract_sources(payload: dict[str, Any]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for key in ("sources", "mounts"):
        value = payload.get(key)
        if isinstance(value, list):
            sources.extend(item for item in value if isinstance(item, dict))

    icestats = payload.get("icestats")
    if isinstance(icestats, dict):
        source_value = icestats.get("source")
        if isinstance(source_value, dict):
            sources.append(source_value)
        elif isinstance(source_value, list):
            sources.extend(item for item in source_value if isinstance(item, dict))
    return sources


def _matches_mount(source: dict[str, Any], mount: str) -> bool:
    target_mount = _normalize_mount(mount)
    if not target_mount:
        return True

    candidates = [
        source.get("mount"),
        source.get("listenurl"),
        source.get("server_url"),
        source.get("url"),
    ]
    for candidate in candidates:
        if _normalize_mount(candidate) == target_mount:
            return True
    return False


def _select_source(sources: list[dict[str, Any]], mount: str) -> dict[str, Any] | None:
    for source in sources:
        if _matches_mount(source, mount):
            return source
    return sources[0] if sources else None


def _parse_source_payload(
    payload: dict[str, Any],
    mount: str,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if not isinstance(payload, dict):
        return None, []

    if payload.get("success") is False:
        return None, []

    default_url = str(payload.get("url") or payload.get("listenurl") or "").strip()
    now_payload: dict[str, Any] | None = None

    raw_now = payload.get("now")
    if isinstance(raw_now, dict):
        now_payload = _extract_now_payload(raw_now, default_url=default_url)
    elif any(_clean_text(payload.get(key)) for key in ("track", "artist", "song", "title")):
        now_payload = _extract_now_payload(payload, default_url=default_url)

    selected_source = _select_source(_extract_sources(payload), mount)
    if selected_source:
        now_payload = _extract_now_payload(selected_source, default_url=default_url)

    raw_history = payload.get("history")
    if not isinstance(raw_history, list):
        raw_history = payload.get("now_history")
    if not isinstance(raw_history, list):
        raw_history = []

    history_payload: list[dict[str, Any]] = []
    item_default_url = now_payload["url"] if now_payload else default_url
    for item in raw_history:
        if not isinstance(item, dict):
            continue
        history_payload.append(_extract_history_payload(item, default_url=item_default_url))

    if now_payload is None:
        return None, history_payload

    track_name = _clean_text(now_payload.get("track")).lower()
    if not track_name:
        return None, history_payload
    if track_name in {"silence", "silencio"}:
        return None, history_payload

    return now_payload, history_payload


def _payload_title_for_log(payload: dict[str, Any], mount: str) -> str:
    selected_source = _select_source(_extract_sources(payload), mount)
    if selected_source:
        title = _clean_text(selected_source.get("title") or selected_source.get("track") or selected_source.get("song"))
        if title:
            return title

    return _clean_text(payload.get("title") or payload.get("track") or payload.get("song"))


def _fetch_from_source_endpoint(
    config: dict[str, Any],
    cache_dir: Path,
    _content_dir: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], str] | None:
    settings = config.get("now_playing", {})
    if not isinstance(settings, dict):
        settings = {}

    source_url = str(settings.get("source_url", "")).strip()
    if not source_url:
        return None
    resolved_source_url = _resolve_source_url(config, source_url)
    if not resolved_source_url:
        _log("source_url_unresolved=true")
        return _unavailable_now(), [], "unavailable"

    timeout_sec = float(settings.get("timeout_sec", 3) or 3)
    cache_ttl_sec = int(settings.get("cache_ttl_sec", 60) or 60)
    mount = str(settings.get("mount", "")).strip()
    source_cache_file = cache_dir / "now_source.json"
    cached_payload = utils.read_json(source_cache_file, None)

    payload: dict[str, Any] | None = None
    payload_source = "missing"

    if cached_payload is not None and utils.is_cache_fresh(source_cache_file, max(cache_ttl_sec, 0)):
        payload = cached_payload
        payload_source = "cache"
        _log("using_fresh_cache=true")
    else:
        try:
            fetched_payload = _fetch_json_with_diagnostics(resolved_source_url, timeout_sec=timeout_sec)

            if fetched_payload.get("success") is False:
                _log("payload_success=false")

            payload_title = _payload_title_for_log(fetched_payload, mount=mount)
            if not payload_title:
                _log("payload_title_empty=true")

            fetched_now_payload, _ = _parse_source_payload(fetched_payload, mount=mount)
            if fetched_now_payload is None:
                raise ValueError("Source payload does not include a playable now item")

            utils.write_json(source_cache_file, fetched_payload)
            payload = fetched_payload
            payload_source = "live"
        except Exception as error:
            _log(f"live_fetch_error={error}")
            if cached_payload is not None:
                payload = cached_payload
                payload_source = "stale"
                _log("using_last_known_good_cache=true")
            else:
                _log("no_last_known_good_cache=true")
                return _unavailable_now(), [], "unavailable"

    now_payload, history_payload = _parse_source_payload(payload or {}, mount=mount)
    if now_payload is None:
        _log("playable_now_missing_in_cache=true")
        return _unavailable_now(), [], f"{payload_source}/none"

    live = payload_source == "live"
    normalized_now = _normalize_now(now_payload, live=live)

    if not live:
        return normalized_now, [], f"{payload_source}/disabled"

    normalized_history = _normalize_history(history_payload)
    return normalized_now, normalized_history, f"{payload_source}/live"


def _fetch_legacy_endpoints(
    config: dict[str, Any],
    cache_dir: Path,
    _content_dir: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    ttl_minutes = int(config.get("now_ttl_minutes", 5))
    ttl_seconds = max(ttl_minutes * 60, 0)
    now_cache_file = cache_dir / "now_playing.json"
    history_cache_file = cache_dir / "now_history.json"

    now_url = str(config.get("now_playing_url", "")).strip()
    history_url = str(config.get("now_history_url", "")).strip()

    if now_url:
        now_payload, now_source = utils.fetch_json_with_cache(
            now_cache_file,
            ttl_seconds=ttl_seconds,
            fetcher=lambda: _fetch_json_with_diagnostics(now_url, timeout_sec=6),
            fallback={},
        )
    else:
        now_payload = _read_local_json(now_cache_file, {})
        now_source = "cache-local" if now_cache_file.exists() else "missing"

    if not isinstance(now_payload, dict):
        now_payload = {}

    now_candidate, _ = _parse_source_payload(now_payload, mount="")
    if now_candidate is None:
        return _unavailable_now(), [], f"{now_source}/none"

    live = now_source == "live"
    normalized_now = _normalize_now(now_candidate, live=live)

    if not live:
        return normalized_now, [], f"{now_source}/disabled"

    if history_url:
        history_payload, history_source = utils.fetch_json_with_cache(
            history_cache_file,
            ttl_seconds=ttl_seconds,
            fetcher=lambda: _fetch_json_with_diagnostics(history_url, timeout_sec=6),
            fallback=[],
        )
    else:
        history_payload = _read_local_json(history_cache_file, [])
        history_source = "cache-local" if history_cache_file.exists() else "missing"

    if not isinstance(history_payload, list):
        history_payload = []

    normalized_history = _normalize_history(history_payload)
    return normalized_now, normalized_history, f"{now_source}/{history_source}"


def fetch_now(
    config: dict[str, Any],
    cache_dir: Path,
    content_dir: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    source_result = _fetch_from_source_endpoint(config, cache_dir, content_dir)
    if source_result is not None:
        return source_result
    return _fetch_legacy_endpoints(config, cache_dir, content_dir)
