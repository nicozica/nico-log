from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from . import utils


WEATHER_CODES = {
    0: "despejado",
    1: "mayormente despejado",
    2: "parcialmente nublado",
    3: "nublado",
    45: "niebla",
    48: "niebla con escarcha",
    51: "llovizna leve",
    53: "llovizna",
    55: "llovizna intensa",
    61: "lluvia leve",
    63: "lluvia",
    65: "lluvia intensa",
    71: "nieve leve",
    73: "nieve",
    75: "nieve intensa",
    80: "chaparrones",
    81: "chaparrones",
    82: "chaparrones fuertes",
    95: "tormenta",
}

DESCRIPTION_ALIASES = {
    "clear": "despejado",
    "mostly clear": "mayormente despejado",
    "partly cloudy": "parcialmente nublado",
    "overcast": "nublado",
    "fog": "niebla",
    "depositing rime fog": "niebla con escarcha",
    "light drizzle": "llovizna leve",
    "drizzle": "llovizna",
    "dense drizzle": "llovizna intensa",
    "light rain": "lluvia leve",
    "rain": "lluvia",
    "heavy rain": "lluvia intensa",
    "light snow": "nieve leve",
    "snow": "nieve",
    "heavy snow": "nieve intensa",
    "rain showers": "chaparrones",
    "violent rain showers": "chaparrones fuertes",
    "thunderstorm": "tormenta",
    "offline cached forecast": "pronóstico en cache",
    "unknown": "desconocido",
}


def _to_spanish_description(value: Any) -> str:
    description = str(value or "").strip().lower()
    if not description:
        return "desconocido"
    return DESCRIPTION_ALIASES.get(description, str(value))


def _icon_for_description(value: Any) -> str:
    description = str(value or "").strip().lower()
    if not description:
        return "cloud"

    if any(token in description for token in ("tormenta", "thunderstorm")):
        return "storm"
    if any(token in description for token in ("llovizna", "drizzle")):
        return "drizzle"
    if any(token in description for token in ("lluvia", "rain", "chaparr")):
        return "rain"
    if any(token in description for token in ("nieve", "snow")):
        return "snow"
    if any(token in description for token in ("niebla", "mist", "fog", "haze", "neblina")):
        return "mist"
    if any(token in description for token in ("despejado", "soleado", "clear", "sun")):
        return "sun"
    if any(token in description for token in ("nublado", "cloud", "overcast")):
        return "cloud"
    return "cloud"


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
        "description": WEATHER_CODES.get(code, "desconocido"),
    }


def _fallback_weather() -> dict[str, Any]:
    return {
        "updated_at": datetime.now(tz=timezone.utc).isoformat(),
        "temp_c": 24.0,
        "humidity": 58,
        "wind_kmh": 12.0,
        "description": "pronóstico en cache",
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
        "description": _to_spanish_description(payload.get("description", "desconocido")),
        "temp_label": f"{temp:.1f}°C",
        "humidity_label": f"{humidity}%",
        "wind_label": f"{wind:.0f} km/h",
    }
    item["icon"] = _icon_for_description(item["description"])
    return item, source
