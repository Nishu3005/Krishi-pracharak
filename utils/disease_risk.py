"""
Disease and pest risk assessment derived from real-time weather data.

Rules are based on published agronomy thresholds:
  Fungal risk  : humidity >= 75 % AND cumulative 3-day rain >= 5 mm
  Pest surge   : max temp >= 35 °C AND humidity < 55 % AND 3-day rain < 2 mm
  Spray blocked: wind >= 25 km/h  (droplet drift, ineffective application)
  Spray window : rain < 1 mm today AND wind < 15 km/h (ideal spray conditions)

Returns a list of risk dicts — one per state — that can be used to:
  1. Boost receptivity score for affected grower segments
  2. Show outbreak alerts in the campaign UI
  3. Inject disease-specific context into AI-generated content
"""
from __future__ import annotations
from typing import Optional

# Crop → diseases that favour wet/humid conditions
_FUNGAL_RISKS: dict[str, dict] = {
    "wheat":     {"disease": "Yellow Rust",          "pathogen": "Puccinia striiformis",   "product_hint": "fungicide"},
    "paddy":     {"disease": "Blast",                "pathogen": "Magnaporthe oryzae",      "product_hint": "fungicide"},
    "rice":      {"disease": "Blast",                "pathogen": "Magnaporthe oryzae",      "product_hint": "fungicide"},
    "cotton":    {"disease": "Grey Mildew",          "pathogen": "Ramularia areola",        "product_hint": "fungicide"},
    "chickpea":  {"disease": "Botrytis Grey Mould",  "pathogen": "Botrytis cinerea",        "product_hint": "fungicide"},
    "soybean":   {"disease": "Soybean Rust",         "pathogen": "Phakopsora pachyrhizi",   "product_hint": "fungicide"},
    "mustard":   {"disease": "White Rust",           "pathogen": "Albugo candida",          "product_hint": "fungicide"},
    "maize":     {"disease": "Turcicum Leaf Blight", "pathogen": "Exserohilum turcicum",    "product_hint": "fungicide"},
    "tomato":    {"disease": "Late Blight",          "pathogen": "Phytophthora infestans",  "product_hint": "fungicide"},
    "potato":    {"disease": "Late Blight",          "pathogen": "Phytophthora infestans",  "product_hint": "fungicide"},
    "groundnut": {"disease": "Tikka Leaf Spot",      "pathogen": "Cercospora arachidicola", "product_hint": "fungicide"},
    "onion":     {"disease": "Purple Blotch",        "pathogen": "Alternaria porri",        "product_hint": "fungicide"},
    "barley":    {"disease": "Powdery Mildew",       "pathogen": "Blumeria graminis",       "product_hint": "fungicide"},
    "lentil":    {"disease": "Rust",                 "pathogen": "Uromyces viciae-fabae",   "product_hint": "fungicide"},
    "cumin":     {"disease": "Powdery Mildew",       "pathogen": "Erysiphe polygoni",       "product_hint": "fungicide"},
    "safflower": {"disease": "Alternaria Leaf Spot", "pathogen": "Alternaria carthami",     "product_hint": "fungicide"},
}

# Crop → pests that surge in hot/dry conditions
_PEST_RISKS: dict[str, dict] = {
    "wheat":     {"pest": "Aphids",           "scientific": "Sitobion avenae",     "product_hint": "insecticide"},
    "paddy":     {"pest": "Brown Plant Hopper","scientific": "Nilaparvata lugens",  "product_hint": "insecticide"},
    "rice":      {"pest": "Brown Plant Hopper","scientific": "Nilaparvata lugens",  "product_hint": "insecticide"},
    "cotton":    {"pest": "Whitefly",          "scientific": "Bemisia tabaci",      "product_hint": "insecticide"},
    "chickpea":  {"pest": "Pod Borer",         "scientific": "Helicoverpa armigera","product_hint": "insecticide"},
    "soybean":   {"pest": "Girdle Beetle",     "scientific": "Obereopsis brevis",   "product_hint": "insecticide"},
    "mustard":   {"pest": "Painted Bug",       "scientific": "Bagrada hilaris",     "product_hint": "insecticide"},
    "maize":     {"pest": "Fall Armyworm",     "scientific": "Spodoptera frugiperda","product_hint": "insecticide"},
    "tomato":    {"pest": "Fruit Borer",       "scientific": "Helicoverpa armigera","product_hint": "insecticide"},
    "potato":    {"pest": "Aphids",            "scientific": "Myzus persicae",      "product_hint": "insecticide"},
    "groundnut": {"pest": "Thrips",            "scientific": "Frankliniella schultzei","product_hint": "insecticide"},
    "onion":     {"pest": "Thrips",            "scientific": "Thrips tabaci",        "product_hint": "insecticide"},
    "barley":    {"pest": "Aphids",            "scientific": "Rhopalosiphum padi",   "product_hint": "insecticide"},
    "lentil":    {"pest": "Pod Borer",         "scientific": "Helicoverpa armigera", "product_hint": "insecticide"},
    "cumin":     {"pest": "Thrips",            "scientific": "Thrips tabaci",        "product_hint": "insecticide"},
    "safflower": {"pest": "Aphids",            "scientific": "Myzus persicae",       "product_hint": "insecticide"},
}


