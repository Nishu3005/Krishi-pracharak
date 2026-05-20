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
from agents.content_agent import run_content_generation, run_content_generation_streaming, describe_promoter
from agents.rep_agent import run_rep_briefing
from agents.targeting_agent import run_targeting
from utils.campaign_store import attach_variants, delete_campaign, load_saved_campaigns, save_plan
from utils.data_loader import load_digital_funnel, load_growers, load_reps, load_whatsapp
from utils.ui_theme import apply_theme

# Needed for lazy import of inventory_analysis inside _load_inv_insights()
sys.path.insert(0, str(Path(__file__).parent.parent / "Syngenta_IITM_Hackathon_2026_dataset"))

st.set_page_config(page_title="Campaign Builder · Krishi Pracharak", layout="wide")
apply_theme()

# ── Sidebar button style ───────────────────────────────────────────────────────
st.markdown("""
<style>
section[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: 1px solid transparent !important;
    border-radius: 8px !important;
    text-align: left !important;
    width: 100% !important;
    padding: 0.3rem 0.7rem !important;
    color: rgba(210,232,216,0.72) !important;
    font-size: 0.82rem !important;
    font-weight: 400 !important;
    justify-content: flex-start !important;
    transition: background 0.13s !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(47,125,76,0.22) !important;
    color: #fff !important;
    border-color: rgba(47,125,76,0.4) !important;
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
REFERENCE_DATE = date(2026, 1, 15)


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
def _active_item(label: str):
    st.markdown(
        f'<div style="background:rgba(47,125,76,0.32);border-left:3px solid {_GREEN};'
        f'border-radius:8px;padding:0.3rem 0.68rem;font-size:0.82rem;font-weight:600;'
        f'color:#fff;margin-bottom:1px;">{label}</div>',
        unsafe_allow_html=True,
    )


def _nav(label: str, key: str, active: bool) -> bool:
    if active:
        _active_item(label)
        return False
    return st.button(label, key=key, use_container_width=True)


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
                rain_badge = (
                    f'<div style="margin-top:0.25rem;"><span style="background:#fff3e0;'
                    f'color:{_AMBER};border-radius:5px;padding:1px 5px;font-size:0.67rem;">'
                    f'🌧 {rain_today:.0f}mm</span></div>'
                    if rain_today > 0 else ""
                )
                st.markdown(
                    f'<div style="border:1px solid #c8dcd0;border-radius:10px;'
                    f'padding:0.65rem 0.7rem;background:#f4faf6;">'
                    f'<div style="font-size:0.65rem;font-weight:700;color:#1a5c35;'
                    f'text-transform:uppercase;letter-spacing:0.04em;">{w["city"]}</div>'
                    f'<div style="font-size:1.35rem;margin:0.15rem 0;">'
                    f'{emoji} {w["temp_c"]:.0f}°C</div>'
                    f'<div style="font-size:0.68rem;color:#4f6157;">{w["condition"]}</div>'
                    f'<div style="font-size:0.66rem;color:#6e7f72;margin-top:0.18rem;">'
                    f'💧{w["humidity_pct"]}% · 💨{w["wind_kmh"]:.0f}km/h</div>'
                    f'{rain_badge}</div>',
                    unsafe_allow_html=True,
                )
    if any(weather.values()):
        ages = [
            (datetime.utcnow() - datetime.fromisoformat(w["fetched_at"])).seconds // 60
            for w in weather.values() if w
        ]
        st.caption(f"Open-Meteo · fetched {min(ages)} min ago · 3-day forecast · no API key required")
    else:
        st.caption("Weather data unavailable — network may be offline.")


def _render_segment_overview(segs: list[dict], reference_date, date_window: dict | None = None):
    active_states = list({s["state"] for s in segs if s.get("state")})
    state_grower: dict[str, int] = {}
    for s in segs:
        state_grower[s["state"]] = state_grower.get(s["state"], 0) + s.get("grower_count", 0)
    campaign_end = date_window.get("end") if date_window else None
    ov1, ov2 = st.columns([3, 2])
    with ov1:
        st.markdown("**Campaign Timeline**")
        _render_timeline(segs, reference_date, campaign_end)
    with ov2:
        st.markdown("**Active States**")
        _render_geo_map(state_grower)
    if active_states:
        st.markdown("**Field Conditions**")
        _render_weather_cards(active_states)


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
        Path("C:/Windows/Fonts/Nirmala.ttf"),                                      # Windows 8+ — best coverage
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
                            key=f"stw_{seg_id}")
        with c2:
            st.caption("💬 SMS")
            _render_sms_card(content.get("sms"), content.get("sms_meta"),
                             key=f"sts_{seg_id}")
        _render_ivr_card(content.get("ivr_script"), content.get("ivr_meta"),
                         "IVR Script", language=_lang, key_suffix=f"sti_{seg_id}")
    else:
        _render_ivr_card(content.get("ivr_script"), content.get("ivr_meta"),
                         "Field Visit Script", language=_lang, key_suffix=f"stf_{seg_id}")

    poster_path = content.get("poster_file_path")
    poster_url  = content.get("poster_image_url")
    if poster_path and Path(poster_path).exists():
        st.image(poster_path, caption="Campaign Poster", use_container_width=True)
    elif poster_url:
        st.image(poster_url, caption="Campaign Poster", use_container_width=True)
    else:
        st.caption("🖼 _Poster unavailable_")


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


def _render_wa_card(text: str | None, meta: dict | None, key: str = "wa"):
    """WhatsApp-style chat bubble card with copy button."""
    if (meta or {}).get("status") == "skipped":
        st.caption("_Not applicable — rep-assist channel_")
        return
    body = _safe_html(text)
    st.markdown(
        f"""<div class="kp-wa-phone">
  <div class="kp-wa-header">
    <div class="kp-wa-avatar">S</div>
    <div><div class="kp-wa-hname">Syngenta India</div>
    <div class="kp-wa-hstatus">online</div></div>
  </div>
  <div class="kp-wa-body">
    <div class="kp-wa-bubble">{body}
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
    m1.metric("Segments", total)
    m2.metric("Full Success", total - fallback_count)
    m3.metric("Partial Fallback", fallback_count,
              delta_color="inverse" if fallback_count else "off")
    m4.metric("Generated", variants.get("generated_at", "")[:10] or "—")
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
            st.markdown("")

            _lang = content.get("language", "Hindi")
            if channel == "whatsapp":
                col_wa, col_sms = st.columns(2, gap="medium")
                with col_wa:
                    st.markdown(
                        '<div style="font-size:0.7rem;font-weight:700;color:#1a5c35;'
                        'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.4rem;">'
                        '📱 WhatsApp</div>', unsafe_allow_html=True)
                    _render_wa_card(content.get("whatsapp"), content.get("whatsapp_meta"),
                                    key=seg_id)
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

            # Poster
            st.markdown("")
            st.markdown(
                '<div style="font-size:0.72rem;font-weight:700;color:#1a5c35;'
                'text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.5rem;">'
                '🖼 Poster</div>',
                unsafe_allow_html=True,
            )
            url = content.get("poster_image_url")
            if url:
                pc1, pc2 = st.columns([2, 1])
                with pc1:
                    st.image(url, use_container_width=True)
                with pc2:
                    prompt = content.get("poster_prompt_used", "")
                    if prompt:
                        st.caption(f"**Prompt used:**\n{prompt[:200]}{'…' if len(prompt) > 200 else ''}")
                    gen_at = content.get("poster_generated_at", "")
                    if gen_at:
                        st.caption(f"Generated {gen_at[:16].replace('T', ' ')} UTC")
                    st.markdown(_status_badge(content.get("poster_status", "unknown")),
                                unsafe_allow_html=True)
            else:
                ps_col, pp_col = st.columns([1, 2])
                with ps_col:
                    st.markdown(
                        f'<div style="border:1px dashed {_AMBER};border-radius:10px;'
                        f'padding:1.5rem;text-align:center;background:#fffaf4;">'
                        f'{_status_badge(content.get("poster_status", "unknown"))}'
                        f'<div style="font-size:0.78rem;color:#999;margin-top:0.5rem;">'
                        f'Poster image unavailable</div></div>',
                        unsafe_allow_html=True,
                    )
                with pp_col:
                    prompt = content.get("poster_prompt_used", "")
                    if prompt:
                        st.caption(f"**Prompt used:**\n{prompt[:200]}{'…' if len(prompt) > 200 else ''}")

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
def _render_receptivity(crop_filter: str | None = None):
    with st.spinner("Computing receptivity scores…"):
        df = _scored_df()
    wa = load_whatsapp()
    if crop_filter:
        crop_key = str(crop_filter).strip().lower()
        crop_ids = (df[df["crop"].astype(str).str.lower() == crop_key]["grower_id"]
                    if "crop" in df.columns else df["grower_id"])
        df = df[df["grower_id"].isin(crop_ids)]
        wa = (wa[wa["campaign_crop"].astype(str).str.lower() == crop_key]
              if "campaign_crop" in wa.columns else wa)
    if df.empty:
        st.warning("No growers found for this crop filter in the scored dataset.")
        return
    wa_df = wa.merge(
        df[["grower_id", "receptivity_score", "state", "farm_tier", "timing_mode"]],
        on="grower_id", how="left",
    )
    baseline_open = wa["opened_status"].mean() if len(wa) else 0
    top_q       = df["receptivity_score"].quantile(0.75)
    top_growers = df[df["receptivity_score"] >= top_q]["grower_id"]
    top_wa      = wa[wa["grower_id"].isin(top_growers)]
    top_open    = top_wa["opened_status"].mean() if len(top_wa) else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("Baseline Open Rate",     f"{baseline_open:.1%}")
    c2.metric("Top-Quartile Open Rate", f"{top_open:.1%}", delta=f"+{top_open - baseline_open:.1%}")
    c3.metric("Top-Quartile Growers",   len(top_growers))
    st.caption("Retrospective validation using the same dataset window used for scoring.")
    st.divider()
    l1, r1 = st.columns(2)
    with l1:
        st.markdown("**Score Distribution**")
        fig = px.histogram(df, x="receptivity_score", nbins=30, color_discrete_sequence=[_GREEN])
        fig.add_vline(x=0.30, line_dash="dash", line_color=_AMBER, annotation_text="Threshold")
        fig.update_layout(**_layout_with(xaxis_title="Receptivity Score", yaxis_title="Growers",
                                         showlegend=False))
        st.plotly_chart(fig, use_container_width=True)
    with r1:
        st.markdown("**Signal Contributions (Avg)**")
        bds   = df["score_breakdown"].apply(lambda x: x.get("breakdown", {}) if isinstance(x, dict) else {})
        bd_df = pd.DataFrame(list(bds)).mean().reset_index()
        bd_df.columns = ["Signal", "Avg Contribution"]
        bd_df = bd_df.sort_values("Avg Contribution", ascending=True)
        fig2  = px.bar(bd_df, x="Avg Contribution", y="Signal", orientation="h",
                       color_discrete_sequence=[_GREEN])
        fig2.update_layout(**_layout_with())
        st.plotly_chart(fig2, use_container_width=True)
    l2, r2 = st.columns(2)
    with l2:
        st.markdown("**Open Rate by State**")
        state_data = (wa_df.groupby("state").agg(open_rate=("opened_status", "mean"))
                      .reset_index().sort_values("open_rate", ascending=False))
        fig3 = px.bar(state_data, x="state", y="open_rate",
                      color="open_rate",
                      color_continuous_scale=[[0, "#d6ead9"], [1, _GREEN]],
                      labels={"open_rate": "Open Rate", "state": "State"})
        fig3.add_hline(y=baseline_open, line_dash="dash", line_color=_AMBER,
                       annotation_text="Baseline")
        fig3.update_layout(**_layout_with(xaxis_tickangle=-35))
        st.plotly_chart(fig3, use_container_width=True)
    with r2:
        st.markdown("**Open Rate by Farm Size Tier**")
        if "farm_tier" in df.columns:
            tier_data = wa_df.groupby("farm_tier")["opened_status"].mean().reset_index()
            tier_data.columns = ["Farm Size Tier", "Open Rate"]
            fig4 = px.bar(tier_data, x="Farm Size Tier", y="Open Rate",
                          color_discrete_sequence=["#3f9662"])
            fig4.add_hline(y=baseline_open, line_dash="dash", line_color=_AMBER)
            fig4.update_layout(**_layout_with())
            st.plotly_chart(fig4, use_container_width=True)
    l3, r3 = st.columns(2)
    with l3:
        st.markdown("**Channel Eligibility Split**")
        ch_df = df["device_type"].value_counts().reset_index()
        ch_df.columns = ["Device Type", "Count"]
        fig5  = px.pie(ch_df, names="Device Type", values="Count",
                       color_discrete_sequence=[_GREEN, "#88bb97", "#c7dcca"])
        fig5.update_layout(**_layout_with())
        st.plotly_chart(fig5, use_container_width=True)
    with r3:
        st.markdown("**Timing Mode Coverage**")
        tm_df = df["timing_mode"].value_counts().reset_index()
        tm_df.columns = ["Timing Mode", "Count"]
        fig6  = px.pie(tm_df, names="Timing Mode", values="Count",
                       color_discrete_sequence=[_GREEN, "#6ea781", "#d8e2d2"])
        fig6.update_layout(**_layout_with())
        st.plotly_chart(fig6, use_container_width=True)


# ── Rep Briefing tab ───────────────────────────────────────────────────────────
def _render_rep_briefing_tab(campaign_path: str | None = None):
    _INV_LAYOUT = dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=30, b=10),
        font=dict(color="#1d2a22", family="Space Grotesk"),
    )

    reps    = load_reps()
    rep_ids = sorted(reps["rep_id"].tolist())

    left, main = st.columns([1, 3], gap="large")
    with left:
        st.markdown("#### Parameters")
        rep_id = st.selectbox("Select Rep", rep_ids, key="rb_rep_select")
        reference_date = st.date_input("Reference Date", value=date(2026, 1, 15),
                                       key="rb_ref_date")
        st.markdown("")
        gen_clicked = st.button("Generate Briefing", type="primary",
                                use_container_width=True, key="rb_gen_btn")

    if gen_clicked:
        with st.spinner(f"Analyzing territory and generating briefing for {rep_id}…"):
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
                '<div style="font-size:0.85rem;margin-top:0.4rem;">The AI will compute stock risk, '
                'visit gaps, and offline growers for this territory.</div></div>',
                unsafe_allow_html=True,
            )
        else:
            briefing = st.session_state.rep_briefing_result
            rep_row  = reps[reps["rep_id"] == rep_id].iloc[0]
            st.subheader(f"{rep_id} — {rep_row['territory_name']} "
                         f"({rep_row['state']}, {rep_row['district']})")

            actions = briefing.get("priority_actions", [])
            restock = [a for a in actions if a["type"] == "restock_alert"]
            gap     = [a for a in actions if a["type"] == "visit_gap"]

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Actions",   len(actions))
            c2.metric("Restock Alerts",  len(restock))
            c3.metric("Visit Gaps",      len(gap))
            c4.metric("Offline Growers", briefing.get("offline_growers_count", 0),
                      help="Non-smartphone growers who need in-person or assisted outreach")

            st.subheader("This Week's Briefing")
            st.info(briefing.get("briefing_text", "-"))

            st.divider()
            st.subheader("Priority Actions")
            for action in actions:
                atype = action["type"]
                rank  = action["rank"]
                if atype == "rep_assist_campaign":
                    title = (f"#{rank} Assisted Campaign — "
                             f"{action.get('crop', '').title()} ({action.get('persona', '')})")
                    body  = (f"**Product:** {action.get('product')}  \n"
                             f"**Growers to visit:** {action.get('grower_count')}  \n"
                             f"**Tehsils:** {', '.join(action.get('tehsils', []))}")
                elif atype == "restock_alert":
                    title = f"#{rank} Restock Alert — {action.get('sku')}"
                    body  = (f"**Estimated weeks until OOS:** {action.get('weeks_until_oos')}  \n"
                             f"**Average stock:** {action.get('avg_stock')} units  \n"
                             f"**Trend:** {action.get('trend_slope')} units/week")
                else:
                    title = f"#{rank} Visit Gap — {action.get('tehsil')}"
                    body  = f"**Days since last visit:** {action.get('days_since_visit')}"
                with st.expander(title, expanded=rank <= 3):
                    st.markdown(body)

            if briefing.get("offline_growers_count", 0) > 0:
                st.divider()
                st.subheader("Offline Growers (Non-Smartphone)")
                growers = load_growers()
                tehsil_list = rep_row["tehsil_list"]
                offline = growers[
                    growers["tehsil"].isin(tehsil_list) & (growers["device_type"] != "smartphone")
                ][["grower_id", "tehsil", "device_type", "grower_crop_calendar",
                   "grower_farm_size"]].copy()
                offline["crop"] = offline["grower_crop_calendar"].apply(
                    lambda x: x.get("crop", "-") if isinstance(x, dict) else "-"
                )
                st.dataframe(
                    offline[["grower_id", "tehsil", "crop", "device_type", "grower_farm_size"]],
                    use_container_width=True, hide_index=True,
                )

    # ── Inventory Intelligence (collapsible) ───────────────────────────────────
    st.divider()
    with st.expander("📦 Inventory Intelligence", expanded=False):
        st.caption("Stock health, OOS risk, and depletion trends across 4,000 retailers.")
        try:
            inv = _load_inv_insights()
        except Exception as e:
            st.warning(f"Inventory data unavailable: {e}")
            return
        _PALETTE = ["#2f7d4c", "#5aa876", "#88bb97", "#c07a2b", "#e8a85b", "#1a5c35"]
        mi1, mi2, mi3, mi4 = st.columns(4)
        mi1.metric("Total SKUs",         inv["unique_skus"])
        mi2.metric("Total Retailers",    f"{inv['unique_retailers']:,}")
        mi3.metric("Total OOS Events",   f"{inv['total_oos_events']:,}")
        mi4.metric("Retailers with OOS", f"{inv['retailers_with_any_oos']:,}")

        # Nested st.tabs inside a tab aren't supported — use expanders instead
        with st.expander("📉 OOS Risk", expanded=True):
            cl, cr = st.columns(2, gap="medium")
            with cl:
                st.markdown("**OOS Rate (%) by SKU**")
                oos_rate = inv["oos_rate_by_sku"]
                oos_df   = (pd.DataFrame({"sku": list(oos_rate.keys()),
                                          "oos_rate": list(oos_rate.values())})
                            .sort_values("oos_rate", ascending=True))
                mean_oos = float(pd.Series(list(oos_rate.values())).mean())
                fig_oos  = go.Figure()
                fig_oos.add_trace(go.Bar(x=oos_df["oos_rate"], y=oos_df["sku"],
                                         orientation="h", marker_color="#c07a2b"))
                fig_oos.add_vline(x=mean_oos, line_dash="dash", line_color="#1a5c35",
                                  annotation_text=f"Mean {mean_oos:.1f}%",
                                  annotation_position="top right",
                                  annotation_font_color="#1a5c35")
                fig_oos.update_layout(**_INV_LAYOUT, xaxis_title="OOS Rate (%)",
                                      yaxis_title=None, showlegend=False)
                st.plotly_chart(fig_oos, use_container_width=True,
                                config={"displayModeBar": False})
            with cr:
                st.markdown("**Avg Stock Level by SKU**")
                avg_stock   = inv["avg_stock_by_sku"]
                at_risk_set = set(inv["at_risk_skus"])
                avg_df      = (pd.DataFrame({"sku": list(avg_stock.keys()),
                                             "avg_qty": list(avg_stock.values())})
                               .sort_values("avg_qty", ascending=True))
                bar_colors  = ["#c07a2b" if sku in at_risk_set else "#2f7d4c"
                               for sku in avg_df["sku"]]
                fig_avg = go.Figure()
                fig_avg.add_trace(go.Bar(x=avg_df["avg_qty"], y=avg_df["sku"],
                                         orientation="h", marker_color=bar_colors))
                fig_avg.update_layout(**_INV_LAYOUT, xaxis_title="Avg Qty (units)",
                                      yaxis_title=None, showlegend=False)
                st.plotly_chart(fig_avg, use_container_width=True,
                                config={"displayModeBar": False})
                st.caption("Orange bars = at-risk SKUs")

        with st.expander("📈 Stock Trends", expanded=False):
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
            inv_lt.update(dict(title="Weekly Average Stock by SKU",
                               xaxis_title="Week End Date", yaxis_title="Avg Qty (units)",
                               legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                           xanchor="left", x=0),
                               margin=dict(l=10, r=10, t=60, b=10)))
            fig_trend.update_layout(**inv_lt)
            st.plotly_chart(fig_trend, use_container_width=True,
                            config={"displayModeBar": False})
            at_risk = inv["at_risk_skus"]
            if at_risk:
                badges = " ".join(
                    f'<span style="background:#fff3e0;border:1px solid #c07a2b;'
                    f'border-radius:6px;padding:2px 10px;color:#c07a2b;font-size:0.82rem;'
                    f'margin-right:4px;">⚠️ {s}</span>' for s in at_risk
                )
                st.markdown(
                    f'<div style="margin-top:0.5rem;"><strong style="color:#1d2a22;">'
                    f'At-Risk SKUs: </strong>{badges}</div>',
                    unsafe_allow_html=True,
                )

        with st.expander("🔥 Risk Heatmap", expanded=False):
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
            inv_lh = dict(_INV_LAYOUT)
            inv_lh.update(dict(title="OOS Rate (%) by SKU × Week",
                               xaxis_title="Week End Date", yaxis_title=None,
                               margin=dict(l=10, r=10, t=50, b=10)))
            fig_hm.update_layout(**inv_lh)
            st.plotly_chart(fig_hm, use_container_width=True,
                            config={"displayModeBar": False})


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
    st.markdown(
        '<p style="font-size:0.68rem;font-weight:700;letter-spacing:0.09em;'
        'color:rgba(180,220,190,0.55);text-transform:uppercase;margin:14px 0 5px 2px;">'
        'Campaigns</p>',
        unsafe_allow_html=True,
    )

    # Digital campaigns (read-only from dataset — no delete)
    for c in digital:
        if _nav(c["id"], f"sb_{c['id']}", st.session_state.cb_view == c["id"]):
            st.session_state.cb_view = c["id"]
            st.session_state.targeting_plan = None
            st.session_state.content_variants = None
            st.session_state.current_campaign_path = None
            st.session_state.rep_briefing_result = None
            st.session_state.rep_briefing_rep    = None
            st.rerun()

    # AI / saved campaigns — name button + ✕ delete button
    for c in saved_camps:
        label     = c.get("campaign_name") or c["_filename"].replace(".json", "")
        is_active = st.session_state.cb_view == c["_id"]
        col_name, col_del = st.columns([5, 1])
        with col_name:
            if is_active:
                _active_item(label)
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
            if st.session_state.confirm_delete_id == c["_id"]:
                st.caption("Delete?")
                cc1, cc2 = st.columns(2)
                if cc1.button("Yes", key=f"delyes_{c['_id']}", use_container_width=True):
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
                if cc2.button("No", key=f"delno_{c['_id']}", use_container_width=True):
                    st.session_state.confirm_delete_id = None
                    st.rerun()
            else:
                if st.button("✕", key=f"del_{c['_id']}", help=f"Delete {label}"):
                    st.session_state.confirm_delete_id = c["_id"]
                    st.rerun()

    st.markdown(
        '<div style="border-top:1px solid rgba(255,255,255,0.08);margin:10px 0 6px;"></div>',
        unsafe_allow_html=True,
    )
    if st.button("＋  New Campaign", key="sb_new", use_container_width=True):
        _new_campaign_dialog()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN AREA
