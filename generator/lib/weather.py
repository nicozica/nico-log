from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from . import utils


WEATHER_CODES = {
    0: "clear",
    1: "mostly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "drizzle",
    55: "dense drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    80: "rain showers",
    81: "rain showers",
    82: "violent rain showers",
    95: "thunderstorm",
}


def _fetch_weather(site: dict[str, Any]) -> dict[str, Any]:
    params = {
        "latitude": site.get("latitude"),
        "longitude": site.get("longitude"),
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
        "timezone": site.get("timezone", "auto"),
    }

    response = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=6)
    response.raise_for_status()

    payload = response.json().get("current", {})
    code = int(payload.get("weather_code", 0))
    return {
        "updated_at": datetime.now(tz=timezone.utc).isoformat(),
        "temp_c": float(payload.get("temperature_2m", 0.0)),
        "humidity": int(payload.get("relative_humidity_2m", 0)),
        "wind_kmh": float(payload.get("wind_speed_10m", 0.0)),
        "description": WEATHER_CODES.get(code, "unknown"),
    }


def _fallback_weather() -> dict[str, Any]:
    return {
        "updated_at": datetime.now(tz=timezone.utc).isoformat(),
        "temp_c": 24.0,
        "humidity": 58,
        "wind_kmh": 12.0,
        "description": "offline cached forecast",
    }


def fetch_weather(config: dict[str, Any], cache_dir: Path) -> tuple[dict[str, Any], str]:
    site = config.get("site", {})
    ttl = int(config.get("weather_ttl_minutes", 30))
    cache_file = cache_dir / "weather.json"

    payload, source = utils.fetch_json_with_cache(
        cache_file,
        ttl_seconds=ttl * 60,
        fetcher=lambda: _fetch_weather(site),
        fallback=_fallback_weather,
    )

    temp = float(payload.get("temp_c", 0.0))
    humidity = int(payload.get("humidity", 0))
    wind = float(payload.get("wind_kmh", 0.0))

    item = {
        "temp_c": temp,
        "humidity": humidity,
        "wind_kmh": wind,
        "description": str(payload.get("description", "unknown")),
        "temp_label": f"{temp:.1f}°C",
        "humidity_label": f"{humidity}%",
        "wind_label": f"{wind:.0f} km/h",
    }
    return item, source
