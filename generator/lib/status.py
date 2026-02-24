from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from . import utils


def _check_systemd_service(name: str) -> dict[str, str]:
    try:
        result = subprocess.run(
            ["systemctl", "is-active", name],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except FileNotFoundError:
        return {"name": name, "state": "unknown", "detail": "systemctl unavailable"}
    except subprocess.TimeoutExpired:
        return {"name": name, "state": "degraded", "detail": "timed out"}

    state = result.stdout.strip() or result.stderr.strip() or "unknown"

    if state == "active":
        mapped = "up"
    elif state in {"activating", "reloading"}:
        mapped = "degraded"
    elif state in {"inactive", "failed", "deactivating"}:
        mapped = "down"
    else:
        mapped = "unknown"

    return {"name": name, "state": mapped, "detail": state}


def _check_http(name: str, url: str) -> dict[str, str]:
    try:
        response = requests.get(url, timeout=4)
        code = response.status_code
    except requests.RequestException as exc:
        return {"name": name, "state": "down", "detail": f"error: {exc.__class__.__name__}"}

    if code < 400:
        state = "up"
    elif code < 500:
        state = "degraded"
    else:
        state = "down"

    return {"name": name, "state": state, "detail": f"HTTP {code}"}


def _uptime_seconds() -> float | None:
    path = Path("/proc/uptime")
    if not path.exists():
        return None

    try:
        raw = path.read_text(encoding="utf-8").split()[0]
        return float(raw)
    except (ValueError, IndexError):
        return None


def _cpu_temp_c() -> float | None:
    path = Path("/sys/class/thermal/thermal_zone0/temp")
    if not path.exists():
        return None

    try:
        milli = float(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None
    return milli / 1000.0


def _collect_status(config: dict[str, Any]) -> dict[str, Any]:
    services = [
        _check_systemd_service(str(name))
        for name in config.get("status_services", [])
    ]

    http_checks = [
        _check_http(str(item.get("name", "http")), str(item.get("url", "")))
        for item in config.get("status_http_checks", [])
        if item.get("url")
    ]

    return {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "services": services,
        "http_checks": http_checks,
        "uptime_seconds": _uptime_seconds(),
        "cpu_temp_c": _cpu_temp_c(),
    }


def fetch_status(config: dict[str, Any], cache_dir: Path) -> tuple[dict[str, Any], str]:
    ttl = int(config.get("status_ttl_minutes", 10))
    cache_file = cache_dir / "status.json"

    payload, source = utils.fetch_json_with_cache(
        cache_file,
        ttl_seconds=ttl * 60,
        fetcher=lambda: _collect_status(config),
        fallback=lambda: {
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "services": [],
            "http_checks": [],
            "uptime_seconds": None,
            "cpu_temp_c": None,
        },
    )

    cpu_temp = payload.get("cpu_temp_c")
    cpu_temp_label = "n/a" if cpu_temp is None else f"{float(cpu_temp):.1f}°C"

    summary = {
        "uptime_seconds": payload.get("uptime_seconds"),
        "uptime_label": utils.format_uptime(payload.get("uptime_seconds")),
        "cpu_temp_label": cpu_temp_label,
    }

    status = {
        "services": payload.get("services", []),
        "http_checks": payload.get("http_checks", []),
        "source": source,
    }

    return {"status": status, "summary": summary}, source