def assess_risk(
    weather: Optional[dict],
    crop: str,
    state: str,
) -> dict:
    """
    Return a risk assessment dict for a crop/state given its weather.

    Keys:
      risk_level      : "high" | "moderate" | "low" | "none"
      risk_type       : "fungal" | "pest" | "spray_blocked" | None
      alert_title     : short headline for the UI
      alert_body      : 1-2 sentence explanation
      spray_window_ok : bool — conditions suitable for spraying right now
      score_boost     : float added to receptivity score for affected growers
      content_context : str injected into AI content prompts
    """
    base = {
        "state": state,
        "crop": crop,
        "risk_level": "none",
        "risk_type": None,
        "alert_title": None,
        "alert_body": None,
        "spray_window_ok": True,
        "score_boost": 0.0,
        "content_context": "",
    }

    if not weather:
        return base

    humidity   = weather.get("humidity_pct") or 0
    temp_c     = weather.get("temp_c") or 25
    wind_kmh   = weather.get("wind_kmh") or 0
    forecast   = weather.get("forecast_3day") or []
    rain_3day  = sum(d.get("rain_mm") or 0 for d in forecast)
    rain_today = forecast[0]["rain_mm"] if forecast else 0
    max_temp   = max((d.get("max_c") or temp_c) for d in forecast) if forecast else temp_c

    crop_key = crop.strip().lower()

    # Spray window check
    spray_blocked_wind = wind_kmh >= 25
    spray_blocked_rain = (rain_today or 0) >= 1
    spray_window_ok    = not spray_blocked_wind and not spray_blocked_rain
    base["spray_window_ok"] = spray_window_ok

    # ── Fungal risk ──────────────────────────────────────────────────────
    if humidity >= 75 and rain_3day >= 5:
        info = _FUNGAL_RISKS.get(crop_key)
        if info:
            level = "high" if (humidity >= 85 or rain_3day >= 15) else "moderate"
            base.update({
                "risk_level": level,
                "risk_type": "fungal",
                "alert_title": f"{info['disease']} Risk — {state}",
                "alert_body": (
                    f"High humidity ({humidity:.0f}%) and {rain_3day:.0f} mm rain forecast "
                    f"create favourable conditions for {info['disease']} "
                    f"({info['pathogen']}) in {crop} crops. "
                    f"Early protective spray is recommended."
                ),
                "score_boost": 0.08 if level == "high" else 0.04,
                "content_context": (
                    f"WEATHER ALERT: {info['disease']} risk is {level} in {state} — "
                    f"humidity {humidity:.0f}%, {rain_3day:.0f} mm rain in 3 days. "
                    f"Recommend protective {info['product_hint']} application immediately. "
                    f"Mention this urgency in the message."
                ),
            })
            return base

    # ── Pest surge risk ──────────────────────────────────────────────────
    if max_temp >= 35 and humidity < 55 and rain_3day < 2:
        info = _PEST_RISKS.get(crop_key)
        if info:
            level = "high" if max_temp >= 38 else "moderate"
            base.update({
                "risk_level": level,
                "risk_type": "pest",
                "alert_title": f"{info['pest']} Surge Risk — {state}",
                "alert_body": (
                    f"Hot, dry conditions (max {max_temp:.0f}°C, humidity {humidity:.0f}%) "
                    f"accelerate {info['pest']} ({info['scientific']}) population growth "
                    f"in {crop} crops. Population can double in 5–7 days under these conditions."
                ),
                "score_boost": 0.06 if level == "high" else 0.03,
                "content_context": (
                    f"WEATHER ALERT: {info['pest']} surge risk is {level} in {state} — "
                    f"hot dry weather (max {max_temp:.0f}°C). "
                    f"Recommend {info['product_hint']} application before population explodes. "
                    f"Mention this risk in the message."
                ),
            })
            return base

    # ── Low risk but note spray window ───────────────────────────────────
    if not spray_window_ok:
        reason = "high winds" if spray_blocked_wind else "rain forecast"
        base.update({
            "risk_level": "low",
            "risk_type": "spray_blocked",
            "alert_title": f"Spray Window Blocked — {state}",
            "alert_body": f"Application not recommended today due to {reason}. Advise growers to wait.",
            "score_boost": -0.02,
            "content_context": f"NOTE: Spraying is not recommended in {state} today due to {reason}.",
        })

    return base


def assess_risks_for_plan(
    weather_by_state: dict[str, Optional[dict]],
    segments: list[dict],
) -> dict[str, dict]:
    """
    Return {state_crop_key: risk_dict} for every unique (state, crop) in the plan.
    Key format: "state||crop"
    """
    seen = {}
    for seg in segments:
        state = seg.get("state", "")
        crop  = seg.get("crop", "")
        key   = f"{state}||{crop}"
        if key not in seen:
            w = weather_by_state.get(state)
            seen[key] = assess_risk(w, crop, state)
    return seen
