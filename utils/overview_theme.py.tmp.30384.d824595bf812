"""
CSS and HTML helpers for the Campaign Overview tab.
Covers: campaign header banner, stat pills, weather cards, section dividers,
AI agent insight block, OOS warning block, and segment overview.
"""
import streamlit as st


def inject_overview_css() -> None:
    st.markdown("""
<style>
/* ── Campaign header banner ──────────────────────────────────────────────────── */
.kp-camp-header {
  background: #0f1f15;
  border-radius: 16px;
  padding: 1.6rem 2rem 1.5rem;
  margin-bottom: 1.6rem;
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(47,125,76,0.2);
}
.kp-camp-header::before {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse 600px 300px at 80% 50%,
    rgba(47,125,76,0.18) 0%, transparent 70%);
  pointer-events: none;
}
.kp-camp-header-kicker {
  font-size: 0.63rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: rgba(160,210,175,0.55);
  margin-bottom: 0.45rem;
}
.kp-camp-header-title {
  font-family: "Source Serif 4", serif;
  font-size: 1.9rem;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: -0.025em;
  margin: 0 0 0.3rem;
  line-height: 1.1;
}
.kp-camp-header-meta {
  font-size: 0.85rem;
  color: rgba(200,230,210,0.65);
  margin-bottom: 1rem;
}
.kp-camp-header-pills {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.kp-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  border-radius: 999px;
  padding: 0.22rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 600;
  line-height: 1;
}
.kp-pill-white {
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.15);
  color: rgba(220,240,228,0.9);
}
.kp-pill-green {
  background: rgba(47,125,76,0.35);
  border: 1px solid rgba(47,125,76,0.5);
  color: #a8e6be;
}
.kp-pill-amber {
  background: rgba(184,112,31,0.3);
  border: 1px solid rgba(184,112,31,0.45);
  color: #ffd090;
}
.kp-pill-draft {
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.12);
  color: rgba(200,220,205,0.6);
}

/* ── Section label ───────────────────────────────────────────────────────────── */
.kp-ov-section {
  font-family: "Source Serif 4", serif;
  font-size: 1rem;
  font-weight: 700;
  color: #1a2520;
  letter-spacing: -0.01em;
  margin: 1.4rem 0 0.7rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #e8e4da;
}

/* ── Chart wrapper ───────────────────────────────────────────────────────────── */
.kp-chart-wrap {
  background: #fffdf7;
  border: 1px solid #e8e4da;
  border-radius: 14px;
  padding: 1rem 1.1rem 0.6rem;
  box-shadow: 0 1px 4px rgba(26,37,32,0.04);
  margin-bottom: 0.8rem;
}
.kp-chart-label {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: #8a9e92;
  margin-bottom: 0.5rem;
}

/* ── Weather / field condition cards ─────────────────────────────────────────── */
.kp-weather-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 0.7rem;
  margin-bottom: 1rem;
}
.kp-weather-card {
  background: #fffdf7;
  border: 1px solid #e8e4da;
  border-radius: 12px;
  padding: 0.9rem 1rem 0.8rem;
  box-shadow: 0 1px 4px rgba(26,37,32,0.04);
  transition: border-color 0.15s;
}
.kp-weather-card:hover { border-color: #b8d4be; }
.kp-weather-city {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #8a9e92;
  margin-bottom: 0.3rem;
}
.kp-weather-temp {
  font-family: "Source Serif 4", serif;
  font-size: 1.6rem;
  font-weight: 700;
  color: #1a2520;
  line-height: 1;
  margin-bottom: 0.15rem;
}
.kp-weather-cond {
  font-size: 0.74rem;
  color: #6b7c72;
}
.kp-weather-detail {
  font-size: 0.68rem;
  color: #8a9e92;
  margin-top: 0.35rem;
}
.kp-weather-alert {
  font-size: 0.7rem;
  font-weight: 600;
  margin-top: 0.4rem;
  padding: 0.2rem 0.5rem;
  border-radius: 999px;
  display: inline-block;
}
.kp-weather-alert-fungal { background: #fdf0e0; color: #b8701f; }
.kp-weather-alert-pest   { background: #fef2f2; color: #b83232; }
.kp-weather-alert-ok     { background: #eef7f1; color: #2f7d4c; }

/* ── AI agent insight block ──────────────────────────────────────────────────── */
.kp-agent-block {
  background: #0a1910;
  border: 1px solid rgba(47,125,76,0.3);
  border-radius: 14px;
  padding: 1.1rem 1.3rem;
  margin-bottom: 1rem;
  position: relative;
  overflow: hidden;
}
.kp-agent-block::before {
  content: "";
  position: absolute;
  top: 0; left: 0;
  right: 0; height: 2px;
  background: linear-gradient(90deg, #2f7d4c, transparent);
}
.kp-agent-kicker {
  font-size: 0.63rem;
  font-weight: 700;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: rgba(160,210,175,0.55);
  margin-bottom: 0.45rem;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}
.kp-agent-text {
  font-size: 0.88rem;
  color: rgba(212,237,218,0.88);
  line-height: 1.65;
}

/* ── OOS warning ─────────────────────────────────────────────────────────────── */
.kp-oos-block {
  background: #fdf6ed;
  border: 1px solid #e8c87a;
  border-left: 4px solid #b8701f;
  border-radius: 0 10px 10px 0;
  padding: 0.85rem 1.1rem;
  margin-bottom: 1rem;
}
.kp-oos-title {
  font-size: 0.82rem;
  font-weight: 700;
  color: #7a4e10;
  margin-bottom: 0.4rem;
}
.kp-oos-item {
  font-size: 0.78rem;
  color: #8a6020;
  line-height: 1.6;
}

/* ── Segment overview stat row ───────────────────────────────────────────────── */
.kp-seg-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.8rem;
  margin-bottom: 1.2rem;
}
.kp-seg-stat-card {
  background: #fffdf7;
  border: 1px solid #e8e4da;
  border-radius: 12px;
  padding: 0.9rem 1rem;
  box-shadow: 0 1px 4px rgba(26,37,32,0.04);
  text-align: center;
}
.kp-seg-stat-val {
  font-family: "Source Serif 4", serif;
  font-size: 1.7rem;
  font-weight: 700;
  color: #1a2520;
  line-height: 1;
  margin-bottom: 0.2rem;
}
.kp-seg-stat-val-g { color: #2f7d4c; }
.kp-seg-stat-lbl {
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #8a9e92;
}

/* ── Weekly table wrapper ────────────────────────────────────────────────────── */
.kp-table-wrap {
  background: #fffdf7;
  border: 1px solid #e8e4da;
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(26,37,32,0.04);
  margin-top: 0.5rem;
}
</style>
""", unsafe_allow_html=True)