# ═══════════════════════════════════════════════════════════════════════════════
view = st.session_state.cb_view


# ── WELCOME ───────────────────────────────────────────────────────────────────
if view == "welcome":
    # Hero
    st.markdown(
        """
<div style="background:linear-gradient(135deg,#1a3d28 0%,#2f7d4c 55%,#1a3d28 100%);
border-radius:20px;padding:2.2rem 2.6rem 2rem;margin-bottom:1.6rem;
box-shadow:0 16px 48px rgba(47,125,76,0.24);position:relative;overflow:hidden;">
  <div style="position:absolute;top:-40px;right:-40px;width:220px;height:220px;
  border-radius:50%;background:rgba(255,255,255,0.04);pointer-events:none;"></div>
  <div style="position:absolute;bottom:-60px;left:30%;width:280px;height:280px;
  border-radius:50%;background:rgba(255,255,255,0.03);pointer-events:none;"></div>
  <h2 style="color:#fff;font-size:2.1rem;font-weight:700;margin:0.65rem 0 0.45rem;
  letter-spacing:-0.025em;font-family:'Source Serif 4',serif;">Krishi Pracharak</h2>
  <p style="color:rgba(255,255,255,0.78);font-size:0.96rem;margin:0 0 1.1rem;max-width:560px;
  line-height:1.65;">AI-driven targeting across 6,000+ growers — score, segment, generate
  multilingual content, and brief field reps. Select a campaign or start a new one.</p>
  <div style="display:flex;gap:1rem;flex-wrap:wrap;">
    <div style="background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.18);
    border-radius:12px;padding:0.7rem 1.1rem;">
      <div style="color:#fff;font-size:1.4rem;font-weight:700;font-family:'Source Serif 4',serif;">6,000+</div>
      <div style="color:rgba(255,255,255,0.6);font-size:0.68rem;text-transform:uppercase;letter-spacing:0.06em;">Farmers Tracked</div>
    </div>
    <div style="background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.18);
    border-radius:12px;padding:0.7rem 1.1rem;">
      <div style="color:#fff;font-size:1.4rem;font-weight:700;font-family:'Source Serif 4',serif;">10</div>
      <div style="color:rgba(255,255,255,0.6);font-size:0.68rem;text-transform:uppercase;letter-spacing:0.06em;">States Covered</div>
    </div>
    <div style="background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.18);
    border-radius:12px;padding:0.7rem 1.1rem;">
      <div style="color:#fff;font-size:1.4rem;font-weight:700;font-family:'Source Serif 4',serif;">6</div>
      <div style="color:rgba(255,255,255,0.6);font-size:0.68rem;text-transform:uppercase;letter-spacing:0.06em;">Languages</div>
    </div>
    <div style="background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.18);
    border-radius:12px;padding:0.7rem 1.1rem;">
      <div style="color:#ffd8a0;font-size:1.4rem;font-weight:700;font-family:'Source Serif 4',serif;">4</div>
      <div style="color:rgba(255,255,255,0.6);font-size:0.68rem;text-transform:uppercase;letter-spacing:0.06em;">AI Personas</div>
    </div>
  </div>
</div>""",
        unsafe_allow_html=True,
    )

    # Key metrics
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Total Campaigns",   len(digital) + len(saved_camps))
    s2.metric("Total Impressions", _fmt(funnel_df["social_post_impression"].sum()))
    s3.metric("Total Visits",      _fmt(funnel_df["landing_page_visits"].sum()))
    s4.metric("Total Leads",       _fmt(funnel_df["lead_form_submission"].sum()))

    st.markdown("<div style='margin-top:1.2rem;'></div>", unsafe_allow_html=True)

    # ── Unified campaign grid (digital + AI, no division) ─────────────────────
    all_card_cols = st.columns(2, gap="medium")
    col_idx = 0

    # Digital campaign cards
    for dc in digital:
        with all_card_cols[col_idx % 2]:
            visit_badge = (
                f'<span style="background:#e8f5e9;color:#1a5c35;border-radius:999px;'
                f'padding:0.1rem 0.5rem;font-size:0.68rem;font-weight:600;">'
                f'Visit {dc["visit_rate"]:.1f}%</span>'
            )
            lead_badge = (
                f'<span style="background:#fff3e0;color:#c07a2b;border-radius:999px;'
                f'padding:0.1rem 0.5rem;font-size:0.68rem;font-weight:600;">'
                f'Lead {dc["lead_rate"]:.1f}%</span>'
            )
            st.markdown(
                f'<div class="kp-camp-card">'
                f'<div class="kp-camp-typetag">{dc["crop"].title()}</div>'
                f'<div class="kp-camp-name">{dc["id"]}</div>'
                f'<div class="kp-camp-meta">{dc["product"]} &nbsp;·&nbsp; {dc["start"]} → {dc["end"]}</div>'
                f'<div class="kp-camp-stats">'
                f'<div><div class="kp-camp-stat-val">{_fmt(dc["impressions"])}</div>'
                f'<div class="kp-camp-stat-lbl">Impressions</div></div>'
                f'<div><div class="kp-camp-stat-val">{_fmt(dc["visits"])}</div>'
                f'<div class="kp-camp-stat-lbl">Visits</div></div>'
                f'<div><div class="kp-camp-stat-val">{_fmt(dc["leads"])}</div>'
                f'<div class="kp-camp-stat-lbl">Leads</div></div>'
                f'</div>'
                f'<div style="margin-top:0.6rem;display:flex;gap:0.4rem;">{visit_badge}{lead_badge}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(f"Open {dc['id']}", key=f"wc_{dc['id']}", use_container_width=True,
                         help=f"Open {dc['id']}"):
                st.session_state.cb_view = dc["id"]
                st.session_state.targeting_plan = None
                st.session_state.content_variants = None
                st.session_state.current_campaign_path = None
                st.session_state.rep_briefing_result = None
                st.session_state.rep_briefing_rep = None
                st.rerun()
        col_idx += 1

    # AI / saved campaign cards — same grid, continued
    for sc in saved_camps:
        with all_card_cols[col_idx % 2]:
            sc_name    = sc.get("campaign_name") or sc["_filename"].replace(".json", "")
            sc_segs    = sc.get("segments", [])
            sc_growers = sum(s.get("grower_count", 0) for s in sc_segs)
            sc_date    = sc.get("generated_at", "")[:10] or "—"
            sc_obj     = sc.get("campaign_objective", "")
            is_draft   = sc.get("stub", False) or not sc_segs
            status_badge = (
                '<span style="background:#f0f0f0;color:#888;border-radius:999px;'
                'padding:0.1rem 0.5rem;font-size:0.66rem;font-weight:600;">⚙ Draft</span>'
                if is_draft else
                f'<span style="background:#e8f5e9;color:#1a5c35;border-radius:999px;'
                f'padding:0.1rem 0.5rem;font-size:0.66rem;font-weight:600;">'
                f'✓ {len(sc_segs)} seg · {sc_growers:,} growers</span>'
            )
            type_label = sc_obj if sc_obj else "AI Campaign"
            st.markdown(
                f'<div class="kp-camp-card">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
                f'<div style="flex:1;min-width:0;">'
                f'<div class="kp-camp-typetag">{type_label}</div>'
                f'<div class="kp-camp-name">{sc_name}</div>'
                f'<div class="kp-camp-meta">Created {sc_date}</div>'
                f'</div>'
                f'<div style="margin-left:0.5rem;flex-shrink:0;">{status_badge}</div>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(f"Open {sc_name}", key=f"wsc_{sc['_id']}", use_container_width=True,
                         help=f"Open {sc_name}"):
                st.session_state.cb_view = sc["_id"]
                st.session_state.targeting_plan = {
                    k: v for k, v in sc.items() if not str(k).startswith("_")
                }
                st.session_state.content_variants     = sc.get("content_variants")
                st.session_state.current_campaign_path = sc.get("_path")
                st.session_state.rep_briefing_result  = None
                st.session_state.rep_briefing_rep     = None
                st.rerun()
        col_idx += 1


