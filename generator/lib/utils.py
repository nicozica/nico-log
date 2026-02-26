from __future__ import annotations

import json
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml
from dateutil import parser as date_parser


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_text(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return default


def read_json(path: Path, default: Any = None) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path: Path, payload: Any) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def load_yaml(path: Path, default: Any = None) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
            return default if data is None else data
    except FileNotFoundError:
        return default


def load_lines(path: Path) -> list[str]:
    raw = read_text(path, "")
    return [line.strip() for line in raw.splitlines() if line.strip()]


def is_cache_fresh(path: Path, ttl_seconds: int) -> bool:
    if ttl_seconds <= 0 or not path.exists():
        return False
    age_seconds = time.time() - path.stat().st_mtime
    return age_seconds <= ttl_seconds


def fetch_json_with_cache(
    cache_path: Path,
    ttl_seconds: int,
    fetcher: Callable[[], Any],
    fallback: Any,
) -> tuple[Any, str]:
    cached = read_json(cache_path, None)

    if cached is not None and is_cache_fresh(cache_path, ttl_seconds):
        return cached, "cache"

    try:
        fresh = fetcher()
        write_json(cache_path, fresh)
        return fresh, "live"
    except Exception:
        if cached is not None:
            return cached, "stale"
        if callable(fallback):
            return fallback(), "fallback"
        return fallback, "fallback"


def to_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
    elif isinstance(value, str) and value.strip():
        dt = date_parser.parse(value)
    else:
        dt = datetime.now(tz=timezone.utc)

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def format_datetime(dt: datetime) -> str:
    return to_datetime(dt).strftime("%Y-%m-%d %H:%M")


def slugify(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9\s-]", "", lowered)
    lowered = re.sub(r"[\s_-]+", "-", lowered)
    lowered = lowered.strip("-")
    return lowered or "note"


def excerpt_from_markdown(body: str, words: int = 45) -> str:
    text = re.sub(r"`{1,3}.*?`{1,3}", "", body, flags=re.DOTALL)
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
    text = re.sub(r"[#>*_~\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    chunks = text.split(" ")
    if len(chunks) <= words:
        return text
    return " ".join(chunks[:words]).strip() + "…"


def clean_output_dir(path: Path) -> None:
    ensure_dir(path)
    for child in path.iterdir():
        if child.name == ".gitkeep":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def copy_static_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def format_uptime(seconds: float | int | None) -> str:
    if seconds is None:
        return "n/a"

    total = int(seconds)
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)

    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def pick_tiny_thing(lines: list[str], when: datetime) -> str:
    if not lines:
        return "Mantenelo simple y en línea."
    index = when.toordinal() % len(lines)
    return lines[index]
