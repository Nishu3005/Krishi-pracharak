import base64
import io
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

import time as _time
from agents.content_agent import run_content_generation_streaming, describe_promoter
from agents.rep_agent import run_rep_briefing
from agents.targeting_agent import run_targeting
from utils.campaign_store import attach_variants, delete_campaign, load_saved_campaigns, save_plan
from utils.data_loader import load_digital_funnel, load_growers, load_reps, load_whatsapp
from utils.ui_theme import apply_theme
from utils.landing_theme import inject_landing_css, crop_img, IMG_HERO, IMG_PEOPLE
from utils.overview_theme import (
    inject_overview_css, camp_header_html, section_label,
    agent_block_html, oos_block_html, seg_stats_html,
)

# Needed for lazy import of inventory_analysis inside _load_inv_insights()
sys.path.insert(0, str(Path(__file__).parent.parent / "Syngenta_IITM_Hackathon_2026_dataset"))

st.set_page_config(page_title="Campaign Builder · Krishi Pracharak", layout="wide")
apply_theme()

# ── Sidebar styles ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* All sidebar nav buttons — clean, minimal, left-aligned */
section[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: none !important;
    border-radius: 6px !important;
    text-align: left !important;
    width: 100% !important;
    padding: 0.32rem 0.6rem !important;
    color: rgba(210,232,216,0.6) !important;
    font-size: 0.81rem !important;
    font-weight: 400 !important;
    justify-content: flex-start !important;
    box-shadow: none !important;
    transition: background 0.1s, color 0.1s !important;
    line-height: 1.35 !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.06) !important;
    color: rgba(220,240,225,0.92) !important;
    border: none !important;
    box-shadow: none !important;
    transform: none !important;
}
/* Primary "New Campaign" button */
section[data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"],
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: #2f7d4c !important;
    border: none !important;
    color: #fff !important;
    font-weight: 600 !important;
    font-size: 0.83rem !important;
    border-radius: 8px !important;
    box-shadow: none !important;
    letter-spacing: 0.01em !important;
}
section[data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"]:hover,
section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
    background: #369958 !important;
    border: none !important;
    box-shadow: none !important;
    transform: none !important;
}
/* Remove extra padding Streamlit adds around column widgets in sidebar */
section[data-testid="stSidebar"] [data-testid="column"] {
    padding-left: 0.15rem !important;
    padding-right: 0.15rem !important;
}
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
_GREEN  = "#2f7d4c"
_AMBER  = "#b8701f"
_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=10, r=10, t=30, b=10),
    font=dict(color="#1a2520", family="Space Grotesk"),
)
REFERENCE_DATE = date.today()


def _layout_with(**overrides):
    layout = dict(_LAYOUT)
    layout.update(overrides)
    return layout


OBJECTIVES = [
    "Pre-Season Alert",
    "Awareness",
    "Harvest Optimization",
    "Post-Harvest",
    "Trial Push",
]

_STATE_COORDS: dict[str, tuple[float, float]] = {
    "Uttar Pradesh":  (26.85, 80.95),
    "Rajasthan":      (26.91, 75.79),
    "Madhya Pradesh": (23.26, 77.41),
    "Bihar":          (25.59, 85.14),
    "Haryana":        (30.74, 76.79),
    "Punjab":         (30.74, 76.79),
    "Maharashtra":    (18.53, 73.85),
    "Gujarat":        (23.03, 72.58),
    "Karnataka":      (12.97, 77.59),
    "West Bengal":    (22.57, 88.36),
}

