from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

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

SUPPORTED_PROVIDERS = {"weatherapi", "open_meteo"}
WEEKDAY_NAMES = [
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes",
    "Sábado",
    "Domingo",
]


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


def _weather_settings(config: dict[str, Any]) -> dict[str, Any]:
    settings = config.get("weather", {})
    return settings if isinstance(settings, dict) else {}


def _weather_ttl_minutes(config: dict[str, Any]) -> int:
    settings = _weather_settings(config)
    raw_ttl = settings.get("ttl_minutes", config.get("weather_ttl_minutes", 30))
    try:
        ttl = int(raw_ttl)
    except (TypeError, ValueError):
        return 30
    return ttl if ttl > 0 else 30


def _preferred_provider(config: dict[str, Any]) -> str:
    settings = _weather_settings(config)
    provider = str(settings.get("provider", "open_meteo")).strip().lower()
    return provider if provider in SUPPORTED_PROVIDERS else "open_meteo"


def _provider_order(config: dict[str, Any]) -> list[str]:
    primary = _preferred_provider(config)
    secondary = [provider for provider in ("weatherapi", "open_meteo") if provider != primary]
    return [primary, *secondary]


def _cache_file(cache_dir: Path, provider: str) -> Path:
    return cache_dir / f"weather_{provider}.json"


def _day_label(value: Any, timezone_name: str) -> str:
    if isinstance(value, str) and len(value) == 10 and value[4] == "-" and value[7] == "-":
        day_value = datetime.strptime(value, "%Y-%m-%d")
    else:
        day_value = utils.to_datetime(value)
        try:
            day_value = day_value.astimezone(ZoneInfo(timezone_name))
        except Exception:
            pass

    return WEEKDAY_NAMES[day_value.weekday()]


def _range_label(max_temp: Any, min_temp: Any) -> str:
    return f"{round(float(min_temp))}° / {round(float(max_temp))}°"


def _normalize_forecast_days(entries: list[dict[str, Any]], timezone_name: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for entry in entries[:3]:
        description = _to_spanish_description(entry.get("description", "desconocido"))
        max_temp = float(entry.get("max_temp_c", 0.0))
        min_temp = float(entry.get("min_temp_c", 0.0))
        items.append(
            {
                "date": str(entry.get("date", "")).strip(),
                "label": _day_label(entry.get("date", ""), timezone_name),
                "description": description,
                "icon": _icon_for_description(description),
                "max_temp_c": max_temp,
                "min_temp_c": min_temp,
                "temp_range_label": _range_label(max_temp, min_temp),
            }
        )
    return items


def _fetch_open_meteo(site: dict[str, Any]) -> dict[str, Any]:
    params = {
        "latitude": site.get("latitude"),
        "longitude": site.get("longitude"),
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min",
        "forecast_days": 3,
        "timezone": site.get("timezone", "auto"),
    }

    response = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=6)
    response.raise_for_status()

    data = response.json()
    payload = data.get("current", {})
    daily = data.get("daily", {})
    code = int(payload.get("weather_code", 0))

    forecast_days = []
    for date_value, code_value, max_temp, min_temp in zip(
        daily.get("time", []),
        daily.get("weather_code", []),
        daily.get("temperature_2m_max", []),
        daily.get("temperature_2m_min", []),
    ):
        forecast_days.append(
            {
                "date": date_value,
                "description": WEATHER_CODES.get(int(code_value), "desconocido"),
                "max_temp_c": max_temp,
                "min_temp_c": min_temp,
            }
        )

    return {
        "provider": "open_meteo",
        "updated_at": datetime.now(tz=timezone.utc).isoformat(),
        "temp_c": float(payload.get("temperature_2m", 0.0)),
        "humidity": int(payload.get("relative_humidity_2m", 0)),
        "wind_kmh": float(payload.get("wind_speed_10m", 0.0)),
        "description": WEATHER_CODES.get(code, "desconocido"),
        "forecast": forecast_days,
    }


