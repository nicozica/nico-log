#!/usr/bin/env bash
set -euo pipefail
umask 022

# Export live power metrics for the Raspberry Pi Zero 2 W plug from Home Assistant.
# Keep token and Home Assistant details server-side only.

TOKEN_FILE="${TOKEN_FILE:-/srv/secrets/nico-log/ha.token}"
HA_BASE_URL="${HA_BASE_URL:-http://homeassistant.local:8123}"
OUT_DIR="${OUT_DIR:-/srv/data/www/nico.com.ar/status}"
OUT_FILE="${OUT_FILE:-$OUT_DIR/pizero-power.json}"
CACHE_FILE="${CACHE_FILE:-/srv/data/nico-log/pizero-power-cache.json}"

ENTITY_POWER="${ENTITY_POWER:-sensor.raspberry_pi_zero_2_w_power}"
ENTITY_CURRENT="${ENTITY_CURRENT:-sensor.raspberry_pi_zero_2_w_current}"
ENTITY_VOLTAGE="${ENTITY_VOLTAGE:-sensor.raspberry_pi_zero_2_w_voltage}"
ENTITY_TOTAL_ENERGY="${ENTITY_TOTAL_ENERGY:-sensor.raspberry_pi_zero_2_w_total_energy}"

if [ ! -r "$TOKEN_FILE" ]; then
  echo "Token file is missing or unreadable: $TOKEN_FILE" >&2
  exit 1
fi

TOKEN="$(tr -d '\r\n' < "$TOKEN_FILE")"
if [ -z "$TOKEN" ]; then
  echo "Token file is empty: $TOKEN_FILE" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
mkdir -p "$(dirname "$CACHE_FILE")"

TMP_FILE="$(mktemp "${OUT_FILE}.tmp.XXXXXX")"
TMP_CACHE_FILE="$(mktemp "${CACHE_FILE}.tmp.XXXXXX")"
cleanup() {
  rm -f "$TMP_FILE"
  rm -f "$TMP_CACHE_FILE"
}
trap cleanup EXIT

python3 - "$HA_BASE_URL" "$TOKEN" "$ENTITY_POWER" "$ENTITY_CURRENT" "$ENTITY_VOLTAGE" "$ENTITY_TOTAL_ENERGY" "$CACHE_FILE" "$TMP_CACHE_FILE" "$TMP_FILE" <<'PY'
import json
import math
from pathlib import Path
import sys
import time
import urllib.request


def fetch_state(base_url: str, token: str, entity_id: str) -> tuple[float, str]:
    url = base_url.rstrip("/") + "/api/states/" + entity_id
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        payload = json.load(response)

    raw_state = str(payload.get("state", "")).strip()
    if raw_state in {"", "unknown", "unavailable"}:
        raise RuntimeError(f"Invalid state for {entity_id}: {raw_state!r}")

    value = float(raw_state)
    attributes = payload.get("attributes", {})
    unit = str(attributes.get("unit_of_measurement", "")).strip()
    return value, unit


def read_cache(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def calculate_power_estimate(raw_power: float, total_energy: float, cache_payload: dict) -> float | None:
    if raw_power > 0:
        return raw_power

    previous_ts = cache_payload.get("ts")
    previous_energy = cache_payload.get("total_energy")
    if previous_ts is None or previous_energy is None:
        return None

    try:
        previous_ts = float(previous_ts)
        previous_energy = float(previous_energy)
    except (TypeError, ValueError):
        return None

    current_ts = time.time()
    delta_seconds = current_ts - previous_ts
    delta_energy = total_energy - previous_energy
    if delta_seconds <= 0 or delta_energy <= 0:
        return None

    estimate = (delta_energy * 3600000.0) / delta_seconds
    if not math.isfinite(estimate) or estimate <= 0:
        return None
    return estimate


def main() -> None:
    (
        base_url,
        token,
        power_id,
        current_id,
        voltage_id,
        total_energy_id,
        cache_path_raw,
        tmp_cache_path_raw,
        out_path_raw,
    ) = sys.argv[1:10]

    cache_path = Path(cache_path_raw)
    tmp_cache_path = Path(tmp_cache_path_raw)
    out_path = Path(out_path_raw)

    power, power_unit = fetch_state(base_url, token, power_id)
    current, current_unit = fetch_state(base_url, token, current_id)
    voltage, voltage_unit = fetch_state(base_url, token, voltage_id)
    total_energy, total_energy_unit = fetch_state(base_url, token, total_energy_id)
    now_ts = int(time.time())

    cache_payload = read_cache(cache_path)
    power_estimate_w = calculate_power_estimate(power, total_energy, cache_payload)

    payload = {
        "ts": now_ts,
        "pizero": {
            "power": power,
            "power_raw": power,
            "power_unit": power_unit or "W",
            "power_estimate_w": round(power_estimate_w, 3) if power_estimate_w is not None else None,
            "power_estimate_unit": "W",
            "current": current,
            "current_unit": current_unit or "A",
            "voltage": voltage,
            "voltage_unit": voltage_unit or "V",
            "total_energy": total_energy,
            "total_energy_unit": total_energy_unit or "kWh",
        },
    }
    cache_update = {
        "ts": now_ts,
        "total_energy": total_energy,
    }

    out_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp_cache_path.write_text(json.dumps(cache_update, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    main()
PY

chmod 0644 "$TMP_FILE"
mv "$TMP_FILE" "$OUT_FILE"
chmod 0644 "$TMP_CACHE_FILE"
mv "$TMP_CACHE_FILE" "$CACHE_FILE"
