from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from . import utils


def _normalize_now(item: dict[str, Any]) -> dict[str, Any]:
    started_at = utils.to_datetime(item.get("started_at"))
    return {
        "track": str(item.get("track", "Silence")),
        "artist": str(item.get("artist", "Unknown")),
        "url": str(item.get("url", "https://example.com")),
        "started_at": started_at.isoformat(),
        "started_label": started_at.strftime("%Y-%m-%d %H:%M"),
    }


def _normalize_history(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in history[:30]:
        played_at = utils.to_datetime(item.get("played_at"))
        rows.append(
            {
                "track": str(item.get("track", "Unknown")),
                "artist": str(item.get("artist", "Unknown")),
                "url": str(item.get("url", "")),
                "played_at": played_at.isoformat(),
                "played_label": played_at.strftime("%Y-%m-%d %H:%M"),
            }
        )
    return rows


def _fetch_json(url: str) -> dict[str, Any]:
    response = requests.get(url, timeout=6)
    response.raise_for_status()
    return response.json()


def _read_local_json(path: Path, default: Any) -> Any:
    data = utils.read_json(path, None)
    if data is None:
        return default
    return data


def _fallback_now(content_dir: Path) -> dict[str, Any]:
    path = content_dir / "now_playing_mock.json"
    data = _read_local_json(path, {})
    if data:
        return data
    return {
        "track": "Warm Breeze",
        "artist": "Blur FM",
        "url": "https://blur.fm/listen",
        "started_at": datetime.now(tz=timezone.utc).isoformat(),
    }


def _fallback_history(content_dir: Path) -> list[dict[str, Any]]:
    path = content_dir / "now_history_mock.json"
    data = _read_local_json(path, [])
    if isinstance(data, list) and data:
        return data
    return [
        {
            "track": "Warm Breeze",
            "artist": "Blur FM",
            "url": "https://blur.fm/listen",
            "played_at": datetime.now(tz=timezone.utc).isoformat(),
        }
    ]


def fetch_now(config: dict[str, Any], cache_dir: Path, content_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    ttl_minutes = int(config.get("now_ttl_minutes", 5))
    now_cache_file = cache_dir / "now_playing.json"
    history_cache_file = cache_dir / "now_history.json"

    now_url = str(config.get("now_playing_url", "")).strip()
    history_url = str(config.get("now_history_url", "")).strip()

    if now_url:
        now_payload, now_source = utils.fetch_json_with_cache(
            now_cache_file,
            ttl_seconds=ttl_minutes * 60,
            fetcher=lambda: _fetch_json(now_url),
            fallback=lambda: _fallback_now(content_dir),
        )
    else:
        now_payload = _read_local_json(now_cache_file, _fallback_now(content_dir))
        now_source = "cache-local" if now_cache_file.exists() else "mock"

    if history_url:
        history_payload, history_source = utils.fetch_json_with_cache(
            history_cache_file,
            ttl_seconds=ttl_minutes * 60,
            fetcher=lambda: _fetch_json(history_url),
            fallback=lambda: _fallback_history(content_dir),
        )
    else:
        history_payload = _read_local_json(history_cache_file, _fallback_history(content_dir))
        history_source = "cache-local" if history_cache_file.exists() else "mock"

    if not isinstance(history_payload, list):
        history_payload = _fallback_history(content_dir)

    normalized_now = _normalize_now(now_payload)
    normalized_history = _normalize_history(history_payload)
    source = f"{now_source}/{history_source}"
    return normalized_now, normalized_history, source
