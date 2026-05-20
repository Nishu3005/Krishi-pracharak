import streamlit as st


def apply_theme() -> None:
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,500;8..60,700&display=swap');

:root {
  --bg: #f6f2e8;
  --paper: #fffdf7;
  --ink: #1d2a22;
  --muted: #4f6157;
  --accent: #2f7d4c;
  --accent-soft: #d6ead9;
  --signal: #c07a2b;
  --line: #d7d2c7;
}

.stApp {
  background:
    radial-gradient(900px 400px at 10% -10%, #e7f4ea 0%, transparent 55%),
    radial-gradient(1100px 450px at 95% 0%, #f5e8d2 0%, transparent 50%),
    var(--bg);
  color: var(--ink);
}

html, body, [class*="css"] {
  font-family: "Space Grotesk", sans-serif;
}

h1, h2, h3 {
  font-family: "Source Serif 4", serif;
  color: var(--ink);
  letter-spacing: -0.02em;
}

.hero-wrap {
  border: 1px solid var(--line);
  border-radius: 18px;
  background: linear-gradient(145deg, #fffef9 0%, #f8f4ea 100%);
  padding: 1rem 1.1rem 1rem 1.1rem;
  margin-bottom: 0.9rem;
  box-shadow: 0 8px 22px rgba(34, 55, 41, 0.08);
  animation: rise 360ms ease-out;
}

.hero-kicker {
  display: inline-block;
  color: var(--accent);
  background: var(--accent-soft);
  border-radius: 999px;
  padding: 0.2rem 0.6rem;
  font-size: 0.72rem;
  margin-bottom: 0.55rem;
  font-weight: 600;
}

.hero-title {
  margin: 0;
  line-height: 1.1;
}

.hero-sub {
  margin: 0.42rem 0 0;
  color: var(--muted);
  font-size: 0.96rem;
}

.stButton > button {
  border-radius: 12px;
  border: 1px solid #b8c9ba;
}

.stDownloadButton > button {
  border-radius: 12px;
}

[data-testid="stMetricValue"] {
  color: var(--ink);
}

.stTabs [data-baseweb="tab-list"] {
  gap: 0.45rem;
}

.stTabs [data-baseweb="tab"] {
  border-radius: 10px;
  border: 1px solid var(--line);
  background: #fcf9f1;
  padding-left: 0.85rem;
  padding-right: 0.85rem;
}

.stTabs [aria-selected="true"] {
  border-color: #9fbeaa !important;
  background: #f0f7f2 !important;
}

.stDataFrame, .stPlotlyChart {
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 0.35rem;
  background: var(--paper);
}

@keyframes rise {
  from { transform: translateY(7px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

/* ── Sidebar nav ─────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
  background: linear-gradient(175deg, #122b1c 0%, #0d1f14 60%, #091510 100%) !important;
  border-right: 1px solid rgba(47,125,76,0.25) !important;
}

section[data-testid="stSidebar"] > div:first-child {
  padding-top: 1.25rem;
}

/* Brand header injected above nav */
[data-testid="stSidebarNav"]::before {
  content: "🌾  Krishi Pracharak";
  display: block;
  font-family: "Source Serif 4", serif;
  font-size: 1.05rem;
  font-weight: 700;
  color: #d4edda;
  padding: 0.1rem 1.1rem 1rem;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  margin-bottom: 0.75rem;
  letter-spacing: -0.01em;
}

/* Nav section label */
[data-testid="stSidebarNav"] {
  padding: 0 0.6rem;
}

/* Each page link */
[data-testid="stSidebarNavLink"] {
  border-radius: 10px !important;
  padding: 0.55rem 0.9rem !important;
  margin-bottom: 0.22rem !important;
  color: rgba(210,232,216,0.72) !important;
  background: transparent !important;
  border: 1px solid transparent !important;
  transition: background 0.18s, border-color 0.18s, color 0.18s !important;
  font-size: 0.875rem !important;
  font-weight: 500 !important;
}

[data-testid="stSidebarNavLink"]:hover {
  background: rgba(47,125,76,0.18) !important;
  border-color: rgba(47,125,76,0.35) !important;
  color: #d4edda !important;
}

[data-testid="stSidebarNavLink"][aria-current="page"] {
  background: rgba(47,125,76,0.32) !important;
  border-color: rgba(47,125,76,0.6) !important;
  color: #ffffff !important;
  font-weight: 600 !important;
  box-shadow: inset 3px 0 0 #2f7d4c;
}

/* Footer tag at bottom of sidebar */
section[data-testid="stSidebar"]::after {
  content: "Syngenta × IITM · 2026";
  display: block;
  position: absolute;
  bottom: 1.2rem;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 0.68rem;
  color: rgba(255,255,255,0.2);
  letter-spacing: 0.06em;
  font-family: "Space Grotesk", sans-serif;
}
</style>
""",
        unsafe_allow_html=True,
    )


def render_hero(title: str, subtitle: str, kicker: str = "Hackathon Demo") -> None:
    st.markdown(
        f"""
<div class="hero-wrap">
  <div class="hero-kicker">{kicker}</div>
  <h1 class="hero-title">{title}</h1>
  <p class="hero-sub">{subtitle}</p>
</div>
""",
        unsafe_allow_html=True,
    )