# ── DIGITAL CAMPAIGN ──────────────────────────────────────────────────────────
elif any(c["id"] == view for c in digital):
    c = next(x for x in digital if x["id"] == view)

    st.markdown(
        f"""
<div style="background:linear-gradient(135deg,#1a3d28 0%,#2f7d4c 55%,#1a3d28 100%);
border-radius:18px;padding:1.6rem 2rem 1.4rem;margin-bottom:1.5rem;
box-shadow:0 12px 36px rgba(47,125,76,0.2);">
  <div style="font-size:0.72rem;font-weight:600;letter-spacing:0.08em;
  color:rgba(212,237,218,0.7);text-transform:uppercase;margin-bottom:0.3rem;">Digital Campaign</div>
  <h2 style="color:#fff;font-size:1.7rem;font-weight:700;margin:0 0 0.25rem;
  letter-spacing:-0.02em;">{c['id']}</h2>
  <div style="color:rgba(255,255,255,0.78);font-size:0.92rem;margin-bottom:0.8rem;">
    {c['crop'].title()} &nbsp;·&nbsp; {c['product']} &nbsp;·&nbsp; {c['start']} → {c['end']}
  </div>
  <div style="display:flex;gap:1.4rem;flex-wrap:wrap;">
    <span style="color:#fff;font-size:0.88rem;"><strong>{_fmt(c['impressions'])}</strong>
    <span style="opacity:.7;font-size:0.78rem;"> Impressions</span></span>
    <span style="color:#fff;font-size:0.88rem;"><strong>{_fmt(c['visits'])}</strong>
    <span style="opacity:.7;font-size:0.78rem;"> Visits</span></span>
    <span style="color:#fff;font-size:0.88rem;"><strong>{_fmt(c['leads'])}</strong>
    <span style="opacity:.7;font-size:0.78rem;"> Leads</span></span>
    <span style="background:rgba(255,255,255,0.15);border-radius:999px;padding:0.18rem 0.7rem;
    font-size:0.78rem;color:#d4edda;font-weight:600;">Visit {c['visit_rate']:.1f}%</span>
    <span style="background:rgba(192,122,43,0.35);border-radius:999px;padding:0.18rem 0.7rem;
    font-size:0.78rem;color:#ffd8a0;font-weight:600;">Lead {c['lead_rate']:.1f}%</span>
  </div>
</div>""",
        unsafe_allow_html=True,
    )

    tab_ov, tab_cg, tab_rx, tab_rb = st.tabs(
        ["Overview", "Content Generation", "Receptivity", "Rep Briefing"]
    )

    with tab_ov:
        grower_state_map = _grower_states_by_crop(c["crop"])
        weeks_ts = [pd.Timestamp(w) for w in c["weeks"]]

        if grower_state_map and weeks_ts:
            ov1, ov2 = st.columns([3, 2])
            with ov1:
                gn_rows = [{"Campaign": c["id"], "Start": weeks_ts[0],
                            "Finish": weeks_ts[-1] + timedelta(days=7), "Type": "Active Period"}]
                fig_gn = px.timeline(pd.DataFrame(gn_rows), x_start="Start", x_end="Finish",
                                     y="Campaign", color="Type",
                                     color_discrete_sequence=[_GREEN])
                fig_gn.update_layout(**_layout_with(height=100, showlegend=False,
                                                     margin=dict(l=10, r=10, t=20, b=10)))
                fig_gn.update_yaxes(autorange="reversed")
                st.plotly_chart(fig_gn, use_container_width=True, config={"displayModeBar": False})

                fig_sp = go.Figure(go.Scatter(
                    x=c["weeks"], y=c["weekly_imp"], mode="lines",
                    line=dict(color=_GREEN, width=2),
                    fill="tozeroy", fillcolor="rgba(47,125,76,0.12)", hoverinfo="skip",
                ))
                fig_sp.update_layout(**_layout_with(
                    height=160,
                    xaxis=dict(visible=True, showgrid=False),
                    yaxis=dict(visible=True, showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
                    showlegend=False, xaxis_title="Week", yaxis_title="Impressions",
                ))
                st.plotly_chart(fig_sp, use_container_width=True, config={"displayModeBar": False})

            with ov2:
                st.markdown("**Active States**")
                _render_geo_map(grower_state_map)
        elif weeks_ts:
            # No grower-state data — show timeline only (full width)
            gn_rows = [{"Campaign": c["id"], "Start": weeks_ts[0],
                        "Finish": weeks_ts[-1] + timedelta(days=7), "Type": "Active Period"}]
            fig_gn = px.timeline(pd.DataFrame(gn_rows), x_start="Start", x_end="Finish",
                                 y="Campaign", color="Type",
                                 color_discrete_sequence=[_GREEN])
            fig_gn.update_layout(**_layout_with(height=100, showlegend=False,
                                                 margin=dict(l=10, r=10, t=20, b=10)))
            fig_gn.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_gn, use_container_width=True, config={"displayModeBar": False})

            fig_sp = go.Figure(go.Scatter(
                x=c["weeks"], y=c["weekly_imp"], mode="lines",
                line=dict(color=_GREEN, width=2),
                fill="tozeroy", fillcolor="rgba(47,125,76,0.12)", hoverinfo="skip",
            ))
            fig_sp.update_layout(**_layout_with(
                height=160,
                xaxis=dict(visible=True, showgrid=False),
                yaxis=dict(visible=True, showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
                showlegend=False, xaxis_title="Week", yaxis_title="Impressions",
            ))
            st.plotly_chart(fig_sp, use_container_width=True, config={"displayModeBar": False})

        if grower_state_map:
            st.markdown("**Field Conditions**")
            _render_weather_cards(list(grower_state_map.keys())[:5])

        st.markdown("#### Weekly Breakdown")
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
            ref_date  = f1.date_input("Reference Date", value=REFERENCE_DATE, key=f"date_{view}")
            state_sel = f2.selectbox("State", ["All"] + unique_states, key=f"state_{view}")
            state_arg = None if state_sel == "All" else state_sel
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
            p1.metric("Growers Scored",  qs_plan.get("total_growers", "—"))
            p2.metric("Eligible",        plan.get("total_eligible", "—"))
            p3.metric("Segments",        len(segs_plan))
            p4.metric("OOS Blocked",     len(plan.get("oos_blocked", [])))

            # ── Step 2: Scope preview + Promoter + Generate ───────────────────
            st.markdown("#### Content Scope")
            _render_content_scope(segs_plan)
            _render_promoter_uploader(key_prefix=f"promo_{view}")

            if not variants:
                if st.button("Generate Multilingual Content →", type="primary",
                             use_container_width=True, key=f"gen_{view}"):
                    with st.spinner("Generating content for all segments…"):
                        st.session_state.content_variants = run_content_generation(
                            plan,
                            promoter_image_b64=st.session_state.get("promoter_image_b64"),
                        )
                        _persist_variants(st.session_state.content_variants)
                    st.rerun()
            else:
                rc1, rc2 = st.columns([4, 1])
                rc1.success(f"Content generated for {len(variants.get('variants', {}))} segments.")
                if rc2.button("Regenerate", key=f"regen_{view}"):
                    with st.spinner("Regenerating…"):
                        st.session_state.content_variants = run_content_generation(
                            plan,
                            promoter_image_b64=st.session_state.get("promoter_image_b64"),
                        )
                        _persist_variants(st.session_state.content_variants)
                    st.rerun()

        st.divider()
        _render_content_variants()

    with tab_rx:
        _render_receptivity(crop_filter=c["crop"])

    with tab_rb:
        _render_rep_briefing_tab(campaign_path=st.session_state.current_campaign_path)


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
    _stats_html = (
        f'<span style="color:#fff;font-size:0.88rem;"><strong>{qs.get("total_growers","—")}</strong>'
        f'<span style="opacity:.7;font-size:0.78rem;"> Scored</span></span>'
        f'<span style="color:#fff;font-size:0.88rem;"><strong>{c.get("total_eligible","—")}</strong>'
        f'<span style="opacity:.7;font-size:0.78rem;"> Eligible</span></span>'
        f'<span style="color:#fff;font-size:0.88rem;"><strong>{len(segs)}</strong>'
        f'<span style="opacity:.7;font-size:0.78rem;"> Segments</span></span>'
        f'<span style="background:rgba(192,122,43,0.35);border-radius:999px;padding:0.18rem 0.7rem;'
        f'font-size:0.78rem;color:#ffd8a0;font-weight:600;">'
        f'{len(c.get("oos_blocked", []))} OOS blocked</span>'
    )

    st.markdown(
        f"""
<div style="background:linear-gradient(135deg,#1a3d28 0%,#2f7d4c 55%,#1a3d28 100%);
border-radius:18px;padding:1.6rem 2rem 1.4rem;margin-bottom:1.5rem;
box-shadow:0 12px 36px rgba(47,125,76,0.2);">
  <div style="font-size:0.72rem;font-weight:600;letter-spacing:0.08em;
  color:rgba(212,237,218,0.7);text-transform:uppercase;margin-bottom:0.3rem;">
  {camp_obj or 'AI Campaign'}</div>
  <h2 style="color:#fff;font-size:1.7rem;font-weight:700;margin:0 0 0.25rem;
  letter-spacing:-0.02em;">{camp_name}</h2>
  <div style="color:rgba(255,255,255,0.78);font-size:0.92rem;margin-bottom:0.8rem;">
    {', '.join(crops) if crops else '—'} &nbsp;·&nbsp; Created {gen_at}
    {f" &nbsp;·&nbsp; {date_win['start']} → {date_win['end']}" if date_win.get('start') else ""}
  </div>
  <div style="display:flex;gap:1.4rem;flex-wrap:wrap;">
    {_draft_badge if is_stub else _stats_html}
  </div>
</div>""",
        unsafe_allow_html=True,
    )

    tab_ov, tab_cg, tab_rx, tab_rb = st.tabs(
        ["Overview", "Content Generation", "Receptivity", "Rep Briefing"]
    )

    with tab_ov:
        if is_stub:
            # ── Targeting form for new/draft campaigns ─────────────────────────
            st.markdown("### Configure Campaign Targeting")
            st.caption("This campaign hasn't been run yet. Set your targeting parameters below.")
            growers_df = load_growers()
            raw_crops  = (growers_df["grower_crop_calendar"].dropna()
                          .apply(lambda x: x.get("crop", "") if isinstance(x, dict) else ""))
            unique_crops  = sorted(cc for cc in raw_crops.unique() if cc)
            unique_states = sorted(growers_df["state"].dropna().unique().tolist())

            f1, f2, f3 = st.columns(3)
            objective    = f1.selectbox("Objective", OBJECTIVES, key=f"stub_obj_{view}")
            crop_filter  = f2.selectbox("Crop",  ["All"] + unique_crops, key=f"stub_crop_{view}")
            state_filter = f3.selectbox("State", ["All"] + unique_states, key=f"stub_state_{view}")
            crop_arg  = None if crop_filter  == "All" else crop_filter
            state_arg = None if state_filter == "All" else state_filter

            d1, d2, d3 = st.columns(3)
            start_date  = d1.date_input("Campaign Start", value=REFERENCE_DATE,
                                        key=f"stub_start_{view}")
            end_date    = d2.date_input("Campaign End",   value=date(2026, 3, 31),
                                        key=f"stub_end_{view}")
            channel_mix = d3.multiselect("Channel Mix",
                                         ["WhatsApp", "SMS", "IVR", "Rep Assist"],
                                         default=["WhatsApp", "SMS", "IVR"],
                                         key=f"stub_channels_{view}")

            with st.expander("Optional: Budget"):
                budget_val = st.number_input("Budget (INR)", min_value=0, value=0,
                                             step=5000, key=f"stub_budget_{view}")
                budget_arg = int(budget_val) if budget_val else None

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
                    if budget_arg:
                        plan["budget_inr"] = budget_arg
                    st.session_state.targeting_plan   = plan
                    st.session_state.content_variants = None
                    _persist_plan(plan, source_meta={
                        "source_type":  "new_campaign",
                        "source_crop":  crop_arg,
                        "state_filter": state_arg,
                    })
                st.rerun()

            if gen_clicked:
                with st.spinner("Generating multilingual content…"):
                    st.session_state.content_variants = run_content_generation(
                        st.session_state.targeting_plan
                    )
                    _persist_variants(st.session_state.content_variants)
                st.rerun()

            # Show preview if plan was just built in this session
            plan = st.session_state.targeting_plan
            if plan and plan.get("segments"):
                st.divider()
                st.info(plan.get("rationale", "-"))
                qsp = plan.get("quality_summary", {})
                mm1, mm2, mm3, mm4 = st.columns(4)
                mm1.metric("Growers Scored",       qsp.get("total_growers", "-"))
                mm2.metric("Eligible",             plan.get("total_eligible", "-"))
                mm3.metric("Pre-OOS Eligible",     plan.get("total_eligible_pre_oos", "-"))
                mm4.metric("No Digital Channel",   qsp.get("non_smartphone", "-"))
                segs_new = plan.get("segments", [])
                if segs_new:
                    dw = plan.get("date_window") or {}
                    _render_segment_overview(segs_new, plan.get("reference_date", start_date), dw)
                    st.divider()
                    st.markdown(f"#### Targeting Segments ({len(segs_new)})")
                    st.dataframe(pd.DataFrame([{
                        "ID": s["segment_id"], "Crop": s["crop"].title(),
                        "State": s["state"], "Language": s["language"],
                        "Channel": s["channel"], "Persona": s["persona"],
                        "Product": s["product"], "Stage": s["stage_context"],
                        "Growers": s["grower_count"], "Avg Score": s["avg_score"],
                    } for s in segs_new]), use_container_width=True, hide_index=True)
        else:
            # ── Normal saved campaign overview ─────────────────────────────────
            if c.get("rationale"):
                st.info(c["rationale"])
            if c.get("oos_blocked"):
                grouped_oos = _summarize_oos_blocks(c["oos_blocked"])
                st.warning(
                    f"**{len(c['oos_blocked'])} campaign(s) paused — "
                    f"{len(grouped_oos)} grouped out-of-stock risk bucket(s)**\n\n"
                    + "\n".join(
                        f"- **{b['crop'].title()}** in {b['state']}: {b['product']} "
                        f"({b['grower_count']} growers) — {b['reason']}"
                        for b in grouped_oos
                    )
                )
            if segs:
                _render_segment_overview(segs, c.get("reference_date", date.today()),
                                         date_win or None)
                st.divider()
                st.markdown(f"#### Targeting Segments ({len(segs)})")
                st.dataframe(pd.DataFrame([{
                    "ID": s["segment_id"], "Crop": s["crop"].title(),
                    "State": s["state"], "Language": s["language"],
                    "Channel": s["channel"], "Persona": s["persona"],
                    "Product": s["product"], "Stage": s["stage_context"],
                    "Growers": s["grower_count"], "Avg Score": s["avg_score"],
                } for s in segs]), use_container_width=True, hide_index=True)
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
            p1.metric("Growers Scored", qs_c.get("total_growers", "—"))
            p2.metric("Eligible",       c.get("total_eligible", "—"))
            p3.metric("Segments",       len(segs))
            p4.metric("OOS Blocked",    len(c.get("oos_blocked", [])))
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
                    with st.spinner("Regenerating multilingual content…"):
                        st.session_state.content_variants = run_content_generation(
                            st.session_state.targeting_plan,
                            promoter_image_b64=st.session_state.get("promoter_image_b64"),
                        )
                        _persist_variants(st.session_state.content_variants)
                    st.rerun()
            else:
                st.session_state.content_variants = None
                if st.button("Generate Multilingual Content →", type="primary",
                             use_container_width=True, key=f"gen_saved_{c['_id']}"):
                    with st.spinner("Generating multilingual content for all segments…"):
                        st.session_state.content_variants = run_content_generation(
                            st.session_state.targeting_plan,
                            promoter_image_b64=st.session_state.get("promoter_image_b64"),
                        )
                        _persist_variants(st.session_state.content_variants)
                    st.rerun()

            st.divider()
            _render_content_variants()

    with tab_rx:
        unique_seg_crops = {s.get("crop") for s in segs if s.get("crop")}
        crop_f = next(iter(unique_seg_crops)) if len(unique_seg_crops) == 1 else None
        _render_receptivity(crop_filter=crop_f)

    with tab_rb:
        _render_rep_briefing_tab(campaign_path=c.get("_path"))


# ── FALLBACK (deleted or unknown view — reset to welcome) ─────────────────────
else:
    st.session_state.cb_view = "welcome"
    st.rerun()
