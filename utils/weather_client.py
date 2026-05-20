"""
Fetch current weather and 3-day forecast for Indian agricultural state capitals.

Uses Open-Meteo (https://open-meteo.com) — free, no API key, production-safe.
Every public function returns None on any failure; callers must treat None as
a graceful absence, not an error condition.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime
from typing import Optional

# Agricultural hub city per state: (lat, lon, city_name)
STATE_HUBS: dict[str, tuple[float, float, str]] = {
    "Uttar Pradesh":  (26.85, 80.95, "Lucknow"),
    "Rajasthan":      (26.91, 75.79, "Jaipur"),
    "Madhya Pradesh": (23.26, 77.41, "Bhopal"),
    "Bihar":          (25.59, 85.14, "Patna"),
    "Haryana":        (30.74, 76.79, "Chandigarh"),
    "Punjab":         (30.74, 76.79, "Chandigarh"),
    "Maharashtra":    (18.53, 73.85, "Pune"),
    "Gujarat":        (23.03, 72.58, "Ahmedabad"),
    "Karnataka":      (12.97, 77.59, "Bengaluru"),
    "West Bengal":    (22.57, 88.36, "Kolkata"),
}

# WMO weather interpretation codes → human label
WMO_CODES: dict[int, str] = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Icy fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm + hail", 99: "Thunderstorm + heavy hail",
}

_TIMEOUT_S = 5
_BASE_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_weather(state: str) -> Optional[dict]:
    """Return current weather dict for a state's agricultural hub city.

    Returns None if:
    - state is not in STATE_HUBS
    - network is unreachable within _TIMEOUT_S
    - response is malformed or missing expected fields
    """
    coords = STATE_HUBS.get(state)
    if not coords:
        return None

    lat, lon, city = coords
    params = (
        f"?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,weather_code,wind_speed_10m,relative_humidity_2m"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
        f"&forecast_days=3&timezone=Asia%2FKolkata"
    )
    try:
        req = urllib.request.Request(
            _BASE_URL + params,
            headers={"User-Agent": "KrishiPracharak/1.0"},
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:
            data = json.loads(resp.read())

        cur = data.get("current", {})
        daily = data.get("daily", {})
        code = cur.get("weather_code")
        condition = WMO_CODES.get(int(code), "Unknown") if code is not None else "Unknown"

        return {
            "state": state,
            "city": city,
            "temp_c": cur.get("temperature_2m"),
            "humidity_pct": cur.get("relative_humidity_2m"),
            "wind_kmh": cur.get("wind_speed_10m"),
            "condition": condition,
            "forecast_3day": [
                {"date": d, "max_c": mx, "min_c": mn, "rain_mm": rn}
                for d, mx, mn, rn in zip(
                    daily.get("time", []),
                    daily.get("temperature_2m_max", []),
                    daily.get("temperature_2m_min", []),
                    daily.get("precipitation_sum", []),
                )
            ],
            "fetched_at": datetime.utcnow().isoformat(),
        }
    except (urllib.error.URLError, OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


def fetch_weather_multi(states: list[str]) -> dict[str, Optional[dict]]:
    """Fetch weather for multiple states. Per-state failures silently return None."""
    return {s: fetch_weather(s) for s in states}
