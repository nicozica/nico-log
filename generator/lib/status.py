from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from . import utils

STATE_LABELS = {
    "up": "activo",
    "degraded": "degradado",
    "down": "caído",
    "unknown": "desconocido",
}

SOURCE_LABELS = {
    "live": "en vivo",
    "cache": "cache",
    "stale": "cache vencida",
    "fallback": "fallback",
    "unknown": "desconocido",
}

SYSTEMCTL_DETAIL_LABELS = {
    "active": "activo",
    "activating": "activando",
    "reloading": "recargando",
    "inactive": "inactivo",
    "failed": "fallido",
    "deactivating": "desactivando",
    "unknown": "desconocido",
}


def _status_settings(config: dict[str, Any]) -> dict[str, Any]:
    settings = config.get("status", {})
    if not isinstance(settings, dict):
        return {}
    return settings


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
        return {"name": name, "state": "unknown", "detail": "systemctl no disponible"}
    except subprocess.TimeoutExpired:
        return {"name": name, "state": "degraded", "detail": "timeout"}

    state = result.stdout.strip() or result.stderr.strip() or "unknown"

    if state == "active":
        mapped = "up"
    elif state in {"activating", "reloading"}:
        mapped = "degraded"
    elif state in {"inactive", "failed", "deactivating"}:
        mapped = "down"
    else:
        mapped = "unknown"

    detail = SYSTEMCTL_DETAIL_LABELS.get(state, state)
    return {"name": name, "state": mapped, "detail": detail}


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


def _apply_state_labels(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        state = str(item.get("state", "unknown")).strip().lower() or "unknown"
        detail = str(item.get("detail", "")).strip()
        detail = SYSTEMCTL_DETAIL_LABELS.get(detail, detail)
        rows.append(
            {
                **item,
                "state": state,
                "state_label": STATE_LABELS.get(state, STATE_LABELS["unknown"]),
                "detail": detail,
            }
        )
    return rows


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


def _collect_remote_metrics_via_ssh(settings: dict[str, Any], cache_dir: Path) -> dict[str, Any]:
    ssh_target = str(settings.get("ssh_target", "")).strip()
    ssh_timeout_sec = float(settings.get("ssh_timeout_sec", 3) or 3)
    allow_fallback_cache = bool(settings.get("allow_fallback_cache", True))
    remote_cache_file = cache_dir / "status_remote.json"

    remote_command = "cut -d. -f1 /proc/uptime; cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || true"
    try:
        if not ssh_target:
            raise ValueError("missing ssh target")

        result = subprocess.run(
            [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                f"ConnectTimeout={int(ssh_timeout_sec)}",
                ssh_target,
                remote_command,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=max(1.0, ssh_timeout_sec + 1.0),
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "ssh failed")

        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if not lines:
            raise ValueError("ssh returned empty payload")

        uptime_seconds = int(float(lines[0]))
        cpu_temp_c: float | None = None
        if len(lines) > 1:
            try:
                cpu_temp_c = float(int(lines[1])) / 1000.0
            except ValueError:
                cpu_temp_c = None

        remote_payload = {
            "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
            "uptime_seconds": uptime_seconds,
            "cpu_temp_c": cpu_temp_c,
        }
        utils.write_json(remote_cache_file, remote_payload)
        return {
            "uptime_seconds": uptime_seconds,
            "cpu_temp_c": cpu_temp_c,
            "metrics_stale": False,
            "metrics_source": "remote_ssh",
        }
    except Exception:
        if allow_fallback_cache:
            cached_payload = utils.read_json(remote_cache_file, None)
            if isinstance(cached_payload, dict):
                try:
                    cached_uptime = int(float(cached_payload.get("uptime_seconds")))
                    cached_cpu_raw = cached_payload.get("cpu_temp_c")
                    cached_cpu = float(cached_cpu_raw) if cached_cpu_raw is not None else None
                    return {
                        "uptime_seconds": cached_uptime,
                        "cpu_temp_c": cached_cpu,
                        "metrics_stale": True,
                        "metrics_source": "remote_cache",
                    }
                except (TypeError, ValueError):
                    pass

        return {
            "uptime_seconds": _uptime_seconds(),
            "cpu_temp_c": _cpu_temp_c(),
            "metrics_stale": True,
            "metrics_source": "local_fallback",
        }


def _collect_metrics(config: dict[str, Any], cache_dir: Path) -> dict[str, Any]:
    settings = _status_settings(config)
    metrics_mode = str(settings.get("metrics_mode", "local")).strip().lower()
    if metrics_mode != "remote_ssh":
        return {
            "uptime_seconds": _uptime_seconds(),
            "cpu_temp_c": _cpu_temp_c(),
            "metrics_stale": False,
            "metrics_source": "local",
        }
    return _collect_remote_metrics_via_ssh(settings, cache_dir)


def _collect_status(config: dict[str, Any], cache_dir: Path) -> dict[str, Any]:
    metrics = _collect_metrics(config, cache_dir)

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
        "uptime_seconds": metrics.get("uptime_seconds"),
        "cpu_temp_c": metrics.get("cpu_temp_c"),
        "metrics_stale": bool(metrics.get("metrics_stale", False)),
        "metrics_source": str(metrics.get("metrics_source", "local")),
    }


def fetch_status(config: dict[str, Any], cache_dir: Path) -> tuple[dict[str, Any], str]:
    ttl = int(config.get("status_ttl_minutes", 10))
    status_settings = _status_settings(config)
    metrics_mode = str(status_settings.get("metrics_mode", "local")).strip().lower()
    # Always attempt fresh collection when metrics come from remote SSH.
    ttl_seconds = 0 if metrics_mode == "remote_ssh" else ttl * 60
    cache_file = cache_dir / "status.json"

    payload, source = utils.fetch_json_with_cache(
        cache_file,
        ttl_seconds=ttl_seconds,
        fetcher=lambda: _collect_status(config, cache_dir),
        fallback=lambda: {
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "services": [],
            "http_checks": [],
            "uptime_seconds": None,
            "cpu_temp_c": None,
            "metrics_stale": True,
            "metrics_source": "fallback",
        },
    )

    cpu_temp = payload.get("cpu_temp_c")
    cpu_temp_label = "n/a" if cpu_temp is None else f"{float(cpu_temp):.1f}°C"
    uptime_seconds = payload.get("uptime_seconds")
    metrics_stale = bool(payload.get("metrics_stale", source in {"stale", "fallback"}))

    summary = {
        "metrics_available": uptime_seconds is not None,
        "metrics_stale": metrics_stale,
        "uptime_seconds": uptime_seconds,
        "uptime_label": utils.format_uptime(uptime_seconds),
        "cpu_temp_label": cpu_temp_label,
    }

    services = payload.get("services", [])
    if not isinstance(services, list):
        services = []
    http_checks = payload.get("http_checks", [])
    if not isinstance(http_checks, list):
        http_checks = []

    status = {
        "services": _apply_state_labels(services),
        "http_checks": _apply_state_labels(http_checks),
        "source": source,
        "source_label": SOURCE_LABELS.get(source, SOURCE_LABELS["unknown"]),
        "metrics_source": str(payload.get("metrics_source", "unknown")),
    }

    return {"status": status, "summary": summary}, source