# ── Session state ─────────────────────────────────────────────────────────────
for _k, _v in [
    ("cb_view", "welcome"),
    ("targeting_plan", None),
    ("content_variants", None),
    ("current_campaign_path", None),
    ("rep_briefing_result", None),
    ("rep_briefing_rep", None),
    ("promoter_image_b64", None),
    ("promoter_description", None),
    ("confirm_delete_id", None),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ── Generic helpers ───────────────────────────────────────────────────────────
def _fmt(n: float | int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(int(n))


def _summarize_oos_blocks(blocks: list[dict]) -> list[dict]:
    grouped: dict[tuple, dict] = {}
    for b in blocks or []:
        crop    = str(b.get("crop")    or "Unknown crop").strip().title()
        state   = str(b.get("state")   or "Unknown state").strip()
        product = str(b.get("product") or "Unknown product").strip()
        reason  = str(b.get("reason")  or "OOS risk").strip()
        try:
            growers = int(b.get("grower_count", 0) or 0)
        except (TypeError, ValueError):
            growers = 0
        key = (crop, state, product, reason)
        if key not in grouped:
            grouped[key] = {"crop": crop, "state": state, "product": product,
                            "reason": reason, "grower_count": 0}
        grouped[key]["grower_count"] += growers
    return sorted(grouped.values(), key=lambda x: x["grower_count"], reverse=True)


def _load_saved() -> list[dict]:
    return load_saved_campaigns()


def _persist_plan(plan: dict, source_meta: dict | None = None) -> str:
    current_path = st.session_state.current_campaign_path
    saved_path = save_plan(plan, Path(current_path) if current_path else None,
                           source_meta=source_meta)
    st.session_state.current_campaign_path = str(saved_path)
    return str(saved_path)


def _persist_variants(variants: dict) -> None:
    current_path = st.session_state.current_campaign_path
    if not current_path:
        return
    attach_variants(Path(current_path), variants)


@st.cache_data
def _scored_df():
    from utils.features import build_grower_features
    from utils.receptivity_score import score_dataframe
    return score_dataframe(build_grower_features(REFERENCE_DATE))


@st.cache_data(show_spinner=False, ttl=3600)
def _disease_ai_overview(alerts_json: str) -> str:
    """AI agronomic field advisory summarising all active outbreak alerts."""
    try:
        from utils.ai_client import call_text, TEXT_MODEL_FAST
        alerts = json.loads(alerts_json)
        if not alerts:
            return ""
        lines = "\n".join(
            f"- {a['level'].upper()} {a.get('type','')} — {a['title']}: {a['body']}"
            for a in alerts
        )
        return call_text(
            model=TEXT_MODEL_FAST,
            system=(
                "You are a senior agronomist at Syngenta India advising field sales reps. "
                "Be specific, practical, and urgent where needed. Max 3 sentences."
            ),
            user=(
                f"Active outbreak alerts for this campaign:\n{lines}\n\n"
                "Write a concise field advisory: which crops face the highest immediate risk, "
                "what action reps should take today, and what to tell farmers about protecting their crop."
            ),
            temperature=0.4,
        )
    except Exception:
        return ""


@st.cache_data(show_spinner=False, ttl=7200)
def _disease_outbreak_image(risk_type: str, crop: str, disease_name: str) -> str | None:
    """Generate an AI image for a disease/pest outbreak alert. Cached per disease × crop."""
    try:
        from utils.ai_client import call_image, IMAGE_MODEL
        if risk_type == "fungal":
            prompt = (
                f"Extreme close-up agricultural photograph of {disease_name} fungal disease "
                f"on {crop} crop leaves, showing characteristic lesions and spores, "
                f"field setting, natural light, photorealistic, plant pathology documentation"
            )
        elif risk_type == "pest":
            prompt = (
                f"Close-up agricultural photograph of {disease_name} pest infestation "
                f"on {crop} crop, insects clearly visible on damaged plant tissue, "
                f"field setting, natural light, photorealistic, entomology documentation"
            )
        else:
            return None
        return call_image(IMAGE_MODEL, prompt)
    except Exception:
        return None


@st.cache_data(ttl=1800)
def _fetch_weather_cached(states_tuple: tuple) -> dict:
    from utils.weather_client import fetch_weather_multi
    return fetch_weather_multi(list(states_tuple))


@st.cache_data
def _grower_states_by_crop(crop: str) -> dict[str, int]:
    """Return {state: grower_count} from growers dataset for this crop. Used for digital campaign geo map."""
    gdf = load_growers().copy()
    gdf["_crop"] = gdf["grower_crop_calendar"].apply(
        lambda x: x.get("crop", "") if isinstance(x, dict) else ""
    )
    filtered = gdf[gdf["_crop"].str.lower() == crop.lower()]
    if filtered.empty:
        return {}
    return filtered.groupby("state").size().to_dict()


@st.cache_data
def _load_inv_insights():
    from inventory_analysis import get_inventory_insights
    return get_inventory_insights()


# ── New Campaign dialog ────────────────────────────────────────────────────────
@st.dialog("New Campaign")
def _new_campaign_dialog():
    st.markdown("Give your campaign a name. You'll configure targeting, dates, and channels inside the campaign.")
    name = st.text_input("Campaign Name", placeholder="e.g. Rabi Wheat North India Push",
                         key="dialog_cname")
    col_ok, col_cancel = st.columns(2)
    with col_ok:
        if st.button("Create Campaign", type="primary", use_container_width=True):
            _name = name.strip()
            if not _name:
                st.error("Please enter a campaign name.")
            else:
                stub = {
                    "campaign_name": _name,
                    "stub": True,
                    "segments": [],
                    "generated_at": datetime.utcnow().isoformat(),
                }
                path = save_plan(stub)
                st.session_state.cb_view = path.stem
                st.session_state.targeting_plan = None
                st.session_state.content_variants = None
                st.session_state.current_campaign_path = str(path)
                st.session_state.rep_briefing_result = None
                st.session_state.rep_briefing_rep = None
                st.rerun()
    with col_cancel:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


# ── Nav helpers ───────────────────────────────────────────────────────────────
def _active_item(label: str, meta: str = ""):
    meta_html = (
        f'<div style="font-size:0.68rem;font-weight:400;color:rgba(180,220,190,0.52);'
        f'margin-top:0.06rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'
        f'{meta}</div>'
    ) if meta else ""
    st.markdown(
        f'<div style="background:rgba(255,255,255,0.08);border-radius:6px;'
        f'padding:0.32rem 0.6rem;font-size:0.81rem;font-weight:600;'
        f'color:rgba(220,242,228,0.95);margin-bottom:1px;">{label}{meta_html}</div>',
        unsafe_allow_html=True,
    )


def _nav(label: str, key: str, active: bool, meta: str = "") -> bool:
    if active:
        _active_item(label, meta)
        return False
    return st.button(label, key=key, use_container_width=True)


def _sidebar_section_label(text: str):
    st.markdown(
        f'<p style="font-size:0.62rem;font-weight:500;letter-spacing:0.07em;'
        f'color:rgba(180,220,190,0.32);text-transform:uppercase;margin:12px 0 1px 4px;'
        f'padding:0;">{text}</p>',
        unsafe_allow_html=True,
    )


def _sidebar_divider():
    st.markdown(
        '<div style="border-top:1px solid rgba(255,255,255,0.06);margin:10px 0 4px;"></div>',
        unsafe_allow_html=True,
    )


# ── Overview visual helpers ────────────────────────────────────────────────────
def _render_geo_map(state_grower_map: dict[str, int]):
    active = {s: n for s, n in state_grower_map.items() if s in _STATE_COORDS}
    if not active:
        st.caption("No mapped state coordinates available.")
        return
    lats   = [_STATE_COORDS[s][0] for s in active]
    lons   = [_STATE_COORDS[s][1] for s in active]
    texts  = [f"{s}<br>{n:,} growers" for s, n in active.items()]
    counts = list(active.values())
    sizes  = [max(12, min(40, n // 8)) for n in counts]
    fig = go.Figure()
    fig.add_trace(go.Scattergeo(
        lat=lats, lon=lons, text=texts, mode="markers+text",
        marker=dict(size=sizes, color=_GREEN, opacity=0.85,
                    line=dict(color="#ffffff", width=1.5)),
        textposition="top center",
        textfont=dict(size=8, color="#1d2a22"),
        hoverinfo="text",
    ))
    fig.update_geos(
        scope="asia",
        showland=True,      landcolor="#f0f7f2",
        showcountries=True, countrycolor="#9ab3a0",
        showocean=True,     oceancolor="#e8f0ec",
        showlakes=False,
        center=dict(lat=22, lon=80),
        projection_scale=4.2,
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", geo_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0), height=260, showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _render_timeline(segments: list[dict], reference_date, campaign_end=None):
    ref = pd.Timestamp(reference_date)
    rows = []
    for s in segments[:14]:
        ctx = s.get("stage_context", "")
        m = re.search(r"in (\d+) days", ctx)
        days = int(m.group(1)) if m else None
        finish = ref + timedelta(days=int(days) if days is not None else 30)
        if campaign_end:
            try:
                finish = min(finish, pd.Timestamp(campaign_end))
            except Exception:
                pass
        rows.append({
            "Segment": f"{s.get('crop', '').title()} / {s.get('state', '')}",
            "Start":   ref,
            "Finish":  finish,
            "Crop":    s.get("crop", "unknown").title(),
            "Channel": s.get("channel", ""),
            "Growers": s.get("grower_count", 0),
        })
    if not rows:
        st.caption("No segment data for timeline.")
        return
    df_gn = pd.DataFrame(rows)
    fig = px.timeline(
        df_gn, x_start="Start", x_end="Finish", y="Segment", color="Crop",
        color_discrete_sequence=[_GREEN, _AMBER, "#5aa876", "#1a5c35", "#e8a85b", "#88bb97"],
        hover_data={"Growers": True, "Channel": True},
        labels={"Segment": ""},
    )
    fig.update_layout(**_layout_with(
        height=max(160, len(rows) * 30 + 60),
        xaxis_title=None, yaxis_title=None, showlegend=True,
        legend=dict(orientation="h", y=1.08, x=0, font=dict(size=10)),
        margin=dict(l=10, r=10, t=40, b=10),
    ))
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _render_weather_cards(active_states: list[str]):
    if not active_states:
        return
    _WMO_EMOJI = {
        "Clear sky": "☀️", "Mainly clear": "🌤️", "Partly cloudy": "⛅",
        "Overcast": "☁️", "Fog": "🌫️", "Icy fog": "🌫️",
        "Light drizzle": "🌦️", "Moderate drizzle": "🌧️", "Dense drizzle": "🌧️",
        "Slight rain": "🌧️", "Moderate rain": "🌧️", "Heavy rain": "🌧️",
        "Thunderstorm": "⛈️", "Thunderstorm + hail": "⛈️",
        "Thunderstorm + heavy hail": "⛈️",
        "Slight showers": "🌦️", "Moderate showers": "🌧️", "Violent showers": "⛈️",
    }
    states_to_fetch = active_states[:5]
    with st.spinner("Fetching weather…"):
        weather = _fetch_weather_cached(tuple(sorted(states_to_fetch)))
    cols = st.columns(len(states_to_fetch))
    for state, col in zip(states_to_fetch, cols):
        w = weather.get(state)
        with col:
            if not w:
                st.markdown(
                    f'<div style="border:1px solid #e0ddd7;border-radius:10px;'
                    f'padding:0.65rem 0.7rem;background:#fafaf7;text-align:center;">'
                    f'<div style="font-size:0.68rem;font-weight:700;color:#888;'
                    f'text-transform:uppercase;">{state[:12]}</div>'
                    f'<div style="font-size:0.78rem;color:#bbb;margin-top:0.3rem;">No data</div></div>',
                    unsafe_allow_html=True,
                )
            else:
                emoji = _WMO_EMOJI.get(w["condition"], "🌡️")
                rain_today = (w["forecast_3day"][0]["rain_mm"] if w.get("forecast_3day") else 0) or 0
                is_fallback = w.get("_is_fallback", False)
                rain_badge = (
                    f'<div style="margin-top:0.25rem;"><span style="background:#fff3e0;'
                    f'color:{_AMBER};border-radius:5px;padding:1px 5px;font-size:0.67rem;">'
                    f'🌧 {rain_today:.0f}mm</span></div>'
                    if rain_today > 0 else ""
                )
                fallback_badge = (
                    f'<div style="margin-top:0.2rem;"><span style="background:#fff8e1;'
                    f'color:#9e7a00;border-radius:5px;padding:1px 5px;font-size:0.63rem;">'
                    f'📅 seasonal estimate</span></div>'
                    if is_fallback else ""
                )
                st.markdown(
                    f'<div style="border:1px solid {"#ddd" if is_fallback else "#c8dcd0"};'
                    f'border-radius:10px;padding:0.65rem 0.7rem;'
                    f'background:{"#fdfcf5" if is_fallback else "#f4faf6"};">'
                    f'<div style="font-size:0.65rem;font-weight:700;color:#1a5c35;'
                    f'text-transform:uppercase;letter-spacing:0.04em;">{w["city"]}</div>'
                    f'<div style="font-size:1.35rem;margin:0.15rem 0;">'
                    f'{emoji} {w["temp_c"]:.0f}°C</div>'
                    f'<div style="font-size:0.68rem;color:#4f6157;">{w["condition"]}</div>'
                    f'<div style="font-size:0.66rem;color:#6e7f72;margin-top:0.18rem;">'
                    f'💧{w["humidity_pct"]}% · 💨{w["wind_kmh"]:.0f}km/h</div>'
                    f'{rain_badge}{fallback_badge}</div>',
                    unsafe_allow_html=True,
                )
    live_weather     = [w for w in weather.values() if w and not w.get("_is_fallback")]
    fallback_weather = [w for w in weather.values() if w and     w.get("_is_fallback")]
    sources_used = sorted({w.get("_source", "live") for w in live_weather})
    source_label = " · ".join(s.replace("_", " ").title() for s in sources_used) or "Live"
    if live_weather:
        ages = [
            (datetime.utcnow() - datetime.fromisoformat(w["fetched_at"])).seconds // 60
            for w in live_weather
        ]
        note = f"{source_label} · fetched {min(ages)} min ago · 3-day forecast · no API key required"
        if fallback_weather:
            note += f" · {len(fallback_weather)} state(s) using seasonal estimate (network issue)"
        st.caption(note)
    elif fallback_weather:
        st.caption(
            f"⚠️ Live weather unavailable (Open-Meteo + wttr.in both unreachable) — "
            f"showing seasonal climate estimates for {len(fallback_weather)} state(s). "
            "Disease risk assessment still active using representative data."
        )
    else:
        st.caption("Weather data unavailable — network may be offline.")


def _render_disease_alerts(segs: list[dict]) -> None:
    """Show disease/pest outbreak alerts with AI field advisory and AI-generated images."""
    # ── Collect unique alerts ──────────────────────────────────────────────────
    alerts = []
    seen   = set()
    for seg in segs:
        lvl = seg.get("disease_risk_level", "none")
        if lvl in ("none", None):
            continue
        title = seg.get("disease_alert_title") or ""
        if title in seen:
            continue
        seen.add(title)
        alerts.append({
            "level":   lvl,
            "type":    seg.get("disease_risk_type"),
            "title":   title,
            "body":    seg.get("disease_alert_body", ""),
            "spray":   seg.get("spray_window_ok", True),
            "boost":   seg.get("weather_boost_applied", 0.0),
            "crop":    seg.get("crop", ""),
        })

    spray_blocked = [seg for seg in segs if not seg.get("spray_window_ok", True)]

    if not alerts and not spray_blocked:
        st.caption("✅ No disease or pest outbreak alerts for this campaign's regions.")
        return

    # ── AI field advisory ──────────────────────────────────────────────────────
    if alerts:
        with st.spinner("Generating AI agronomic advisory…"):
            advisory = _disease_ai_overview(json.dumps(alerts))
        if advisory:
            st.markdown(
                f'<div style="background:linear-gradient(135deg,#0d2318 0%,#1a3d28 100%);'
                f'border-radius:12px;padding:0.85rem 1.1rem;margin-bottom:1rem;'
                f'border:1px solid rgba(47,125,76,0.4);">'
                f'<div style="font-size:0.68rem;font-weight:700;color:rgba(212,237,218,0.6);'
                f'text-transform:uppercase;letter-spacing:0.07em;margin-bottom:0.35rem;">'
                f'🤖 AI Agronomic Advisory</div>'
                f'<div style="font-size:0.88rem;color:#d4edda;line-height:1.6;">{advisory}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Alert cards with AI-generated outbreak images ─────────────────────────
    _LEVEL_STYLE = {
        "high":          ("🔴", "#fdecea", "#c0392b", "HIGH RISK"),
        "moderate":      ("🟡", "#fff8e1", _AMBER,    "MODERATE RISK"),
        "low":           ("⚪", "#f5f5f5", "#888",    "LOW / WATCH"),
        "spray_blocked": ("🚫", "#fff3e0", _AMBER,    "SPRAY BLOCKED"),
    }

    for a in sorted(alerts, key=lambda x: {"high": 0, "moderate": 1, "low": 2}.get(x["level"], 3)):
        icon, bg, color, badge = _LEVEL_STYLE.get(a["level"], _LEVEL_STYLE["low"])
        boost_note = (
            f'<span style="font-size:0.72rem;color:{_GREEN};">▲ +{a["boost"]:.0%} receptivity boost applied</span>'
            if a["boost"] > 0 else ""
        )
        risk_type   = a.get("type") or ""
        crop        = a.get("crop", "")
        disease_name = a["title"].split(" Risk")[0].split(" Surge")[0].strip()

        # Left: AI outbreak image  |  Right: alert text
        img_col, txt_col = st.columns([1, 3], gap="small")

        with img_col:
            if risk_type in ("fungal", "pest") and crop:
                with st.spinner(f"Generating {disease_name} image…"):
                    img_src = _disease_outbreak_image(risk_type, crop, disease_name)
                if img_src:
                    st.markdown(
                        f'<img src="{img_src}" style="width:100%;border-radius:10px;'
                        f'border:2px solid {color}33;object-fit:cover;max-height:140px;" />',
                        unsafe_allow_html=True,
                    )
                else:
                    # Emoji fallback when image generation unavailable
                    emoji = "🍄" if risk_type == "fungal" else "🐛"
                    st.markdown(
                        f'<div style="background:{bg};border:2px solid {color}44;border-radius:10px;'
                        f'height:120px;display:flex;align-items:center;justify-content:center;'
                        f'font-size:3rem;">{emoji}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    f'<div style="background:{bg};border:2px solid {color}44;border-radius:10px;'
                    f'height:120px;display:flex;align-items:center;justify-content:center;'
                    f'font-size:2.5rem;">🌿</div>',
                    unsafe_allow_html=True,
                )

        with txt_col:
            st.markdown(
                f'<div style="background:{bg};border-left:4px solid {color};border-radius:0 10px 10px 0;'
                f'padding:0.7rem 1rem;height:100%;box-sizing:border-box;">'
                f'<div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.15rem;">'
                f'<span style="font-size:0.7rem;font-weight:700;color:{color};text-transform:uppercase;'
                f'letter-spacing:0.05em;">{icon} {badge} · {risk_type}</span>'
                f'</div>'
                f'<div style="font-size:0.9rem;font-weight:600;color:#1a2520;margin-bottom:0.2rem;">{a["title"]}</div>'
                f'<div style="font-size:0.82rem;color:#555;line-height:1.5;">{a["body"]}</div>'
                f'<div style="margin-top:0.3rem;">{boost_note}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── District-level hotspot map ─────────────────────────────────────────────
    # Collect all district-level risk entries from segments (distinct entries only)
    all_district_risks: list[dict] = []
    seen_district_keys: set = set()
    for seg in segs:
        for dr in seg.get("district_risk_breakdown", []):
            key = (dr["district"], dr.get("risk_type"), dr.get("risk_level"))
            if key not in seen_district_keys:
                seen_district_keys.add(key)
                all_district_risks.append({**dr, "crop": seg.get("crop", ""), "state": seg.get("state", "")})

    if all_district_risks:
        st.markdown("**District-level Hotspots**")
        st.caption(
            "Each district is scored on its own weather data (not the state average). "
            "Districts shown here have weather conditions that actively favour disease or pest pressure."
        )
        # Build a compact table
        rows_html = ""
        level_color = {"high": "#c0392b", "moderate": _AMBER}
        level_icon  = {"high": "🔴", "moderate": "🟡"}
        for dr in sorted(all_district_risks,
                         key=lambda x: ({"high": 0, "moderate": 1}.get(x["risk_level"], 2),
                                        -x["n_growers"])):
            lc = level_color.get(dr["risk_level"], "#888")
            li = level_icon.get(dr["risk_level"], "⚪")
            src_badge = (
                f'<span style="background:#f0f0f0;color:#777;border-radius:4px;'
                f'padding:0px 4px;font-size:0.62rem;">{dr.get("weather_src","?")}</span>'
            )
            spray_note = (
                '<span style="color:#c07a2b;font-size:0.68rem;"> · 🚫 spray blocked</span>'
                if not dr.get("spray_ok", True) else ""
            )
            rows_html += (
                f'<tr>'
                f'<td style="padding:0.3rem 0.6rem;font-weight:600;color:{lc};">{li} {dr["district"]}</td>'
                f'<td style="padding:0.3rem 0.6rem;color:#555;font-size:0.82rem;">'
                f'{dr["state"]} · {dr["crop"].title()}</td>'
                f'<td style="padding:0.3rem 0.6rem;font-size:0.82rem;color:#333;">'
                f'{dr.get("alert_title","")}{spray_note}</td>'
                f'<td style="padding:0.3rem 0.6rem;text-align:right;font-size:0.8rem;color:#666;">'
                f'{dr["n_growers"]:,} growers &nbsp;{src_badge}</td>'
                f'</tr>'
            )
        st.markdown(
            f'<table style="width:100%;border-collapse:collapse;font-family:\'Space Grotesk\',sans-serif;">'
            f'<thead><tr>'
            f'<th style="padding:0.3rem 0.6rem;text-align:left;font-size:0.7rem;color:#888;'
            f'text-transform:uppercase;letter-spacing:0.05em;border-bottom:1px solid #e0ddd7;">District</th>'
            f'<th style="padding:0.3rem 0.6rem;text-align:left;font-size:0.7rem;color:#888;'
            f'text-transform:uppercase;letter-spacing:0.05em;border-bottom:1px solid #e0ddd7;">Location · Crop</th>'
            f'<th style="padding:0.3rem 0.6rem;text-align:left;font-size:0.7rem;color:#888;'
            f'text-transform:uppercase;letter-spacing:0.05em;border-bottom:1px solid #e0ddd7;">Alert</th>'
            f'<th style="padding:0.3rem 0.6rem;text-align:right;font-size:0.7rem;color:#888;'
            f'text-transform:uppercase;letter-spacing:0.05em;border-bottom:1px solid #e0ddd7;">Growers</th>'
            f'</tr></thead>'
            f'<tbody>{rows_html}</tbody>'
            f'</table>',
            unsafe_allow_html=True,
        )

    # ── Spray window blocked notice ────────────────────────────────────────────
    spray_states = {seg.get("state") for seg in spray_blocked if seg.get("state")}
    if spray_states:
        st.markdown(
            f'<div style="background:#fff3e0;border-left:4px solid {_AMBER};border-radius:0 10px 10px 0;'
            f'padding:0.6rem 1rem;margin-bottom:0.5rem;">'
            f'<span style="font-size:0.7rem;font-weight:700;color:{_AMBER};">🚫 SPRAY WINDOW BLOCKED</span>'
            f'<div style="font-size:0.82rem;color:#555;margin-top:0.2rem;">'
            f'Poor spray conditions (rain / high wind) in: <strong>{", ".join(sorted(spray_states))}</strong>. '
            f'Advise growers to wait for a suitable window before applying. '
            f'Messaging for these segments has been adjusted.</div></div>',
            unsafe_allow_html=True,
        )


def _render_segment_overview(segs: list[dict], reference_date, date_window: dict | None = None):
    active_states = list({s["state"] for s in segs if s.get("state")})
    state_grower: dict[str, int] = {}
    for s in segs:
        state_grower[s["state"]] = state_grower.get(s["state"], 0) + s.get("grower_count", 0)
    campaign_end = date_window.get("end") if date_window else None
    ov1, ov2 = st.columns([3, 2])
    with ov1:
        st.markdown("**Campaign Timeline**")
        st.caption("Each bar is one segment. Width = time until the next critical crop stage. Colour = crop type.")
        _render_timeline(segs, reference_date, campaign_end)
    with ov2:
        st.markdown("**Active States**")
        st.caption("Bubble size = grower count in that state. Hover for exact numbers.")
        _render_geo_map(state_grower)
    if active_states:
        st.markdown("**Field Conditions**")
        _render_weather_cards(active_states)
        st.markdown("**Disease & Pest Outbreak Alerts**")
        st.caption(
            "Derived from real-time weather — high humidity + rain = fungal risk; "
            "hot + dry = pest surge. Alerts boost receptivity scores and adjust campaign messaging."
        )
        _render_disease_alerts(segs)


# ── Segment "why" explanation helper ──────────────────────────────────────────
def _segment_why_html(seg: dict) -> str:
    """
    Build a brief human-readable explanation card for a segment.
    Uses segment metadata only — no extra API call.
    """
    crop    = seg.get("crop", "unknown").title()
    state   = seg.get("state", "unknown")
    channel = "WhatsApp" if seg.get("channel") == "whatsapp" else "rep field visit"
    persona = seg.get("persona", "awareness").replace("_", " ").title()
    product = seg.get("product", "")
    count   = seg.get("grower_count", 0)
    stage   = seg.get("stage_context", "")
    score   = seg.get("avg_score", 0)
    disease_level = seg.get("disease_risk_level", "none")
    disease_title = seg.get("disease_alert_title", "")
    agent_note    = seg.get("agent_note", "")
    selection_reason = seg.get("product_selection_reason", "")
    high_districts   = seg.get("high_risk_districts", [])

    bullets = []

    # Who — group identity
    bullets.append(
        f"<b>{count:,} {crop} growers</b> in {state} with similar growth stage "
        f"and engagement profile, reachable via <b>{channel}</b>."
    )

    # Timing
    if stage:
        bullets.append(
            f"Crop is at <b>{stage}</b> — product intervention now yields highest ROI."
        )

    # Product choice
    if product:
        reason_part = f" ({selection_reason})" if selection_reason else ""
        bullets.append(f"Recommended product: <b>{product}</b>{reason_part}.")

    # Disease / weather signal
    if disease_level in ("high", "moderate"):
        icon = "🔴" if disease_level == "high" else "🟡"
        district_note = (
            f" Hotspot districts: {', '.join(high_districts[:3])}." if high_districts else ""
        )
        bullets.append(
            f"{icon} <b>{disease_level.title()} disease risk</b> — {disease_title}.{district_note} "
            f"Urgency is elevated; messaging emphasises spray timing."
        )

    # Receptivity
    score_pct = int(score * 100)
    if score >= 0.50:
        bullets.append(
            f"Average receptivity is <b>{score_pct}%</b> — growers in this segment "
            f"have strong prior engagement and are likely to convert."
        )
    elif score >= 0.35:
        bullets.append(
            f"Average receptivity is <b>{score_pct}%</b> — moderate engagement; "
            f"personalised messaging can push conversion."
        )

    # AI agent tactical note
    if agent_note:
        bullets.append(f"🤖 <i>AI agent note:</i> {agent_note}")

    items_html = "".join(f"<li>{b}</li>" for b in bullets)
    return (
        f'<div style="background:#f0f7f2;border-left:3px solid #2f7d4c;border-radius:0 10px 10px 0;'
        f'padding:0.75rem 1rem 0.6rem;margin-bottom:0.9rem;">'
        f'<div style="font-size:0.68rem;font-weight:700;color:#1a5c35;text-transform:uppercase;'
        f'letter-spacing:0.07em;margin-bottom:0.4rem;">Why this segment?</div>'
        f'<ul style="margin:0;padding-left:1.2rem;font-size:0.84rem;color:#1d2a22;line-height:1.65;">'
        f'{items_html}</ul></div>'
    )


def _render_segment_cards(segs: list[dict]) -> None:
    """Render each segment as an expander with a 'Why this segment?' explanation."""
    _PERSONA_COLORS = {
        "hot_lead": "#1a5c35", "pre_stage_alert": "#c07a2b",
        "offline_reinforcement": "#5a4b8a", "awareness": "#2f7d4c",
    }
    for s in segs:
        seg_id  = s.get("segment_id", "?")
        crop    = s.get("crop", "").title()
        state   = s.get("state", "")
        persona = s.get("persona", "awareness")
        channel = s.get("channel", "whatsapp")
        product = s.get("product", "—")
        count   = s.get("grower_count", 0)
        score   = s.get("avg_score", 0)
        disease = s.get("disease_risk_level", "none")

        p_color = _PERSONA_COLORS.get(persona, "#2f7d4c")
        ch_lbl  = "📱 Digital" if channel == "whatsapp" else "🤝 Rep Assist"
        d_badge = ""
        if disease == "high":
            d_badge = ' <span style="background:#fdecea;color:#c0392b;border-radius:999px;padding:0.1rem 0.5rem;font-size:0.7rem;font-weight:600;">🔴 High risk</span>'
        elif disease == "moderate":
            d_badge = ' <span style="background:#fff8e1;color:#c07a2b;border-radius:999px;padding:0.1rem 0.5rem;font-size:0.7rem;font-weight:600;">🟡 Moderate risk</span>'

        label = (
            f"{seg_id} · {crop} / {state} · "
            f"{persona.replace('_', ' ').title()} · {count:,} growers · "
            f"{int(score*100)}% score"
        )
        with st.expander(label, expanded=False):
            st.markdown(
                f'<div style="display:flex;gap:0.45rem;flex-wrap:wrap;margin-bottom:0.6rem;">'
                f'<span style="background:{p_color}22;color:{p_color};border-radius:999px;'
                f'padding:0.1rem 0.55rem;font-size:0.72rem;font-weight:600;">'
                f'{persona.replace("_"," ").title()}</span>'
                f'<span style="background:#e8f5e9;color:#1a5c35;border-radius:999px;'
                f'padding:0.1rem 0.55rem;font-size:0.72rem;">{ch_lbl}</span>'
                f'<span style="background:#f0f0f0;color:#555;border-radius:999px;'
                f'padding:0.1rem 0.55rem;font-size:0.72rem;">📦 {product}</span>'
                f'{d_badge}'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.markdown(_segment_why_html(s), unsafe_allow_html=True)


# ── Content rendering helpers ──────────────────────────────────────────────────
def _status_badge(status: str) -> str:
    if status == "success":
        return (f'<span style="background:#e8f5e9;color:{_GREEN};border-radius:5px;'
                f'padding:1px 7px;font-size:0.69rem;font-weight:600;">✓ success</span>')
    if status == "fallback":
        return (f'<span style="background:#fff3e0;color:{_AMBER};border-radius:5px;'
                f'padding:1px 7px;font-size:0.69rem;font-weight:600;">⚠ fallback</span>')
    if status == "skipped":
        return ('<span style="background:#f0f0f0;color:#888;border-radius:5px;'
                'padding:1px 7px;font-size:0.69rem;">— skipped</span>')
    if status == "local":
        return ('<span style="background:#e8f4ff;color:#1a5c8a;border-radius:5px;'
                'padding:1px 7px;font-size:0.69rem;font-weight:600;">🎨 local</span>')
    return ('<span style="background:#f5f5f5;color:#aaa;border-radius:5px;'
            'padding:1px 7px;font-size:0.69rem;">✕ unavailable</span>')


def _content_meta_row(meta: dict | None):
    if not meta:
        return
    status     = meta.get("status", "")
    char_count = meta.get("char_count", 0)
    model      = (meta.get("model") or "").split("/")[-1]
    parts = [_status_badge(status)]
    if char_count:
        parts.append(f'<span style="background:#f0f0f0;color:#555;border-radius:5px;'
                     f'padding:1px 6px;font-size:0.69rem;">{char_count} chars</span>')
    if model:
        parts.append(f'<span style="background:#f0f0f0;color:#777;border-radius:5px;'
                     f'padding:1px 6px;font-size:0.69rem;">{model}</span>')
    st.markdown(
        f'<div style="margin-top:0.35rem;display:flex;gap:0.35rem;flex-wrap:wrap;">'
        + "".join(parts) + "</div>",
        unsafe_allow_html=True,
    )


# ── gTTS language mapping ─────────────────────────────────────────────────────
_GTTS_LANG: dict[str, str] = {
    "Hindi": "hi", "Punjabi": "pa", "Marathi": "mr",
    "Gujarati": "gu", "Kannada": "kn", "Bengali": "bn",
}


@st.cache_data(show_spinner=False)
def _ivr_audio_bytes(text: str, language: str) -> bytes | None:
    """Generate MP3 audio for an IVR/script using gTTS. Returns None if gtts unavailable."""
    try:
        from gtts import gTTS
        lang_code = _GTTS_LANG.get(language, "hi")
        tts = gTTS(text, lang=lang_code, slow=False)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf.read()
    except Exception:
        return None


def _copy_btn(text: str | None, key: str) -> None:
    """Inline clipboard copy button via components.html (no page rerun)."""
    if not text:
        return
    safe = (text.replace("\\", "\\\\").replace("`", "\\`")
                .replace("\n", "\\n").replace("\r", ""))
    components.html(
        f"""<button id="cb_{key}"
  onclick="navigator.clipboard.writeText(`{safe}`);
           var b=document.getElementById('cb_{key}');
           b.textContent='✓ Copied!';b.style.background='#e8f5e9';b.style.color='#1a5c35';
           setTimeout(function(){{b.textContent='📋 Copy';b.style.background='#f5f1e8';b.style.color='#555';}},2000);"
  style="background:#f5f1e8;border:1px solid #ddd8cc;border-radius:6px;padding:4px 10px;
         font-size:12px;color:#555;cursor:pointer;font-family:'Space Grotesk',sans-serif;">
  📋 Copy
</button>""",
        height=36,
    )


def _find_unicode_font() -> str | None:
    """Find a system TTF font that supports Indian scripts (Devanagari, Gujarati, Gurmukhi, Bengali, Kannada)."""
    candidates = [
        Path("C:/Windows/Fonts/Nirmala.ttc"),                                      # Windows 8+ — best coverage
        Path("C:/Windows/Fonts/Nirmala.ttf"),                                      # alternate name
        Path("C:/Windows/Fonts/mangal.ttf"),                                        # Windows XP+ Devanagari
        Path("/usr/share/fonts/truetype/freefont/FreeSans.ttf"),                    # Linux GNU FreeFont
        Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),               # Linux Noto
        Path("/System/Library/Fonts/Supplemental/NotoSansDevanagari-Regular.ttf"), # macOS
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None


def _generate_pdf_bytes(variants: dict, seg_map: dict, campaign_name: str) -> bytes | None:
    """Build a PDF of all generated content with Unicode font support for Indian scripts."""
    try:
        from fpdf import FPDF
    except ImportError:
        return None

    unicode_font = _find_unicode_font()

    def _latin(s: str | None) -> str:
        return (s or "").encode("latin-1", errors="replace").decode("latin-1")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    if unicode_font:
        try:
            pdf.add_font("U", fname=unicode_font)
        except Exception:
            unicode_font = None  # font load failed — fall back to latin

    pdf.add_page()

    # Header banner (Latin only — Helvetica is fine here)
    pdf.set_fill_color(26, 61, 40)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 14, _latin(campaign_name or "Campaign Content"), ln=True, fill=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 7,
             f"Krishi Pracharak  |  Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC",
             ln=True, fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)

    def _write_content(text: str | None):
        t = text or "[Not generated]"
        if unicode_font:
            pdf.set_font("U", size=9)
            pdf.multi_cell(0, 5, t)
        else:
            pdf.set_font("Helvetica", size=9)
            pdf.multi_cell(0, 5, _latin(t))

    for seg_id, content in variants.items():
        seg     = seg_map.get(seg_id, {})
        channel = content.get("channel", "")
        lang    = content.get("language", "")
        persona = content.get("persona", "")
        crop    = seg.get("crop", "").title()
        state   = seg.get("state", "")
        product = seg.get("product", "")
        growers = seg.get("grower_count", 0)

        # Segment banner
        pdf.set_fill_color(47, 125, 76)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7,
                 f"  {seg_id}  |  {_latin(crop)} / {_latin(state)}  |  {persona}  |  {lang}  |  {growers:,} growers",
                 ln=True, fill=True)
        pdf.set_text_color(50, 50, 50)
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 5, f"  Product: {_latin(product)}  |  Channel: {channel}", ln=True)
        pdf.ln(2)

        def _block(title: str, body: str | None):
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(26, 61, 40)
            pdf.cell(0, 5, title, ln=True)
            pdf.set_text_color(30, 30, 30)
            _write_content(body)
            pdf.ln(2)

        if channel == "whatsapp":
            _block("WhatsApp Message:", content.get("whatsapp"))
            _block("SMS:", content.get("sms"))
            _block("IVR Script:", content.get("ivr_script"))
        else:
            _block("Field Visit Script:", content.get("ivr_script"))

        # Embed poster image if saved to disk
        poster_path = content.get("poster_file_path")
        if poster_path and Path(poster_path).exists():
            try:
                pdf.set_font("Helvetica", "B", 9)
                pdf.set_text_color(26, 61, 40)
                pdf.cell(0, 5, "Campaign Poster:", ln=True)
                pdf.image(poster_path, w=80)
                pdf.ln(3)
            except Exception:
                pass

        pdf.set_draw_color(200, 200, 200)
        pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
        pdf.ln(4)

    return bytes(pdf.output())


def _render_streaming_segment(content: dict, seg: dict, seg_id: str) -> None:
    """Compact inline rendering of one segment's content during streaming generation."""
    ch = content.get("channel", "whatsapp")
    _lang = content.get("language", "Hindi")
    if ch == "whatsapp":
        c1, c2 = st.columns(2)
        with c1:
            st.caption("📱 WhatsApp")
            _render_wa_card(content.get("whatsapp"), content.get("whatsapp_meta"),
                            key=f"stw_{seg_id}", poster_content=content)
        with c2:
            st.caption("💬 SMS")
            _render_sms_card(content.get("sms"), content.get("sms_meta"),
                             key=f"sts_{seg_id}")
        _render_ivr_card(content.get("ivr_script"), content.get("ivr_meta"),
                         "IVR Script", language=_lang, key_suffix=f"sti_{seg_id}")
    else:
        _render_ivr_card(content.get("ivr_script"), content.get("ivr_meta"),
                         "Field Visit Script", language=_lang, key_suffix=f"stf_{seg_id}")

    st.caption("🖼 Poster")
    _render_poster_section(content, key=f"stream_{seg_id}")


def _run_streaming_generation(plan: dict, key_prefix: str) -> None:
    """
    Run content generation one segment at a time with live progress UI.
    Shows each segment's content as it's generated, saves to session state, then reruns.
    """
    promoter_b64 = st.session_state.get("promoter_image_b64")
    eligible = [s for s in plan.get("segments", []) if s.get("inventory_ok", True)]
    n = max(len(eligible), 1)

    hdr_slot    = st.empty()
    bar_col, eta_col = st.columns([5, 1])
    progress    = bar_col.progress(0.0)
    eta_slot    = eta_col.empty()
    out_area    = st.container()

    all_variants: dict = {}
    t0 = _time.monotonic()

    for i, (seg_id, seg, content) in enumerate(
        run_content_generation_streaming(plan, promoter_image_b64=promoter_b64)
    ):
        done    = i + 1
        elapsed = _time.monotonic() - t0
        avg     = elapsed / done
        rem     = avg * (n - done)

        all_variants[seg_id] = content
        progress.progress(done / n)

        crop = seg.get("crop", "").title()
        state = seg.get("state", "")
        lang  = content.get("language", "")
        ch    = content.get("channel", "whatsapp")
        ch_icon = "📱" if ch == "whatsapp" else "🤝"

        hdr_slot.markdown(
            f'<div style="font-size:0.88rem;color:#2f7d4c;font-weight:600;">'
            f'{ch_icon} Segment {done}/{n} — {crop} / {state} · {lang}</div>',
            unsafe_allow_html=True,
        )
        if n - done > 0:
            eta_slot.caption(f"~{rem:.0f}s")
        else:
            eta_slot.empty()

        with out_area:
            with st.expander(
                f"{seg_id} · {crop} / {state} · {lang}",
                expanded=(done == 1),
            ):
                _render_streaming_segment(content, seg, f"{key_prefix}_{seg_id}")

    result = {
        "generated_at": datetime.utcnow().isoformat(),
        "total_segments": len(all_variants),
        "variants": all_variants,
    }
    st.session_state.content_variants = result
    _persist_variants(result)

    total_s = _time.monotonic() - t0
    hdr_slot.success(f"✓ {len(all_variants)} segments generated in {total_s:.1f}s")
    progress.progress(1.0)
    eta_slot.empty()
    _time.sleep(1.2)
    st.rerun()


def _safe_html(text: str | None) -> str:
    """Escape text for safe embedding in HTML."""
    if not text:
        return "<em style='color:#aaa;font-style:italic;'>Not available</em>"
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace("\n", "<br>"))


def _poster_img_src(content: dict) -> str | None:
    """Return an <img src=...> value for the poster: data URI (from file) or plain URL."""
    fpath = content.get("poster_file_path")
    if fpath and Path(fpath).exists():
        try:
            img_bytes = Path(fpath).read_bytes()
            b64 = base64.b64encode(img_bytes).decode()
            return f"data:image/png;base64,{b64}"
        except Exception:
            pass
    url = content.get("poster_image_url")
    if url:
        return url
    return None


def _render_poster_section(content: dict, key: str = "poster") -> None:
    """Render the campaign poster at a fixed width with a download button beside it."""
    poster_path = content.get("poster_file_path")
    poster_url  = content.get("poster_image_url")
    has_file    = poster_path and Path(poster_path).exists()

    # Resolve image bytes (needed for download + st.image from URL)
    img_bytes: bytes | None = None
    display_src = None
    if has_file:
        try:
            img_bytes   = Path(poster_path).read_bytes()
            display_src = poster_path
        except Exception:
            pass
    if not display_src and poster_url:
        display_src = poster_url

    if not display_src:
        st.markdown(
            f'<div style="border:1px dashed {_AMBER};border-radius:10px;padding:1.2rem;'
            f'text-align:center;background:#fffaf4;">'
            f'{_status_badge(content.get("poster_status","unknown"))}'
            f'<div style="font-size:0.78rem;color:#999;margin-top:0.4rem;">Poster unavailable</div></div>',
            unsafe_allow_html=True,
        )
        return

    # Image (fixed width ~320 px, not full-width)
    img_col, btn_col = st.columns([3, 1])
    with img_col:
        st.image(display_src, width=320)
    with btn_col:
        # Download button
        fname = Path(poster_path).name if has_file else f"poster_{key}.png"
        if img_bytes:
            st.download_button(
                "⬇ Download",
                data=img_bytes,
                file_name=fname,
                mime="image/png",
                key=f"dl_poster_{key}",
                use_container_width=True,
            )
        st.markdown(_status_badge(content.get("poster_status", "unknown")),
                    unsafe_allow_html=True)
        if has_file:
            st.caption(f"📁 `{fname}`")
        prompt = content.get("poster_prompt_used", "")
        if prompt:
            st.caption(f"Prompt: {prompt[:160]}{'…' if len(prompt) > 160 else ''}")
        gen_at = content.get("poster_generated_at", "")
        if gen_at:
            st.caption(f"Generated {gen_at[:16].replace('T', ' ')} UTC")


def _render_wa_card(text: str | None, meta: dict | None, key: str = "wa",
                    poster_content: dict | None = None):
    """WhatsApp-style chat bubble card. If poster_content is given, shows the
    campaign poster image at the top of the bubble, like a real WA marketing message."""
    if (meta or {}).get("status") == "skipped":
        st.caption("_Not applicable — rep-assist channel_")
        return
    body = _safe_html(text)

    img_src = _poster_img_src(poster_content) if poster_content else None
    img_html = (
        f'<img src="{img_src}" style="width:100%;border-radius:8px 8px 0 0;'
        f'display:block;margin-bottom:0;" />'
        if img_src else ""
    )
    # Adjust bubble padding-top when image present so text sits right below image
    bubble_pt = "0" if img_src else "10px"

    st.markdown(
        f"""<div class="kp-wa-phone">
  <div class="kp-wa-header">
    <div class="kp-wa-avatar">S</div>
    <div><div class="kp-wa-hname">Syngenta India</div>
    <div class="kp-wa-hstatus">online</div></div>
  </div>
  <div class="kp-wa-body">
    <div class="kp-wa-bubble" style="padding-top:{bubble_pt};overflow:hidden;">
      {img_html}
      <div style="padding:{'8px 10px 4px' if img_src else '0 0 4px'};">{body}</div>
      <div class="kp-wa-foot">
        <span class="kp-wa-tick">✓✓</span>
      </div>
    </div>
  </div>
  <div class="kp-wa-footer-bar">
    <div class="kp-wa-footer-input">Type a message…</div>
    <span style="font-size:1rem;color:#075e54;">📎</span>
    <span style="font-size:1rem;color:#075e54;">🎤</span>
  </div>
</div>""",
        unsafe_allow_html=True,
    )
    _copy_btn(text, f"wa_{key}")
    if meta:
        _content_meta_row(meta)


def _render_sms_card(text: str | None, meta: dict | None, key: str = "sms"):
    """iOS-style SMS dark screen mockup with copy button."""
    if (meta or {}).get("status") == "skipped":
        st.caption("_Not applicable — rep-assist channel_")
        return
    body = _safe_html(text)
    st.markdown(
        f"""<div class="kp-sms-phone">
  <div class="kp-sms-screen">
    <div class="kp-sms-topbar">
      <div class="kp-sms-sender">SYNGENTA</div>
      <div class="kp-sms-sublabel">SMS · today</div>
    </div>
    <div class="kp-sms-body">
      <div class="kp-sms-bubble">{body}</div>
      <div class="kp-sms-time">Delivered</div>
    </div>
  </div>
</div>""",
        unsafe_allow_html=True,
    )
    _copy_btn(text, f"sms_{key}")
    if meta:
        _content_meta_row(meta)


def _ivr_waveform() -> str:
    """Return CSS waveform bar HTML string."""
    heights = [8, 14, 22, 30, 36, 26, 18, 32, 24, 14, 28, 20, 36, 22, 16, 30, 26, 18, 34, 24]
    bars = "".join(
        f'<span style="height:{h}px;animation-delay:{i * 0.065:.2f}s;"></span>'
        for i, h in enumerate(heights)
    )
    return f'<div class="kp-ivr-waveform">{bars}</div>'


def _render_ivr_card(text: str | None, meta: dict | None,
                     label: str = "IVR Script",
                     language: str = "Hindi",
                     key_suffix: str = ""):
    """Dark gradient audio script card with TTS speaker + audio download."""
    if (meta or {}).get("status") == "skipped":
        st.caption("_Not applicable — rep-assist channel_")
        return
    icon = "📞" if "IVR" in label else "🤝"
    dur  = "~30 sec spoken" if "IVR" in label else "Field visit guide"
    body = _safe_html(text)
    st.markdown(
        f"""<div class="kp-ivr-card">
  <div class="kp-ivr-header">
    <div class="kp-ivr-icon">{icon}</div>
    <div>
      <div class="kp-ivr-title">{label}</div>
      <div class="kp-ivr-dur">{dur} · {language}</div>
    </div>
  </div>
  {_ivr_waveform()}
  <div class="kp-ivr-script">{body}</div>
</div>""",
        unsafe_allow_html=True,
    )
    if meta:
        _content_meta_row(meta)
    # Audio player + download
    if text:
        with st.spinner("Generating audio…"):
            audio = _ivr_audio_bytes(text, language)
        if audio:
            st.audio(audio, format="audio/mp3")
            st.download_button(
                "⬇ Download Audio (MP3)",
                data=audio,
                file_name=f"ivr_{key_suffix or label.replace(' ', '_').lower()}.mp3",
                mime="audio/mp3",
                key=f"dl_audio_{key_suffix}_{label[:3]}",
            )


def _render_promoter_uploader(key_prefix: str = "promo") -> None:
    """Collapsible promoter image uploader — stores b64 + description in session state."""
    with st.expander("🧑‍🌾 Brand Ambassador / Promoter Image (optional)", expanded=False):
        st.caption(
            "Upload a person's photo to feature them as a brand ambassador in AI-generated posters. "
            "Leave empty to use the default poster style."
        )
        uploaded = st.file_uploader(
            "Promoter photo (JPG or PNG)",
            type=["jpg", "jpeg", "png"],
            key=f"{key_prefix}_upload",
            label_visibility="collapsed",
        )
        if uploaded:
            raw = uploaded.read()
            new_b64 = base64.b64encode(raw).decode()
            if st.session_state.promoter_image_b64 != new_b64:
                st.session_state.promoter_image_b64 = new_b64
                st.session_state.promoter_description = None
            col_img, col_info = st.columns([1, 2])
            with col_img:
                st.image(raw, width=110, caption="Promoter photo")
            with col_info:
                if not st.session_state.promoter_description:
                    with st.spinner("Analyzing promoter image…"):
                        try:
                            desc = describe_promoter(new_b64)
                            st.session_state.promoter_description = desc
                        except Exception:
                            st.session_state.promoter_description = None
                if st.session_state.promoter_description:
                    st.success("Promoter recognized — will be featured in posters.")
                    st.caption(f"**Description:** {st.session_state.promoter_description}")
                else:
                    st.warning("Could not analyze image — proceeding without promoter.")
            if st.button("Clear promoter image", key=f"{key_prefix}_clear"):
                st.session_state.promoter_image_b64 = None
                st.session_state.promoter_description = None
                st.rerun()
        elif st.session_state.promoter_image_b64:
            st.info("Promoter image loaded from this session. Clear it above to remove.")
            if st.button("Clear promoter image", key=f"{key_prefix}_clear2"):
                st.session_state.promoter_image_b64 = None
                st.session_state.promoter_description = None
                st.rerun()


def _render_content_scope(segs: list[dict]):
    """Show visual card grid of segments before content generation."""
    if not segs:
        st.caption("No segments in scope.")
        return

    _CROP_EMOJI = {
        "wheat": "🌾", "rice": "🌾", "paddy": "🌾", "cotton": "🌱",
        "maize": "🌽", "corn": "🌽", "soybean": "🫘", "soya": "🫘",
        "sugarcane": "🍬", "potato": "🥔", "tomato": "🍅",
        "sunflower": "🌻", "mustard": "🌼", "groundnut": "🥜",
    }
    _PERSONA_CFG = {
        "hot_lead":              ("#1a5c35", "#e8f5e9", "🔥 Hot Lead"),
        "pre_stage_alert":       ("#c07a2b", "#fff3e0", "⏰ Pre-Stage"),
        "offline_reinforcement": ("#5a4b8a", "#f0ebff", "🤝 Offline"),
        "awareness":             ("#2f7d4c", "#eef7f1", "📢 Awareness"),
    }
    _CHANNEL_FORMATS = {
        "whatsapp":   "📱 WA · 💬 SMS · 📞 IVR",
        "rep_assist": "🤝 Field Visit Script",
    }

    total_growers = sum(s.get("grower_count", 0) for s in segs)
    wa_segs  = [s for s in segs if s.get("channel") == "whatsapp"]
    rep_segs = [s for s in segs if s.get("channel") == "rep_assist"]

    # Summary banner
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#1a3d28 0%,#2f7d4c 100%);'
        f'border-radius:12px;padding:0.85rem 1.2rem;margin-bottom:0.9rem;'
        f'display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.5rem;">'
        f'<div style="color:#fff;font-size:0.9rem;font-weight:700;">'
        f'{len(segs)} segments &nbsp;·&nbsp; {total_growers:,} growers in scope</div>'
        f'<div style="display:flex;gap:0.6rem;">'
        f'<span style="background:rgba(255,255,255,0.15);color:#d4edda;border-radius:999px;'
        f'padding:0.14rem 0.65rem;font-size:0.73rem;font-weight:600;">📱 {len(wa_segs)} digital</span>'
        f'<span style="background:rgba(192,122,43,0.35);color:#ffd8a0;border-radius:999px;'
        f'padding:0.14rem 0.65rem;font-size:0.73rem;font-weight:600;">🤝 {len(rep_segs)} rep-assist</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # Card grid HTML
    cards = []
    for s in segs:
        crop    = s.get("crop", "").lower()
        state   = s.get("state", "")
        lang    = s.get("language", "")
        persona = s.get("persona", "awareness")
        channel = s.get("channel", "whatsapp")
        product = s.get("product", "—")
        count   = s.get("grower_count", 0)
        score   = s.get("avg_score", 0)

        emoji = _CROP_EMOJI.get(crop, "🌿")
        p_color, p_bg, p_label = _PERSONA_CFG.get(persona, ("#2f7d4c", "#eef7f1", persona.replace("_", " ").title()))
        formats = _CHANNEL_FORMATS.get(channel, channel)
        ch_bg  = "#e8f5e9" if channel == "whatsapp" else "#fff3e0"
        ch_col = "#1a5c35" if channel == "whatsapp" else "#c07a2b"
        ch_lbl = "📱 Digital" if channel == "whatsapp" else "🤝 Rep Assist"
        score_col = "#2f7d4c" if score >= 0.5 else "#c07a2b" if score >= 0.35 else "#888"
        score_pct = int(score * 100)

        cards.append(
            f'<div class="kp-scope-card">'
            f'<div class="kp-scope-top">'
            f'<div class="kp-scope-emoji">{emoji}</div>'
            f'<div><div class="kp-scope-crop">{crop.title()}</div>'
            f'<div class="kp-scope-state">{state} &middot; {lang}</div></div>'
            f'</div>'
            f'<div class="kp-scope-badges">'
            f'<span class="kp-scope-badge" style="background:{p_bg};color:{p_color};">{p_label}</span>'
            f'<span class="kp-scope-badge" style="background:{ch_bg};color:{ch_col};">{ch_lbl}</span>'
            f'<span class="kp-scope-badge" style="background:#f0f0f0;color:#555;">{product}</span>'
            f'</div>'
            f'<div class="kp-scope-foot">'
            f'<div><div class="kp-scope-growers">{count:,}</div>'
            f'<div class="kp-scope-glabel">growers</div></div>'
            f'<div style="text-align:center;">'
            f'<div style="font-size:0.88rem;font-weight:700;color:{score_col};">{score_pct}%</div>'
            f'<div class="kp-scope-glabel">score</div></div>'
            f'<div class="kp-scope-formats">{formats}</div>'
            f'</div>'
            f'</div>'
        )
    st.markdown(
        '<div class="kp-scope-grid">' + "".join(cards) + '</div>',
        unsafe_allow_html=True,
    )


def _render_content_variants():
    plan     = st.session_state.targeting_plan
    variants = st.session_state.content_variants
    if not variants:
        return
    segs    = plan.get("segments", []) if plan else []
    seg_map = {s["segment_id"]: s for s in segs}
    all_v   = variants.get("variants", {})
    total   = len(all_v)
    fallback_count = sum(
        1 for v in all_v.values()
        if any(
            (v.get(mk) or {}).get("status") == "fallback"
            for mk in ["whatsapp_meta", "sms_meta", "ivr_meta"]
        )
    )

    # ── Summary bar + PDF download ─────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns([2, 2, 2, 2, 3])
    m1.metric("Segments", total,
              help="Number of targeting segments for which content was generated")
    m2.metric("Full Success", total - fallback_count,
              help="Segments where all content (WhatsApp, SMS, IVR) was AI-generated successfully")
    m3.metric("Partial Fallback", fallback_count,
              delta_color="inverse" if fallback_count else "off",
              help="Segments that fell back to rule-based templates because AI generation failed")
    m4.metric("Generated", variants.get("generated_at", "")[:10] or "—",
              help="Date this content batch was generated")
    with m5:
        camp_name = (plan or {}).get("campaign_name", "campaign")
        pdf_bytes = _generate_pdf_bytes(all_v, seg_map, camp_name)
        if pdf_bytes:
            st.download_button(
                "⬇ Download All as PDF",
                data=pdf_bytes,
                file_name=f"{camp_name.replace(' ', '_')}_content.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.caption("_(install fpdf2 for PDF export)_")
    st.divider()

    # ── Per-segment content cards ───────────────────────────────────────────────
    for seg_id, content in all_v.items():
        seg     = seg_map.get(seg_id, {})
        channel = content.get("channel", "whatsapp")
        persona = content.get("persona", "")
        lang    = content.get("language", "")
        crop    = seg.get("crop", "").title()
        state   = seg.get("state", "")

        persona_color = {
            "hot_lead": "#1a5c35", "pre_stage_alert": "#c07a2b",
            "offline_reinforcement": "#5a4b8a", "awareness": "#2f7d4c",
        }.get(persona, "#2f7d4c")

        header_html = (
            f'<div style="display:flex;align-items:center;gap:0.6rem;flex-wrap:wrap;">'
            f'<span style="font-weight:700;font-size:0.9rem;color:#1d2a22;">{seg_id}</span>'
            f'<span style="color:#666;font-size:0.82rem;">{crop} / {state}</span>'
            f'<span style="background:{persona_color}22;color:{persona_color};border-radius:999px;'
            f'padding:0.1rem 0.55rem;font-size:0.72rem;font-weight:600;">{persona}</span>'
            f'<span style="background:#f0f0f0;color:#555;border-radius:999px;'
            f'padding:0.1rem 0.55rem;font-size:0.72rem;">{lang}</span>'
            f'<span style="background:#e8f5e9;color:#2f7d4c;border-radius:999px;'
            f'padding:0.1rem 0.55rem;font-size:0.72rem;">{"📱 WhatsApp" if channel == "whatsapp" else "🤝 Rep Assist"}</span>'
            f'</div>'
        )

        with st.expander(f"{seg_id} · {crop} / {state} · {persona} · {lang}", expanded=False):
            st.markdown(header_html, unsafe_allow_html=True)
            st.markdown(_segment_why_html(seg), unsafe_allow_html=True)

            _lang = content.get("language", "Hindi")
            if channel == "whatsapp":
                col_wa, col_sms = st.columns(2, gap="medium")
                with col_wa:
                    st.markdown(
                        '<div style="font-size:0.7rem;font-weight:700;color:#1a5c35;'
                        'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.4rem;">'
                        '📱 WhatsApp</div>', unsafe_allow_html=True)
                    _render_wa_card(content.get("whatsapp"), content.get("whatsapp_meta"),
                                    key=seg_id, poster_content=content)
                with col_sms:
                    st.markdown(
                        '<div style="font-size:0.7rem;font-weight:700;color:#1a5c35;'
                        'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.4rem;">'
                        '💬 SMS</div>', unsafe_allow_html=True)
                    _render_sms_card(content.get("sms"), content.get("sms_meta"),
                                     key=seg_id)
                st.markdown("<div style='margin-top:0.6rem;'></div>", unsafe_allow_html=True)
                _render_ivr_card(content.get("ivr_script"), content.get("ivr_meta"),
                                 "IVR Script", language=_lang, key_suffix=seg_id)
            else:
                _render_ivr_card(content.get("ivr_script"), content.get("ivr_meta"),
                                 "Field Visit Script", language=_lang, key_suffix=seg_id)

            # ── Outbreak alert image (only for disease-affected segments) ─────
            _risk_type  = seg.get("disease_risk_type")
            _risk_level = seg.get("disease_risk_level", "none")
            _alert_title = seg.get("disease_alert_title") or ""
            if _risk_type in ("fungal", "pest") and _risk_level in ("high", "moderate"):
                _disease_name = _alert_title.split(" Risk")[0].split(" Surge")[0].strip()
                _seg_crop = seg.get("crop", "")
                st.markdown("")
                st.markdown(
                    '<div style="font-size:0.72rem;font-weight:700;color:#c0392b;'
                    'text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.5rem;">'
                    '🦠 Outbreak Alert Image</div>',
                    unsafe_allow_html=True,
                )
                with st.spinner(f"Loading {_disease_name} image…"):
                    _outbreak_img = _disease_outbreak_image(_risk_type, _seg_crop, _disease_name)
                if _outbreak_img:
                    _level_color = "#c0392b" if _risk_level == "high" else "#c07a2b"
                    st.markdown(
                        f'<div style="border:2px solid {_level_color}33;border-radius:12px;'
                        f'overflow:hidden;margin-bottom:0.4rem;">'
                        f'<img src="{_outbreak_img}" style="width:100%;display:block;'
                        f'max-height:260px;object-fit:cover;" />'
                        f'</div>'
                        f'<div style="font-size:0.75rem;color:#888;margin-bottom:0.3rem;">'
                        f'AI-generated field reference — {_disease_name} on {_seg_crop}. '
                        f'Attach this to the WhatsApp message for visual context.</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption(f"Outbreak image unavailable for {_disease_name}.")

            # Poster
            st.markdown("")
            st.markdown(
                '<div style="font-size:0.72rem;font-weight:700;color:#1a5c35;'
                'text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.5rem;">'
                '🖼 Poster</div>',
                unsafe_allow_html=True,
            )
            _render_poster_section(content, key=seg_id)

    st.divider()
    d1, d2 = st.columns(2)
    with d1:
        st.download_button("⬇ Targeting Plan",
                           json.dumps(plan, indent=2, ensure_ascii=False),
                           "targeting_plan.json", "application/json")
    with d2:
        st.download_button("⬇ Content Variants",
                           json.dumps(variants, indent=2, ensure_ascii=False),
                           "content_variants.json", "application/json")


# ── Receptivity tab ───────────────────────────────────────────────────────────
def _render_receptivity(plan: dict | None = None):
    if not plan or not plan.get("segments"):
        st.info("Run targeting first to see the receptivity breakdown for this campaign.")
        return

    segs    = [s for s in plan["segments"] if s.get("inventory_ok", True)]
    qs      = plan.get("quality_summary", {})
    total   = qs.get("total_growers", plan.get("total_growers_scored", 0))
    eligible = plan.get("total_eligible_pre_oos", 0)
    oos_blocked = qs.get("oos_blocked_growers", 0)
    targeted = sum(s["grower_count"] for s in segs)
    below   = qs.get("below_threshold", total - eligible)

    # ── Targeting funnel ──────────────────────────────────────────────────
    st.markdown("### How this campaign's audience was selected")
    st.caption(
        "Every grower in the dataset was scored. Only those above the 0.30 receptivity "
        "threshold and with product in stock made it into a segment."
    )

    f1, f2, f3, f4 = st.columns(4)
    f1.metric("Growers scored", f"{total:,}",
              help="All growers matching this campaign's crop and state filters")
    f2.metric("Above threshold", f"{eligible:,}",
              delta=f"-{below:,} below 0.30",
              delta_color="off",
              help="Receptivity score ≥ 0.30 — the AI's minimum bar for campaign eligibility")
    f3.metric("OOS blocked", f"{oos_blocked:,}",
              delta=f"-{oos_blocked:,} inventory risk",
              delta_color="off",
              help="Product out-of-stock in the grower's nearest retailer territory")
    f4.metric("In campaign", f"{targeted:,}",
              delta=f"across {len(segs)} segments",
              delta_color="off",
              help="Growers actually included in a campaign segment")

    st.divider()

    # ── Segment breakdown ─────────────────────────────────────────────────
    st.markdown("### Segment breakdown")
    st.caption(
        "Each bar is one campaign segment — the height shows grower count, "
        "the colour shows average receptivity score. Higher score = more receptive audience."
    )

    seg_df = pd.DataFrame([{
        "Segment": s["segment_id"],
        "Label":   f"{s['crop'].title()} / {s['state']}",
        "Growers": s["grower_count"],
        "Avg Score": s.get("avg_score", 0),
        "Persona": s.get("persona", "").replace("_", " ").title(),
        "Channel": s.get("channel", ""),
    } for s in segs])

    fig_seg = px.bar(
        seg_df.sort_values("Avg Score", ascending=False),
        x="Label", y="Growers",
        color="Avg Score",
        color_continuous_scale=[[0, "#d6ead9"], [1, "#1a5c35"]],
        hover_data={"Persona": True, "Channel": True, "Avg Score": ":.3f"},
        text="Growers",
    )
    fig_seg.update_traces(textposition="outside")
    fig_seg.update_layout(**_layout_with(
        xaxis_title=None, yaxis_title="Growers in segment",
        coloraxis_colorbar=dict(title="Avg score"),
        xaxis_tickangle=-25,
    ))
    st.plotly_chart(fig_seg, use_container_width=True)

    # ── What drove selection ───────────────────────────────────────────────
    st.divider()
    st.markdown("### What drove grower selection")
    st.caption(
        "The receptivity score is built from 7 signals. "
        "The two biggest are **crop timing urgency** (is a critical growth stage approaching?) "
        "and **state engagement history** (do farmers in this state historically respond?). "
        "Product scan and past WhatsApp engagement are bonus signals — they push already-eligible "
        "growers higher but aren't required."
    )

    _SIGNAL_EXPLAIN = [
        ("Crop Timing Urgency",        "0–0.25", "How close is the next critical crop stage? The closer, the higher.",   _GREEN),
        ("State Engagement History",   "0.07–0.15", "Historical WA response rates by state from past campaigns.",        "#5aa876"),
        ("Farm Size",                  "0.06–0.10", "Smaller farms (1–2 ac) tend to engage more than large holdings.",   "#88bb97"),
        ("Product Scan (hot-lead)",    "+0.06",  "Grower previously scanned this product — already product-aware.",      _AMBER),
        ("Past WA Engagement",         "+0.05",  "Grower opened a previous WhatsApp campaign.",                          "#c07a2b"),
        ("Cross-Channel Fatigue",      "−0.08",  "Grower attended offline event AND scanned — risk of over-contact.",    "#e05252"),
        ("Gender Signal",              "+0.02",  "Female farmers show slightly higher response rates in this dataset.",  "#6b7280"),
    ]

    for label, weight, explain, color in _SIGNAL_EXPLAIN:
        st.markdown(
            f'<div style="display:flex;align-items:baseline;gap:0.6rem;margin-bottom:0.4rem;">'
            f'<span style="width:10px;height:10px;border-radius:50%;background:{color};'
            f'flex-shrink:0;display:inline-block;margin-top:3px;"></span>'
            f'<span style="font-size:0.88rem;font-weight:600;color:#1a2520;min-width:220px;">'
            f'{label}</span>'
            f'<span style="font-size:0.78rem;color:{color};font-weight:700;min-width:60px;">'
            f'{weight}</span>'
            f'<span style="font-size:0.82rem;color:#555;">{explain}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Data quality note ─────────────────────────────────────────────────
    missing_cal = qs.get("missing_calendar", 0)
    if missing_cal > 0:
        st.divider()
        st.warning(
            f"**Data quality note:** {missing_cal:,} growers had no crop calendar — "
            "timing urgency defaulted to 0.25 (moderate) for them. "
            "Scores for these growers are less reliable."
        )


# ── Rep Briefing tab ───────────────────────────────────────────────────────────
def _action_card(action: dict) -> None:
    """Render one priority action as a colour-coded card."""
    atype = action["type"]
    rank  = action["rank"]

    if atype == "rep_assist_campaign":
        accent = _GREEN
        icon   = "🌾"
        label  = "Assisted Campaign"
        title  = f"{action.get('crop', '').title()} — {action.get('persona', '').replace('_', ' ').title()}"
        lines  = [
            f"**Product:** {action.get('product')}",
            f"**Growers to visit:** {action.get('grower_count')}",
            f"**Tehsils:** {', '.join(action.get('tehsils', []))}",
        ]
    elif atype == "restock_alert":
        accent = _AMBER
        icon   = "📦"
        label  = "Restock Alert"
        wks    = action.get("weeks_until_oos", "?")
        title  = f"{action.get('sku')} — {wks} week{'s' if wks != 1 else ''} until OOS"
        lines  = [
            f"**Avg stock:** {action.get('avg_stock')} units",
            f"**Depletion trend:** {action.get('trend_slope')} units/week",
        ]
    else:
        accent = "#6b7280"
        icon   = "📍"
        label  = "Visit Gap"
        days   = action.get("days_since_visit", "?")
        title  = f"{action.get('tehsil')} — {days} days since last visit"
        lines  = []

    st.markdown(
        f'<div style="border-left:4px solid {accent};background:#fafaf8;'
        f'border-radius:0 10px 10px 0;padding:0.7rem 1rem;margin-bottom:0.5rem;">'
        f'<div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.2rem;">'
        f'<span style="background:{accent};color:#fff;border-radius:50%;width:22px;height:22px;'
        f'display:inline-flex;align-items:center;justify-content:center;font-size:0.72rem;'
        f'font-weight:700;flex-shrink:0;">#{rank}</span>'
        f'<span style="font-size:0.7rem;font-weight:700;color:{accent};text-transform:uppercase;'
        f'letter-spacing:0.05em;">{icon} {label}</span></div>'
        f'<div style="font-size:0.9rem;font-weight:600;color:#1a2520;margin-bottom:0.2rem;">'
        f'{title}</div>'
        + "".join(
            f'<div style="font-size:0.82rem;color:#555;margin-top:0.1rem;">{l}</div>'
            for l in lines
        )
        + "</div>",
        unsafe_allow_html=True,
    )


def _render_rep_briefing_tab(plan: dict | None = None, campaign_path: str | None = None):
    _INV_LAYOUT = dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=30, b=10),
        font=dict(color="#1d2a22", family="Space Grotesk"),
    )

    all_reps = load_reps()

    # Require a generated plan to filter reps meaningfully
    if not plan or not plan.get("segments"):
        st.markdown(
            '<div style="border:1px dashed #c8c0b0;border-radius:16px;padding:3rem 2rem;'
            'text-align:center;background:#fafaf7;color:#888;">'
            '<div style="font-size:1.6rem;margin-bottom:0.6rem;">👥</div>'
            '<div style="font-weight:600;margin-bottom:0.4rem;color:#555;">No targeting plan yet</div>'
            '<div style="font-size:0.88rem;">Generate the targeting plan first — the rep list '
            'will then show only the field reps whose territories cover this campaign\'s growers.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # Filter to reps whose state appears in this campaign's segments
    campaign_states = {s["state"] for s in plan["segments"] if s.get("state")}
    reps = all_reps[all_reps["state"].isin(campaign_states)].copy()
    if reps.empty:
        st.warning(
            f"No reps found for campaign states: {', '.join(sorted(campaign_states))}. "
            "Showing all reps as fallback."
        )
        reps = all_reps

    rep_ids = sorted(reps["rep_id"].tolist())
    if not rep_ids:
        st.info("No reps found for this campaign's states.")
        return

    left, main = st.columns([1, 3], gap="large")
    with left:
        st.markdown("#### Select Rep")
        st.caption(
            f"Showing {len(rep_ids)} rep{'s' if len(rep_ids) != 1 else ''} "
            f"covering: {', '.join(sorted(campaign_states))}"
        )
        rep_id = st.selectbox("Rep ID", rep_ids, key="rb_rep_select", label_visibility="collapsed")
        rep_row_preview = reps[reps["rep_id"] == rep_id].iloc[0]
        st.caption(
            f"**Territory:** {rep_row_preview['territory_name']}  \n"
            f"**State:** {rep_row_preview['state']}  \n"
            f"**District:** {rep_row_preview['district']}"
        )
        reference_date = st.date_input("Reference Date", value=date.today(),
                                       key="rb_ref_date")
        st.markdown("")
        gen_clicked = st.button("Generate Briefing", type="primary",
                                use_container_width=True, key="rb_gen_btn")
        st.caption("The AI analyses stock risk, visit gaps, and offline growers for this territory.")

    if gen_clicked:
        with st.spinner(f"Analysing territory for {rep_id}…"):
            result = run_rep_briefing(rep_id, reference_date,
                                      targeting_plan_path=campaign_path)
            st.session_state.rep_briefing_result = result.get(rep_id, {})
            st.session_state.rep_briefing_rep    = rep_id
        st.rerun()

    with main:
        if not st.session_state.rep_briefing_result or st.session_state.rep_briefing_rep != rep_id:
            st.markdown(
                '<div style="border:1px dashed #c8c0b0;border-radius:16px;padding:3rem 2rem;'
                'text-align:center;background:#fafaf7;color:#888;">'
                '<div style="font-size:2.5rem;margin-bottom:0.8rem;">🗺️</div>'
                '<div style="font-size:1rem;font-weight:600;color:#555;">Select a rep and click '
                '<strong>Generate Briefing</strong></div>'
                '<div style="font-size:0.85rem;margin-top:0.4rem;">Takes ~10 seconds. '
                'Covers stock risk, visit gaps, and offline growers.</div></div>',
                unsafe_allow_html=True,
            )
        else:
            briefing = st.session_state.rep_briefing_result
            rep_row  = reps[reps["rep_id"] == rep_id].iloc[0]
            actions  = briefing.get("priority_actions", [])
            restock  = [a for a in actions if a["type"] == "restock_alert"]
            gap      = [a for a in actions if a["type"] == "visit_gap"]
            campaign_actions = [a for a in actions if a["type"] == "rep_assist_campaign"]
            n_offline = briefing.get("offline_growers_count", 0)

            # ── Header ────────────────────────────────────────────────────
            st.markdown(
                f'<div style="background:linear-gradient(135deg,#1a3d28,#2f7d4c);'
                f'border-radius:12px;padding:1rem 1.4rem;margin-bottom:1rem;">'
                f'<div style="color:#fff;font-size:1.1rem;font-weight:700;">'
                f'{rep_id} — {rep_row["territory_name"]}</div>'
                f'<div style="color:rgba(255,255,255,0.72);font-size:0.85rem;margin-top:0.2rem;">'
                f'{rep_row["state"]} · {rep_row["district"]}</div></div>',
                unsafe_allow_html=True,
            )

            # ── Snapshot metrics ──────────────────────────────────────────
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Campaign Actions", len(campaign_actions),
                      help="Grower segments this rep should visit in-person for assisted sales")
            m2.metric("Restock Alerts", len(restock),
                      help="Products approaching out-of-stock in this territory")
            m3.metric("Visit Gaps", len(gap),
                      help="Tehsils that haven't had a rep visit in over 30 days")
            m4.metric("Offline Growers", n_offline,
                      help="Non-smartphone growers who can't receive WhatsApp — need direct visit")
            st.divider()

            # ── AI Briefing ───────────────────────────────────────────────
            st.markdown("### This Week's Field Briefing")
            st.markdown(
                f'<div style="background:#f0f7f2;border-left:4px solid {_GREEN};'
                f'border-radius:0 12px 12px 0;padding:1rem 1.2rem;'
                f'font-size:0.92rem;line-height:1.7;color:#1a2520;">'
                f'{_safe_html(briefing.get("briefing_text", "—")).replace("<br>", "<br>")}'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.divider()

            # ── Priority Actions ──────────────────────────────────────────
            st.markdown("### Priority Actions")
            if not actions:
                st.caption("No priority actions generated.")
            else:
                # Group by type with a sub-heading each
                for group_label, group_icon, group_list in [
                    ("Campaign Visits", "🌾", campaign_actions),
                    ("Restock Alerts", "📦", restock),
                    ("Visit Gaps", "📍", gap),
                ]:
                    if not group_list:
                        continue
                    st.markdown(
                        f'<div style="font-size:0.78rem;font-weight:700;color:#555;'
                        f'text-transform:uppercase;letter-spacing:0.06em;'
                        f'margin:0.8rem 0 0.3rem;">{group_icon} {group_label}</div>',
                        unsafe_allow_html=True,
                    )
                    for action in group_list:
                        _action_card(action)

            # ── Offline Growers ───────────────────────────────────────────
            if n_offline > 0:
                st.divider()
                st.markdown(f"### Offline Growers — {n_offline} need direct visit")
                st.caption(
                    "These growers don't have smartphones. They won't receive WhatsApp or SMS. "
                    "Your visit IS their campaign touchpoint."
                )
                growers     = load_growers()
                tehsil_list = rep_row["tehsil_list"]
                offline = growers[
                    growers["tehsil"].isin(tehsil_list) & (growers["device_type"] != "smartphone")
                ].copy()
                offline["crop"] = offline["grower_crop_calendar"].apply(
                    lambda x: x.get("crop", "-") if isinstance(x, dict) else "-"
                )
                # Summary badges by tehsil
                tehsil_counts = offline["tehsil"].value_counts()
                badges = " ".join(
                    f'<span style="background:#f0f7f2;border:1px solid {_GREEN};'
                    f'border-radius:6px;padding:2px 10px;color:{_GREEN};font-size:0.82rem;'
                    f'margin-right:4px;">{t} ({n})</span>'
                    for t, n in tehsil_counts.items()
                )
                st.markdown(
                    f'<div style="margin-bottom:0.6rem;">{badges}</div>',
                    unsafe_allow_html=True,
                )
                st.dataframe(
                    offline[["grower_id", "tehsil", "crop", "device_type",
                              "grower_farm_size"]].rename(columns={
                        "grower_id": "Grower", "tehsil": "Tehsil", "crop": "Crop",
                        "device_type": "Device", "grower_farm_size": "Farm (ac)",
                    }),
                    use_container_width=True, hide_index=True,
                )

    # ── Inventory Intelligence ─────────────────────────────────────────────────
    st.divider()
    with st.expander("📦 Territory Inventory Intelligence", expanded=False):
        st.caption(
            "Stock health and OOS risk across retailers. "
            "Use this to pre-empt restock conversations before they become lost sales."
        )
        try:
            inv = _load_inv_insights()
        except Exception as e:
            st.warning(f"Inventory data unavailable: {e}")
            return
        _PALETTE = ["#2f7d4c", "#5aa876", "#88bb97", "#c07a2b", "#e8a85b", "#1a5c35"]

        mi1, mi2, mi3, mi4 = st.columns(4)
        mi1.metric("SKUs Tracked",       inv["unique_skus"],
                   help="Distinct product SKUs with inventory data in this territory")
        mi2.metric("Retailers Covered",  f"{inv['unique_retailers']:,}",
                   help="Retail outlets with at least one stock record in the dataset")
        mi3.metric("Total OOS Events",   f"{inv['total_oos_events']:,}",
                   help="Total weekly out-of-stock incidents across all SKUs and retailers")
        mi4.metric("Retailers with OOS", f"{inv['retailers_with_any_oos']:,}",
                   help="Retailers that had at least one out-of-stock event — indicates supply chain gaps")

        at_risk_set = set(inv["at_risk_skus"])
        if at_risk_set:
            badges = " ".join(
                f'<span style="background:#fff3e0;border:1px solid {_AMBER};'
                f'border-radius:6px;padding:2px 10px;color:{_AMBER};font-size:0.82rem;'
                f'margin-right:4px;">⚠️ {s}</span>' for s in at_risk_set
            )
            st.markdown(
                f'<div style="margin:0.4rem 0 0.8rem;"><strong>At-risk SKUs:</strong> {badges}</div>',
                unsafe_allow_html=True,
            )

        cl, cr = st.columns(2, gap="medium")
        with cl:
            st.markdown("**OOS Rate by SKU** — how often each product was out of stock")
            st.caption("Amber bars = at-risk SKUs. Dashed line = average OOS rate. Higher = more supply disruptions.")
            oos_rate = inv["oos_rate_by_sku"]
            oos_df   = (pd.DataFrame({"sku": list(oos_rate.keys()),
                                      "oos_rate": list(oos_rate.values())})
                        .sort_values("oos_rate", ascending=True))
            mean_oos = float(pd.Series(list(oos_rate.values())).mean())
            fig_oos  = go.Figure()
            fig_oos.add_trace(go.Bar(
                x=oos_df["oos_rate"], y=oos_df["sku"], orientation="h",
                marker_color=["#c07a2b" if s in at_risk_set else _GREEN for s in oos_df["sku"]],
            ))
            fig_oos.add_vline(x=mean_oos, line_dash="dash", line_color="#555",
                              annotation_text=f"Avg {mean_oos:.1f}%",
                              annotation_font_color="#555")
            fig_oos.update_layout(**_INV_LAYOUT, xaxis_title="OOS Rate (%)",
                                  yaxis_title=None, showlegend=False)
            st.plotly_chart(fig_oos, use_container_width=True, config={"displayModeBar": False})

        with cr:
            st.markdown("**Weekly stock trend** — depletion over the last 8 weeks")
            st.caption("Falling lines mean stock is being depleted. A steep drop approaching zero signals an OOS risk.")
            sku_weekly = inv["sku_weekly_avg"]
            fig_trend  = go.Figure()
            for idx, (sku, week_data) in enumerate(sku_weekly.items()):
                wks = sorted(week_data.keys())
                fig_trend.add_trace(go.Scatter(
                    x=wks, y=[week_data[w] for w in wks],
                    mode="lines+markers", name=sku,
                    line=dict(color=_PALETTE[idx % len(_PALETTE)], width=2),
                    marker=dict(size=5),
                ))
            inv_lt = dict(_INV_LAYOUT)
            inv_lt.update(dict(
                yaxis_title="Avg Qty (units)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=10)),
                margin=dict(l=10, r=10, t=40, b=10),
            ))
            fig_trend.update_layout(**inv_lt)
            st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False})

        with st.expander("🔥 OOS Risk Heatmap — SKU × Week", expanded=False):
            st.caption("Red cells = high out-of-stock rate that week. Use this to spot recurring problem SKUs and problem periods before they hit the field.")
            heatmap_data = inv["oos_heatmap"]
            skus_hm      = list(heatmap_data.keys())
            all_hm_weeks = sorted({w for sd in heatmap_data.values() for w in sd.keys()})
            z_matrix     = [[heatmap_data[sku].get(wk, 0.0) for wk in all_hm_weeks]
                            for sku in skus_hm]
            fig_hm = go.Figure(go.Heatmap(
                z=z_matrix, x=all_hm_weeks, y=skus_hm,
                colorscale=[[0, "#f0f7f2"], [0.5, "#e8a85b"], [1, "#c0392b"]],
                colorbar=dict(title="OOS %", ticksuffix="%"),
                hoverongaps=False,
                hovertemplate="SKU: %{y}<br>Week: %{x}<br>OOS Rate: %{z:.1f}%<extra></extra>",
            ))
            _hm_layout = {**_INV_LAYOUT, "margin": dict(l=10, r=10, t=20, b=10)}
            fig_hm.update_layout(**_hm_layout,
                                 xaxis_title="Week End Date", yaxis_title=None)
            st.plotly_chart(fig_hm, use_container_width=True, config={"displayModeBar": False})


# ═══════════════════════════════════════════════════════════════════════════════
# DATA
# ═══════════════════════════════════════════════════════════════════════════════
funnel_df   = load_digital_funnel()
saved_camps = _load_saved()

digital = []
for (cid, crop, product), grp in funnel_df.groupby(
    ["campaign_id", "campaign_crop", "campaign_product"], sort=False
):
    grp = grp.sort_values("week_start_date")
    imp = grp["social_post_impression"].sum()
    vis = grp["landing_page_visits"].sum()
    ld  = grp["lead_form_submission"].sum()
    digital.append(dict(
        id=cid, crop=crop, product=product,
        impressions=imp, visits=vis, leads=ld,
        visit_rate=vis / imp * 100 if imp else 0,
        lead_rate=ld / vis * 100 if vis else 0,
        start=str(grp["week_start_date"].min())[:10],
        end=str(grp["week_start_date"].max())[:10],
        weeks=grp["week_start_date"].tolist(),
        weekly_imp=grp["social_post_impression"].tolist(),
    ))


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    # ── New Campaign — primary action at the top ───────────────────────────────
    st.markdown('<div style="padding:2px 0 4px;"></div>', unsafe_allow_html=True)
    if st.button("＋  New Campaign", key="sb_new", type="primary", use_container_width=True):
        _new_campaign_dialog()

    # ── AI / saved campaigns ───────────────────────────────────────────────────
    if saved_camps:
        _sidebar_divider()
        for c in saved_camps:
            label     = c.get("campaign_name") or c["_filename"].replace(".json", "")
            is_active = st.session_state.cb_view == c["_id"]
            seg_count = len(c.get("segments") or [])
            gen_at    = (c.get("generated_at") or "")[:10]
            is_stub   = c.get("stub", False)
            meta      = "⚙ Draft" if is_stub else " · ".join(filter(None, [
                f"{seg_count} seg" if seg_count else "",
                gen_at,
            ]))

            if st.session_state.confirm_delete_id == c["_id"]:
                # Confirmation block — replaces normal item row
                st.markdown(
                    f'<div style="background:rgba(160,40,40,0.14);border:1px solid rgba(200,80,80,0.28);'
                    f'border-radius:8px;padding:0.38rem 0.65rem 0.28rem;margin:2px 0;">'
                    f'<div style="font-size:0.74rem;color:rgba(255,150,150,0.9);font-weight:600;">'
                    f'Delete "{label[:22]}{"…" if len(label) > 22 else ""}"?</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                cc1, cc2 = st.columns(2)
                with cc1:
                    if st.button("Delete", key=f"delyes_{c['_id']}", use_container_width=True):
                        delete_campaign(c["_path"])
                        st.session_state.confirm_delete_id = None
                        if st.session_state.cb_view == c["_id"]:
                            st.session_state.cb_view = "welcome"
                            st.session_state.targeting_plan = None
                            st.session_state.content_variants = None
                            st.session_state.current_campaign_path = None
                            st.session_state.rep_briefing_result = None
                            st.session_state.rep_briefing_rep    = None
                        st.rerun()
                with cc2:
                    if st.button("Cancel", key=f"delno_{c['_id']}", use_container_width=True):
                        st.session_state.confirm_delete_id = None
                        st.rerun()
            else:
                col_name, col_del = st.columns([6, 1])
                with col_name:
                    if is_active:
                        _active_item(label, meta)
                    else:
                        if st.button(label, key=f"sb_{c['_id']}", use_container_width=True):
                            st.session_state.cb_view = c["_id"]
                            st.session_state.targeting_plan = {
                                k: v for k, v in c.items() if not str(k).startswith("_")
                            }
                            st.session_state.content_variants    = c.get("content_variants")
                            st.session_state.current_campaign_path = c.get("_path")
                            st.session_state.rep_briefing_result = None
                            st.session_state.rep_briefing_rep    = None
                            st.rerun()
                with col_del:
                    if st.button("✕", key=f"del_{c['_id']}", help=f"Delete {label}",
                                 use_container_width=True):
                        st.session_state.confirm_delete_id = c["_id"]
                        st.rerun()

    # ── Dataset campaigns ──────────────────────────────────────────────────────
    if digital:
        _sidebar_divider()
        for c in digital:
            is_active = st.session_state.cb_view == c["id"]
            meta = f"{c['crop'].title()} · {_fmt(c['impressions'])} impr"
            if _nav(c["id"], f"sb_{c['id']}", is_active, meta):
                st.session_state.cb_view = c["id"]
                st.session_state.targeting_plan = None
                st.session_state.content_variants = None
                st.session_state.current_campaign_path = None
                st.session_state.rep_briefing_result = None
                st.session_state.rep_briefing_rep    = None
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN AREA
# ═══════════════════════════════════════════════════════════════════════════════
view = st.session_state.cb_view


# ── WELCOME ───────────────────────────────────────────────────────────────────
if view == "welcome":
    inject_landing_css()

    total_impr   = funnel_df["social_post_impression"].sum()
    total_visits = funnel_df["landing_page_visits"].sum()
    total_leads  = funnel_df["lead_form_submission"].sum()
    total_camps  = len(digital) + len(saved_camps)

    # ── Hero — full-bleed image with overlay text ──────────────────────────────
    st.markdown(
        f"""
<div class="kp-hero">
  <img class="kp-hero-img" src="{IMG_HERO}" alt="Agricultural field at sunset" />
  <div class="kp-hero-overlay"></div>
  <div class="kp-hero-content">
    <div class="kp-hero-kicker">
      <span>🌾</span> Syngenta · Campaign Intelligence
    </div>
    <h1 class="kp-hero-title">Krishi Pracharak</h1>
    <p class="kp-hero-sub">
      AI-driven grower targeting across India — score receptivity, segment by crop &amp; risk,
      generate multilingual outreach, and brief field reps. All in one operational flow.
    </p>
    <div class="kp-hero-stats">
      <div class="kp-hero-stat">
        <div class="kp-hero-stat-val">6,000+</div>
        <div class="kp-hero-stat-lbl">Growers</div>
      </div>
      <div class="kp-hero-stat">
        <div class="kp-hero-stat-val">10</div>
        <div class="kp-hero-stat-lbl">States</div>
      </div>
      <div class="kp-hero-stat">
        <div class="kp-hero-stat-val">33</div>
        <div class="kp-hero-stat-lbl">Districts</div>
      </div>
      <div class="kp-hero-stat">
        <div class="kp-hero-stat-val accent">{_fmt(total_leads)}</div>
        <div class="kp-hero-stat-lbl">Leads</div>
      </div>
      <div class="kp-hero-stat">
        <div class="kp-hero-stat-val">{_fmt(total_impr)}</div>
        <div class="kp-hero-stat-lbl">Impressions</div>
      </div>
      <div class="kp-hero-stat">
        <div class="kp-hero-stat-val">6</div>
        <div class="kp-hero-stat-lbl">Languages</div>
      </div>
    </div>
  </div>
</div>""",
        unsafe_allow_html=True,
    )

    # ── How it works ───────────────────────────────────────────────────────────
    st.markdown(
        """
<div class="kp-how-strip">
  <div class="kp-how-step">
    <div class="kp-how-num">01</div>
    <div class="kp-how-icon">🎯</div>
    <div class="kp-how-label">Score Growers</div>
    <div class="kp-how-desc">15+ signals — crop stage, purchase history, weather risk, device type</div>
    <div class="kp-how-arrow">→</div>
  </div>
  <div class="kp-how-step">
    <div class="kp-how-num">02</div>
    <div class="kp-how-icon">🧩</div>
    <div class="kp-how-label">AI Segmentation</div>
    <div class="kp-how-desc">Claude agent segments by crop, state, persona &amp; outbreak risk</div>
    <div class="kp-how-arrow">→</div>
  </div>
  <div class="kp-how-step">
    <div class="kp-how-num">03</div>
    <div class="kp-how-icon">✍️</div>
    <div class="kp-how-label">Generate Content</div>
    <div class="kp-how-desc">WhatsApp, SMS, IVR &amp; poster in Hindi, Marathi, Punjabi &amp; more</div>
    <div class="kp-how-arrow">→</div>
  </div>
  <div class="kp-how-step">
    <div class="kp-how-num">04</div>
    <div class="kp-how-icon">📋</div>
    <div class="kp-how-label">Brief Field Reps</div>
    <div class="kp-how-desc">Ranked weekly action list — restock alerts, visit gaps, offline growers</div>
    <div class="kp-how-arrow">→</div>
  </div>
</div>""",
        unsafe_allow_html=True,
    )

    # ── Section header ─────────────────────────────────────────────────────────
    st.markdown(
        f'<div class="kp-section-head">'
        f'<span class="kp-section-title">All Campaigns</span>'
        f'<span class="kp-section-count">{total_camps} campaigns</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Campaign grid ──────────────────────────────────────────────────────────
    all_card_cols = st.columns(3, gap="medium")
    col_idx = 0

    for dc in digital:
        with all_card_cols[col_idx % 3]:
            img = crop_img(dc["crop"])
            st.markdown(
                f'<div class="kp-ccard">'
                f'<img class="kp-ccard-img" src="{img}" alt="{dc["crop"]}" />'
                f'<div class="kp-ccard-body">'
                f'<div class="kp-ccard-top">'
                f'<span class="kp-ccard-type">{dc["crop"].title()}</span>'
                f'<span class="kp-ccard-badge kp-ccard-badge-green">Digital</span>'
                f'</div>'
                f'<div class="kp-ccard-name">{dc["id"]}</div>'
                f'<div class="kp-ccard-meta">{dc["product"]} · {dc["start"][:7]}</div>'
                f'<div class="kp-ccard-stats">'
                f'<div class="kp-ccard-stat kp-ccard-stat-n">'
                f'<div class="kp-stat-val">{_fmt(dc["impressions"])}</div>'
                f'<div class="kp-stat-lbl">Impr</div></div>'
                f'<div class="kp-ccard-stat kp-ccard-stat-n">'
                f'<div class="kp-stat-val">{_fmt(dc["visits"])}</div>'
                f'<div class="kp-stat-lbl">Visits</div></div>'
                f'<div class="kp-ccard-stat kp-ccard-stat-g">'
                f'<div class="kp-stat-val kp-stat-val-g">{_fmt(dc["leads"])}</div>'
                f'<div class="kp-stat-lbl">Leads</div></div>'
                f'</div>'
                f'<div class="kp-ccard-rates">'
                f'Visit rate {dc["visit_rate"]:.1f}% &nbsp;·&nbsp; Lead rate {dc["lead_rate"]:.1f}%'
                f'</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
            if st.button("Open campaign →", key=f"wc_{dc['id']}", use_container_width=True):
                st.session_state.cb_view = dc["id"]
                st.session_state.targeting_plan = None
                st.session_state.content_variants = None
                st.session_state.current_campaign_path = None
                st.session_state.rep_briefing_result = None
                st.session_state.rep_briefing_rep = None
                st.rerun()
        col_idx += 1

    for sc in saved_camps:
        with all_card_cols[col_idx % 3]:
            sc_name    = sc.get("campaign_name") or sc["_filename"].replace(".json", "")
            sc_segs    = sc.get("segments") or []
            sc_growers = sum(s.get("grower_count", 0) for s in sc_segs)
            sc_date    = (sc.get("generated_at") or "")[:10] or "—"
            sc_obj     = sc.get("campaign_objective") or "AI Campaign"
            is_draft   = sc.get("stub", False) or not sc_segs
            sc_crop    = sc_segs[0].get("crop", "") if sc_segs else ""
            badge_cls  = "kp-ccard-badge-gray" if is_draft else "kp-ccard-badge-green"
            badge_txt  = "⚙ Draft" if is_draft else f"✓ {len(sc_segs)} segments"
            img        = crop_img(sc_crop) if sc_crop else IMG_PEOPLE
            st.markdown(
                f'<div class="kp-ccard">'
                f'<img class="kp-ccard-img" src="{img}" alt="campaign" />'
                f'<div class="kp-ccard-body">'
                f'<div class="kp-ccard-top">'
                f'<span class="kp-ccard-type">{sc_obj}</span>'
                f'<span class="kp-ccard-badge {badge_cls}">{badge_txt}</span>'
                f'</div>'
                f'<div class="kp-ccard-name">{sc_name}</div>'
                f'<div class="kp-ccard-meta">Created {sc_date}</div>'
                f'<div class="kp-ccard-growers">'
                f'{"Draft — no segments yet" if is_draft else f"{sc_growers:,} growers targeted"}'
                f'</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
            if st.button("Open campaign →", key=f"wsc_{sc['_id']}", use_container_width=True):
                st.session_state.cb_view = sc["_id"]
                st.session_state.targeting_plan = {
                    k: v for k, v in sc.items() if not str(k).startswith("_")
                }
                st.session_state.content_variants      = sc.get("content_variants")
                st.session_state.current_campaign_path = sc.get("_path")
                st.session_state.rep_briefing_result   = None
                st.session_state.rep_briefing_rep      = None
                st.rerun()
        col_idx += 1


# ── DIGITAL CAMPAIGN ──────────────────────────────────────────────────────────
elif any(c["id"] == view for c in digital):
    c = next(x for x in digital if x["id"] == view)
    inject_overview_css()

    st.markdown(
        camp_header_html(
            title=c["id"],
            kicker="Digital Campaign",
            meta=f"{c['crop'].title()} · {c['product']} · {c['start']} → {c['end']}",
            pills=[
                (f"{_fmt(c['impressions'])} Impressions", "white"),
                (f"{_fmt(c['visits'])} Visits", "white"),
                (f"{_fmt(c['leads'])} Leads", "green"),
                (f"Visit rate {c['visit_rate']:.1f}%", "white"),
                (f"Lead rate {c['lead_rate']:.1f}%", "amber"),
            ],
        ),
        unsafe_allow_html=True,
    )

    tab_ov, tab_cg, tab_rx, tab_rb = st.tabs(
        ["Overview", "Content Generation", "Receptivity", "Rep Briefing"]
    )

    with tab_ov:
        grower_state_map = _grower_states_by_crop(c["crop"])
        weeks_ts = [pd.Timestamp(w) for w in c["weeks"]]

        fig_sp = go.Figure(go.Scatter(
            x=c["weeks"], y=c["weekly_imp"], mode="lines",
            line=dict(color=_GREEN, width=2.5),
            fill="tozeroy", fillcolor="rgba(47,125,76,0.10)", hoverinfo="skip",
        ))
        fig_sp.update_layout(**_layout_with(
            height=180,
            xaxis=dict(visible=True, showgrid=False, tickfont=dict(size=10)),
            yaxis=dict(visible=True, showgrid=True, gridcolor="rgba(0,0,0,0.04)",
                       tickfont=dict(size=10)),
            showlegend=False,
            plot_bgcolor="#fffdf7", paper_bgcolor="#fffdf7",
            margin=dict(l=8, r=8, t=8, b=8),
        ))

        if grower_state_map and weeks_ts:
            ov1, ov2 = st.columns([3, 2])
            with ov1:
                section_label("Weekly Impressions")
                st.markdown('<div class="kp-chart-wrap">', unsafe_allow_html=True)
                st.plotly_chart(fig_sp, use_container_width=True, config={"displayModeBar": False})
                st.markdown('</div>', unsafe_allow_html=True)
            with ov2:
                section_label("Active States")
                _render_geo_map(grower_state_map)
        elif weeks_ts:
            section_label("Weekly Impressions")
            st.markdown('<div class="kp-chart-wrap">', unsafe_allow_html=True)
            st.plotly_chart(fig_sp, use_container_width=True, config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)

        if grower_state_map:
            section_label("Field Conditions")
            _render_weather_cards(list(grower_state_map.keys())[:5])

        section_label("Weekly Breakdown")
        wdf = (
            funnel_df[funnel_df["campaign_id"] == view]
            .sort_values("week_start_date")
            [["week_start_date", "social_post_impression", "landing_page_visits",
              "lead_form_submission"]]
            .rename(columns={
                "week_start_date":        "Week",
                "social_post_impression": "Impressions",
                "landing_page_visits":    "Visits",
                "lead_form_submission":   "Leads",
            })
        )
        st.dataframe(wdf, use_container_width=True, hide_index=True)

    with tab_cg:
        plan     = st.session_state.targeting_plan
        variants = st.session_state.content_variants

        # ── Step 1: Targeting controls ─────────────────────────────────────────
        with st.expander(
            "⚙ Step 1 — Build Targeting Plan" + (" ✓" if plan else ""),
            expanded=not plan,
        ):
            growers_df    = load_growers()
            unique_states = sorted(growers_df["state"].dropna().unique().tolist())
            f1, f2 = st.columns(2)
            ref_date = f1.date_input("Reference Date", value=REFERENCE_DATE, key=f"date_{view}")
            with f2:
                all_states_dig = st.checkbox(
                    "All states", value=True, key=f"all_states_{view}",
                    help="Target every state — uncheck to narrow to specific states",
                )
                if all_states_dig:
                    st.caption(f"Targeting all {len(unique_states)} states")
                    state_sel = []
                else:
                    state_sel = st.multiselect(
                        "Select states", unique_states, key=f"state_{view}",
                        placeholder="Choose one or more states",
                    )
            state_arg = state_sel if state_sel else None
            if st.button("Build Targeting Plan", type="primary",
                         use_container_width=True, key=f"build_{view}"):
                with st.spinner("Scoring growers…"):
                    plan = run_targeting(ref_date, c["crop"], state_arg,
                                        campaign_name=c["id"],
                                        campaign_objective="Awareness")
                    st.session_state.targeting_plan   = plan
                    st.session_state.content_variants = None
                    _persist_plan(plan, source_meta={
                        "source_type":    "digital_campaign",
                        "source_id":      c["id"],
                        "source_crop":    c["crop"],
                        "source_product": c["product"],
                        "state_filter":   state_arg,
                    })
                st.rerun()

        if plan:
            segs_plan = plan.get("segments", [])
            qs_plan   = plan.get("quality_summary", {})
            p1, p2, p3, p4 = st.columns(4)
            p1.metric("Growers Scored",  qs_plan.get("total_growers", "—"),
                      help="Total growers evaluated after applying crop and state filters")
            p2.metric("Eligible",        plan.get("total_eligible", "—"),
                      help="Growers above the 0.30 receptivity threshold with product in stock")
            p3.metric("Segments",        len(segs_plan),
                      help="Targeting groups — each segment gets its own multilingual content")
            p4.metric("OOS Blocked",     len(plan.get("oos_blocked", [])),
                      help="Grower groups excluded because their nearest retailer has out-of-stock risk")

            # ── Step 2: Scope preview + Promoter + Generate ───────────────────
            st.markdown("#### Content Scope")
            _render_content_scope(segs_plan)
            _render_promoter_uploader(key_prefix=f"promo_{view}")

            if not variants:
                if st.button("Generate Multilingual Content →", type="primary",
                             use_container_width=True, key=f"gen_{view}"):
                    _run_streaming_generation(plan, key_prefix=f"dig_{view}")
            else:
                rc1, rc2 = st.columns([4, 1])
                rc1.success(f"Content generated for {len(variants.get('variants', {}))} segments.")
                if rc2.button("Regenerate", key=f"regen_{view}"):
                    st.session_state.content_variants = None
                    _run_streaming_generation(plan, key_prefix=f"digr_{view}")

        st.divider()
        _render_content_variants()

    with tab_rx:
        _render_receptivity(plan=st.session_state.targeting_plan)

    with tab_rb:
        _render_rep_briefing_tab(plan=st.session_state.targeting_plan,
                                 campaign_path=st.session_state.current_campaign_path)


# ── AI / SAVED CAMPAIGN ───────────────────────────────────────────────────────
elif any(c["_id"] == view for c in saved_camps):
    c        = next(x for x in saved_camps if x["_id"] == view)
    segs     = c.get("segments", [])
    is_stub  = c.get("stub", False) or not segs
    crops    = sorted({s.get("crop", "").title() for s in segs})
    qs       = c.get("quality_summary", {})
    gen_at   = c.get("generated_at", "")[:16].replace("T", " ")
    camp_name = c.get("campaign_name") or c["_filename"].replace(".json", "")
    camp_obj  = c.get("campaign_objective", "")
    date_win  = c.get("date_window") or {}

    _draft_badge = (
        '<span style="background:rgba(255,255,255,0.15);border-radius:999px;'
        'padding:0.18rem 0.7rem;font-size:0.78rem;color:#d4edda;font-weight:600;">'
        '⚙ Draft — run targeting to activate</span>'
    )
    _oos_count = len(c.get("oos_blocked", []))
    _stats_html = (
        f'<span class="kp-stat-tip" style="color:#fff;font-size:0.88rem;">'
        f'<strong>{qs.get("total_growers","—")}</strong>'
        f'<span style="opacity:.7;font-size:0.78rem;"> Scored</span>'
        f'<span class="kp-tip-icon">ⓘ</span>'
        f'<span class="kp-tip-box">All growers in the dataset matching this campaign\'s crop and state filters — scored for receptivity.</span>'
        f'</span>'

        f'<span class="kp-stat-tip" style="color:#fff;font-size:0.88rem;">'
        f'<strong>{c.get("total_eligible","—")}</strong>'
        f'<span style="opacity:.7;font-size:0.78rem;"> Eligible</span>'
        f'<span class="kp-tip-icon">ⓘ</span>'
        f'<span class="kp-tip-box">Growers with a receptivity score ≥ 0.30 AND product in stock in their nearest retailer territory.</span>'
        f'</span>'

        f'<span class="kp-stat-tip" style="color:#fff;font-size:0.88rem;">'
        f'<strong>{len(segs)}</strong>'
        f'<span style="opacity:.7;font-size:0.78rem;"> Segments</span>'
        f'<span class="kp-tip-icon">ⓘ</span>'
        f'<span class="kp-tip-box">AI-generated audience segments — each one is a unique combination of crop × state × channel × persona × recommended product.</span>'
        f'</span>'

        f'<span class="kp-stat-tip" style="background:rgba(192,122,43,0.35);border-radius:999px;padding:0.18rem 0.7rem;'
        f'font-size:0.78rem;color:#ffd8a0;font-weight:600;">'
        f'{_oos_count} OOS blocked'
        f'<span class="kp-tip-icon">ⓘ</span>'
        f'<span class="kp-tip-box">Growers excluded because the recommended product is out-of-stock in their territory. They will not receive campaign messages.</span>'
        f'</span>'
    )

    inject_overview_css()

    _meta_parts = [', '.join(crops) if crops else '—', f"Created {gen_at}"]
    if date_win.get("start"):
        _meta_parts.append(f"{date_win['start']} → {date_win['end']}")

    if is_stub:
        _pills = [("⚙ Draft — run targeting to activate", "draft")]
    else:
        _pills = [
            (f"{qs.get('total_growers', '—')} Scored", "white"),
            (f"{c.get('total_eligible', '—')} Eligible", "green"),
            (f"{len(segs)} Segments", "white"),
        ]
        if _oos_count:
            _pills.append((f"{_oos_count} Out-of-stock blocked", "amber"))

    st.markdown(
        camp_header_html(
            title=camp_name,
            kicker=camp_obj or "AI Campaign",
            meta=" · ".join(_meta_parts),
            pills=_pills,
        ),
        unsafe_allow_html=True,
    )

    tab_ov, tab_cg, tab_rx, tab_rb = st.tabs(
        ["Overview", "Content Generation", "Receptivity", "Rep Briefing"]
    )

    with tab_ov:
        if is_stub:
            # ── Targeting form for new/draft campaigns ─────────────────────────
            section_label("Configure Campaign Targeting")
            st.caption("This campaign hasn't been run yet. Set your targeting parameters below.")
            growers_df = load_growers()
            raw_crops  = (growers_df["grower_crop_calendar"].dropna()
                          .apply(lambda x: x.get("crop", "") if isinstance(x, dict) else ""))
            unique_crops  = sorted(cc for cc in raw_crops.unique() if cc)
            unique_states = sorted(growers_df["state"].dropna().unique().tolist())

            f1, f2, f3 = st.columns(3)
            with f1:
                obj_sel = st.multiselect(
                    "Objective",
                    OBJECTIVES,
                    default=["Awareness"],
                    key=f"stub_obj_{view}",
                    placeholder="Pick one or more objectives",
                )
                objective = " + ".join(obj_sel) if obj_sel else "Awareness"

            # ── Crop selector with "All" toggle ───────────────────────────────
            with f2:
                all_crops_chk = st.checkbox(
                    "All crops", value=True, key=f"stub_all_crops_{view}",
                    help="Target every crop in the dataset — uncheck to pick specific crops",
                )
                if all_crops_chk:
                    st.caption(f"Targeting all {len(unique_crops)} crops")
                    crop_sel = []
                else:
                    crop_sel = st.multiselect(
                        "Select crops", unique_crops, key=f"stub_crop_{view}",
                        placeholder="Choose one or more crops",
                    )
            crop_arg = crop_sel if crop_sel else None

            # ── State selector with "All" toggle ──────────────────────────────
            with f3:
                all_states_chk = st.checkbox(
                    "All states", value=True, key=f"stub_all_states_{view}",
                    help="Target every state in the dataset — uncheck to pick specific states",
                )
                if all_states_chk:
                    st.caption(f"Targeting all {len(unique_states)} states")
                    state_sel = []
                else:
                    state_sel = st.multiselect(
                        "Select states", unique_states, key=f"stub_state_{view}",
                        placeholder="Choose one or more states",
                    )
            state_arg = state_sel if state_sel else None

            # ── Date range + live duration display ────────────────────────────
            d1, d2, d3 = st.columns(3)
            start_date  = d1.date_input("Campaign Start", value=REFERENCE_DATE,
                                        key=f"stub_start_{view}")
            end_date    = d2.date_input("Campaign End",   value=date(2026, 3, 31),
                                        key=f"stub_end_{view}")
            channel_mix = d3.multiselect("Channel Mix",
                                         ["WhatsApp", "SMS", "IVR", "Rep Assist"],
                                         default=["WhatsApp", "SMS", "IVR"],
                                         key=f"stub_channels_{view}")

            # Duration badge shown inline between the date fields
            _delta = (end_date - start_date).days if end_date > start_date else 0
            if _delta > 0:
                _weeks, _rem = divmod(_delta, 7)
                _dur_str = (
                    f"{_weeks}w {_rem}d" if _weeks and _rem
                    else (f"{_weeks} week{'s' if _weeks != 1 else ''}" if _weeks
                          else f"{_delta} days")
                )
                _crops_label  = f"{len(crop_sel)} crops"  if crop_sel  else f"all {len(unique_crops)} crops"
                _states_label = f"{len(state_sel)} states" if state_sel else f"all {len(unique_states)} states"
                st.markdown(
                    f'<div style="background:#eef7f1;border-radius:8px;padding:0.45rem 0.85rem;'
                    f'margin-top:0.2rem;display:inline-flex;gap:0.7rem;align-items:center;'
                    f'flex-wrap:wrap;font-size:0.8rem;">'
                    f'<span style="color:{_GREEN};font-weight:700;">📅 {_dur_str}</span>'
                    f'<span style="color:#5a6b62;">·</span>'
                    f'<span style="color:#3a4f43;">{_crops_label}</span>'
                    f'<span style="color:#5a6b62;">·</span>'
                    f'<span style="color:#3a4f43;">{_states_label}</span>'
                    f'<span style="color:#5a6b62;">·</span>'
                    f'<span style="color:#3a4f43;">{start_date.strftime("%d %b")} → {end_date.strftime("%d %b %Y")}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            elif end_date <= start_date:
                st.warning("End date must be after start date.")

            b1c, b2c = st.columns([2, 1])
            build_clicked = b1c.button("Build Targeting Plan", type="primary",
                                       use_container_width=True, key=f"stub_build_{view}")
            gen_clicked   = (
                b2c.button("Generate Content", use_container_width=True, key=f"stub_gen_{view}")
                if st.session_state.targeting_plan else False
            )

            if build_clicked:
                date_window = {"start": start_date.isoformat(), "end": end_date.isoformat()}
                with st.spinner("Scoring growers and building segments…"):
                    plan = run_targeting(
                        start_date, crop_arg, state_arg,
                        campaign_name=camp_name,
                        campaign_objective=objective,
                        date_window=date_window,
                        channel_mix=channel_mix,
                    )
                    st.session_state.targeting_plan   = plan
                    st.session_state.content_variants = None
                    _persist_plan(plan, source_meta={
                        "source_type":  "new_campaign",
                        "source_crop":  crop_arg,
                        "state_filter": state_arg,
                    })
                st.rerun()

            if gen_clicked:
                _run_streaming_generation(st.session_state.targeting_plan, key_prefix="new")

            # Show preview if plan was just built in this session
            plan = st.session_state.targeting_plan
            if plan and plan.get("segments"):
                st.divider()
                st.info(plan.get("rationale", "-"))
                # ── Agent insight banner ──────────────────────────────────────
                ai_ins = plan.get("agent_insight", {})
                if ai_ins.get("campaign_advice"):
                    n_tools = len(ai_ins.get("tool_calls_made", []))
                    n_segs  = ai_ins.get("segments_prioritised", 0)
                    st.markdown(
                        f'<div style="background:linear-gradient(135deg,#0d2318 0%,#172d1e 100%);'
                        f'border-radius:12px;padding:0.85rem 1.15rem;margin-bottom:0.5rem;'
                        f'border:1px solid rgba(47,125,76,0.4);">'
                        f'<div style="font-size:0.68rem;font-weight:700;color:rgba(212,237,218,0.6);'
                        f'text-transform:uppercase;letter-spacing:0.07em;margin-bottom:0.3rem;">'
                        f'🤖 AI Segmentation Agent · {n_tools} tool calls · {n_segs} segments prioritised</div>'
                        f'<div style="font-size:0.88rem;color:#d4edda;line-height:1.6;">'
                        f'{ai_ins["campaign_advice"]}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    if ai_ins.get("tool_calls_made"):
                        with st.expander(f"🔧 Agent tool calls ({n_tools})", expanded=False):
                            for tc in ai_ins["tool_calls_made"]:
                                st.markdown(
                                    f'`{tc["tool"]}` → `{json.dumps(tc["args"])}`',
                                )
                qsp = plan.get("quality_summary", {})
                st.markdown(
                    seg_stats_html(
                        scored=qsp.get("total_growers", 0),
                        eligible=plan.get("total_eligible", 0),
                        non_smartphone=qsp.get("non_smartphone", 0),
                        segments=len(plan.get("segments", [])),
                    ),
                    unsafe_allow_html=True,
                )
                segs_new = plan.get("segments", [])
                if segs_new:
                    dw = plan.get("date_window") or {}
                    _render_segment_overview(segs_new, plan.get("reference_date", start_date), dw)
                    section_label(f"Targeting Segments ({len(segs_new)})")
                    _render_segment_cards(segs_new)
        else:
            # ── Normal saved campaign overview ─────────────────────────────────
            if c.get("rationale"):
                st.info(c["rationale"])
            ai_ins_saved = c.get("agent_insight", {})
            if ai_ins_saved.get("campaign_advice"):
                n_tools = len(ai_ins_saved.get("tool_calls_made", []))
                n_segs  = ai_ins_saved.get("segments_prioritised", 0)
                st.markdown(
                    agent_block_html(
                        kicker=f"AI Segmentation Agent · {n_tools} tool calls · {n_segs} segments prioritised",
                        body=ai_ins_saved["campaign_advice"],
                    ),
                    unsafe_allow_html=True,
                )
            if c.get("oos_blocked"):
                grouped_oos = _summarize_oos_blocks(c["oos_blocked"])
                st.markdown(
                    oos_block_html(
                        title=f"{len(c['oos_blocked'])} group(s) paused — out-of-stock risk",
                        items=[
                            f"{b['crop'].title()} in {b['state']}: {b['product']} "
                            f"({b['grower_count']} growers) — {b['reason']}"
                            for b in grouped_oos
                        ],
                    ),
                    unsafe_allow_html=True,
                )
            if segs:
                qs_s = c.get("quality_summary", {})
                st.markdown(
                    seg_stats_html(
                        scored=qs_s.get("total_growers", 0),
                        eligible=c.get("total_eligible", 0),
                        non_smartphone=qs_s.get("non_smartphone", 0),
                        segments=len(segs),
                    ),
                    unsafe_allow_html=True,
                )
                _render_segment_overview(segs, c.get("reference_date", date.today()),
                                         date_win or None)
                section_label(f"Targeting Segments ({len(segs)})")
                _render_segment_cards(segs)
            st.download_button(
                "⬇ Download JSON",
                data=json.dumps({k: v for k, v in c.items() if not k.startswith("_")},
                                indent=2, ensure_ascii=False),
                file_name=c["_filename"], mime="application/json",
            )

    with tab_cg:
        # Keep session state in sync with the loaded campaign file
        st.session_state.targeting_plan        = {k: v for k, v in c.items()
                                                   if not str(k).startswith("_")}
        st.session_state.current_campaign_path = c.get("_path")

        if is_stub:
            st.info("Run targeting in the **Overview** tab first to unlock content generation.")
        elif not segs:
            st.warning("No segments in this campaign — rebuild the targeting plan.")
        else:
            # Show plan summary
            qs_c = c.get("quality_summary", {})
            p1, p2, p3, p4 = st.columns(4)
            p1.metric("Growers Scored", qs_c.get("total_growers", "—"),
                      help="Total growers evaluated after applying crop and state filters")
            p2.metric("Eligible",       c.get("total_eligible", "—"),
                      help="Growers above the 0.30 receptivity threshold with product in stock")
            p3.metric("Segments",       len(segs),
                      help="Targeting groups — each segment gets its own multilingual content")
            p4.metric("OOS Blocked",    len(c.get("oos_blocked", [])),
                      help="Grower groups excluded because their nearest retailer has out-of-stock risk")
            st.markdown("")

            # ── Scope preview + Promoter + Generate ───────────────────────────
            st.markdown("#### Content Scope")
            _render_content_scope(segs)
            _render_promoter_uploader(key_prefix=f"promo_{c['_id']}")

            _cv = c.get("content_variants")
            existing_variants = _cv if _cv is not None else st.session_state.content_variants
            if existing_variants:
                st.session_state.content_variants = existing_variants
                rc1, rc2 = st.columns([4, 1])
                rc1.success(f"Content generated for {len(existing_variants.get('variants', {}))} segments.")
                if rc2.button("Regenerate", key=f"regen_saved_{c['_id']}"):
                    st.session_state.content_variants = None
                    _run_streaming_generation(
                        st.session_state.targeting_plan,
                        key_prefix=f"savedR_{c['_id']}",
                    )
            else:
                st.session_state.content_variants = None
                if st.button("Generate Multilingual Content →", type="primary",
                             use_container_width=True, key=f"gen_saved_{c['_id']}"):
                    _run_streaming_generation(
                        st.session_state.targeting_plan,
                        key_prefix=f"saved_{c['_id']}",
                    )

            st.divider()
            _render_content_variants()

    with tab_rx:
        _render_receptivity(plan=st.session_state.targeting_plan)

    with tab_rb:
        _render_rep_briefing_tab(plan=st.session_state.targeting_plan,
                                 campaign_path=c.get("_path"))


# ── FALLBACK (deleted or unknown view — reset to welcome) ─────────────────────
else:
    st.session_state.cb_view = "welcome"
    st.rerun()