def _fetch_weatherapi(site: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    api_key_env = str(settings.get("api_key_env", "WEATHERAPI_KEY")).strip() or "WEATHERAPI_KEY"
    api_key = os.environ.get(api_key_env, "").strip()
    if not api_key:
        raise RuntimeError(f"Missing WeatherAPI key in env var {api_key_env}")

    latitude = site.get("latitude")
    longitude = site.get("longitude")
    query = ""
    if latitude not in (None, "") and longitude not in (None, ""):
        query = f"{latitude},{longitude}"
    else:
        query = str(site.get("city", "")).strip()
    if not query:
        raise RuntimeError("Weather query is empty")

    params = {
        "key": api_key,
        "q": query,
        "lang": "es",
        "aqi": "no",
        "days": 3,
    }
    response = requests.get("https://api.weatherapi.com/v1/forecast.json", params=params, timeout=6)
    response.raise_for_status()

    data = response.json()
    payload = data.get("current", {})
    condition = payload.get("condition", {})
    updated_at = payload.get("last_updated_epoch") or payload.get("last_updated")
    updated_label = utils.to_datetime(updated_at).isoformat() if updated_at else datetime.now(tz=timezone.utc).isoformat()

    forecast_days = []
    for item in data.get("forecast", {}).get("forecastday", []):
        day_payload = item.get("day", {})
        forecast_days.append(
            {
                "date": item.get("date", ""),
                "description": str(day_payload.get("condition", {}).get("text", "")).strip() or "desconocido",
                "max_temp_c": float(day_payload.get("maxtemp_c", 0.0)),
                "min_temp_c": float(day_payload.get("mintemp_c", 0.0)),
            }
        )

    return {
        "provider": "weatherapi",
        "updated_at": updated_label,
        "temp_c": float(payload.get("temp_c", 0.0)),
        "humidity": int(payload.get("humidity", 0)),
        "wind_kmh": float(payload.get("wind_kph", 0.0)),
        "description": str(condition.get("text", "")).strip() or "desconocido",
        "forecast": forecast_days,
    }


def _fetch_from_provider(provider: str, config: dict[str, Any]) -> dict[str, Any]:
    site = config.get("site", {})
    if not isinstance(site, dict):
        site = {}

    if provider == "weatherapi":
        return _fetch_weatherapi(site, _weather_settings(config))
    if provider == "open_meteo":
        return _fetch_open_meteo(site)
    raise RuntimeError(f"Unsupported weather provider: {provider}")


def _fetch_or_cached(cache_file: Path, ttl_seconds: int, fetcher: Any) -> tuple[dict[str, Any] | None, str]:
    cached = utils.read_json(cache_file, None)
    cache_has_forecast = isinstance(cached, dict) and isinstance(cached.get("forecast", []), list)

    if cached is not None and utils.is_cache_fresh(cache_file, ttl_seconds) and cache_has_forecast:
        return cached, "cache"

    try:
        fresh = fetcher()
        utils.write_json(cache_file, fresh)
        return fresh, "live"
    except Exception:
        if cached is not None:
            return cached, "stale"
        return None, "missing"


def _fallback_weather() -> dict[str, Any]:
    return {
        "provider": "fallback",
        "updated_at": datetime.now(tz=timezone.utc).isoformat(),
        "temp_c": 24.0,
        "humidity": 58,
        "wind_kmh": 12.0,
        "description": "pronóstico en cache",
        "forecast": [],
    }


def fetch_weather(config: dict[str, Any], cache_dir: Path) -> tuple[dict[str, Any], str]:
    site = config.get("site", {})
    timezone_name = str(site.get("timezone", "America/Argentina/Buenos_Aires")) if isinstance(site, dict) else "America/Argentina/Buenos_Aires"
    ttl_seconds = _weather_ttl_minutes(config) * 60
    payload = None
    source = "fallback"

    for provider in _provider_order(config):
        cache_file = _cache_file(cache_dir, provider)
        candidate, candidate_source = _fetch_or_cached(
            cache_file,
            ttl_seconds=ttl_seconds,
            fetcher=lambda provider=provider: _fetch_from_provider(provider, config),
        )
        if candidate is None:
            continue
        payload = candidate
        source = f"{provider}/{candidate_source}"
        break

    if payload is None:
        payload = _fallback_weather()

    temp = float(payload.get("temp_c", 0.0))
    humidity = int(payload.get("humidity", 0))
    wind = float(payload.get("wind_kmh", 0.0))
    description = _to_spanish_description(payload.get("description", "desconocido"))
    raw_forecast = payload.get("forecast", [])
    if not isinstance(raw_forecast, list):
        raw_forecast = []

    item = {
        "provider": str(payload.get("provider", "")).strip() or _preferred_provider(config),
        "temp_c": temp,
        "humidity": humidity,
        "wind_kmh": wind,
        "description": description,
        "temp_label": f"{temp:.1f}°C",
        "humidity_label": f"{humidity}%",
        "wind_label": f"{wind:.0f} km/h",
        "updated_at": payload.get("updated_at", ""),
        "forecast": _normalize_forecast_days(raw_forecast, timezone_name),
    }
    item["icon"] = _icon_for_description(description)
    return item, source