def camp_header_html(
    title: str,
    kicker: str,
    meta: str,
    pills: list[tuple[str, str]],   # [(label, style: white|green|amber|draft)]
) -> str:
    pills_html = "".join(
        f'<span class="kp-pill kp-pill-{style}">{label}</span>'
        for label, style in pills
    )
    return (
        f'<div class="kp-camp-header">'
        f'<div class="kp-camp-header-kicker">{kicker}</div>'
        f'<div class="kp-camp-header-title">{title}</div>'
        f'<div class="kp-camp-header-meta">{meta}</div>'
        f'<div class="kp-camp-header-pills">{pills_html}</div>'
        f'</div>'
    )


def section_label(text: str) -> None:
    st.markdown(f'<div class="kp-ov-section">{text}</div>', unsafe_allow_html=True)


def agent_block_html(kicker: str, body: str) -> str:
    return (
        f'<div class="kp-agent-block">'
        f'<div class="kp-agent-kicker">🤖 {kicker}</div>'
        f'<div class="kp-agent-text">{body}</div>'
        f'</div>'
    )


def oos_block_html(title: str, items: list[str]) -> str:
    rows = "".join(f'<div class="kp-oos-item">· {i}</div>' for i in items)
    return (
        f'<div class="kp-oos-block">'
        f'<div class="kp-oos-title">⚠ {title}</div>'
        f'{rows}'
        f'</div>'
    )


def seg_stats_html(scored: int, eligible: int, non_smartphone: int, segments: int) -> str:
    def card(val, lbl, green=False):
        cls = "kp-seg-stat-val-g" if green else ""
        return (
            f'<div class="kp-seg-stat-card">'
            f'<div class="kp-seg-stat-val {cls}">{val:,}</div>'
            f'<div class="kp-seg-stat-lbl">{lbl}</div>'
            f'</div>'
        )
    return (
        f'<div class="kp-seg-stats">'
        + card(scored, "Growers scored")
        + card(eligible, "Eligible", green=True)
        + card(segments, "Segments")
        + card(non_smartphone, "Offline growers")
        + f'</div>'
    )
