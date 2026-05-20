import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from agents.content_agent import run_content_generation
from agents.targeting_agent import run_targeting
from utils.data_loader import load_digital_funnel, load_growers, load_whatsapp
from utils.ui_theme import apply_theme

st.set_page_config(page_title="Campaign Builder · Krishi Pracharak", layout="wide")
apply_theme()

# ── Sidebar sub-nav button style ──────────────────────────────────────────────
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
_GREEN = "#2f7d4c"
_AMBER = "#c07a2b"
_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=10, r=10, t=30, b=10),
    font=dict(color="#1d2a22", family="Space Grotesk"),
)
REFERENCE_DATE = date(2026, 1, 15)

SYNGENTA_IMAGES = [
    (
        "https://www.syngenta.com/sites/default/files/styles/small_full_width/public/2025-04/"
        "Medium%20res%20image-Sunflower%20field%20using%20regenerative%20agriculture%20practices.png.webp?itok=0qQ_r1ip",
        "Regenerative agriculture in practice",
    ),
    (
        "https://www.syngenta.com/sites/default/files/styles/s_c_556x320/public/2026-02/"
        "screen-ppt-png-hybrid-wheat_chartres_france_2018-3-2000x1333.jpg.webp?itok=ctew35Ro",
        "Hybrid wheat research",
    ),
    (
        "https://www.syngenta.com/sites/default/files/styles/s_c_266x320/public/2025-06/"
        "Grower_Nathan%20Miller.jpg.webp?itok=X7CAH5C5",
        "Grower partnership",
    ),
]

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in [("cb_view", "welcome"), ("targeting_plan", None), ("content_variants", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Helpers ───────────────────────────────────────────────────────────────────
def _fmt(n):
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000:     return f"{n/1_000:.1f}K"
    return str(int(n))


def _load_saved() -> list[dict]:
    data_dir = Path(__file__).parent.parent / "data"
    if not data_dir.exists():
        return []
    files = sorted(
        list(data_dir.glob("campaign_*.json")) + list(data_dir.glob("targeting_plan.json")),
        key=lambda p: p.stat().st_mtime, reverse=True,
    )
    out = []
    for p in files:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            d["_id"] = p.stem
            d["_filename"] = p.name
            out.append(d)
        except Exception:
            pass
    return out


@st.cache_data
def _scored_df():
    from utils.features import build_grower_features
    from utils.receptivity_score import score_dataframe
    return score_dataframe(build_grower_features(REFERENCE_DATE))


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


# ── Data ──────────────────────────────────────────────────────────────────────
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
        visit_rate=vis/imp*100 if imp else 0,
        lead_rate=ld/vis*100 if vis else 0,
        start=str(grp["week_start_date"].min())[:10],
        end=str(grp["week_start_date"].max())[:10],
        weeks=grp["week_start_date"].tolist(),
        weekly_imp=grp["social_post_impression"].tolist(),
    ))


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — campaign sub-list
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(
        '<p style="font-size:0.68rem;font-weight:700;letter-spacing:0.09em;'
        'color:rgba(180,220,190,0.55);text-transform:uppercase;margin:14px 0 5px 2px;">'
        'Campaigns</p>',
        unsafe_allow_html=True,
    )

    if _nav("Overview", "sb_welcome", st.session_state.cb_view == "welcome"):
        st.session_state.cb_view = "welcome"
        st.rerun()

    for c in digital:
        if _nav(c["id"], f"sb_{c['id']}", st.session_state.cb_view == c["id"]):
            st.session_state.cb_view = c["id"]
            st.session_state.targeting_plan = None
            st.session_state.content_variants = None
            st.rerun()

    for c in saved_camps:
        label = c["_filename"].replace(".json", "")
        if _nav(label, f"sb_{c['_id']}", st.session_state.cb_view == c["_id"]):
            st.session_state.cb_view = c["_id"]
            st.session_state.targeting_plan = None
            st.session_state.content_variants = None
            st.rerun()

    st.markdown(
        '<div style="border-top:1px solid rgba(255,255,255,0.08);margin:10px 0 6px;"></div>',
        unsafe_allow_html=True,
    )
    if _nav("＋  New Campaign", "sb_new", st.session_state.cb_view == "new"):
        st.session_state.cb_view = "new"
        st.session_state.targeting_plan = None
        st.session_state.content_variants = None
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN AREA
# ══════════════════════════════════════════════════════════════════════════════
view = st.session_state.cb_view


# ── Content variants renderer (shared) ───────────────────────────────────────
def _render_content_variants():
    plan     = st.session_state.targeting_plan
    variants = st.session_state.content_variants
    if not variants:
        st.info("Build a targeting plan and then click **Generate Content**.")
        return
    segs    = plan.get("segments",[]) if plan else []
    seg_map = {s["segment_id"]:s for s in segs}
    for seg_id, content in variants.get("variants",{}).items():
        seg   = seg_map.get(seg_id,{})
        label = (f"{seg_id} · {seg.get('crop','').title()} / "
                 f"{seg.get('state','')} / {content.get('persona','')} / "
                 f"{content.get('language','')}")
        with st.expander(label, expanded=False):
            t1,t2,t3,t4 = st.tabs(["WhatsApp","SMS","IVR Script","Poster"])
            with t1: st.write(content.get("whatsapp") or "_Not applicable_")
            with t2: st.write(content.get("sms") or "-")
            with t3: st.write(content.get("ivr_script") or "-")
            with t4:
                url = content.get("poster_image_url")
                if url:
                    st.image(url, use_container_width=True)
                    st.caption(content.get("poster_prompt_used",""))
                else:
                    st.warning("Poster image not available.")
    st.divider()
    d1,d2 = st.columns(2)
    with d1:
        st.download_button("⬇ Targeting Plan",
            json.dumps(plan,indent=2,ensure_ascii=False),
            "targeting_plan.json","application/json")
    with d2:
        st.download_button("⬇ Content Variants",
            json.dumps(variants,indent=2,ensure_ascii=False),
            "content_variants.json","application/json")


# ── Receptivity tab (shared renderer) ────────────────────────────────────────
def _render_receptivity(crop_filter: str | None = None):
    with st.spinner("Computing receptivity scores…"):
        df = _scored_df()
    wa = load_whatsapp()

    if crop_filter:
        crop_ids = df[df["crop"] == crop_filter]["grower_id"] if "crop" in df.columns else df["grower_id"]
        df  = df[df["grower_id"].isin(crop_ids)]
        wa  = wa[wa["campaign_crop"] == crop_filter] if "campaign_crop" in wa.columns else wa

    wa_df = wa.merge(
        df[["grower_id", "receptivity_score", "state", "farm_tier", "timing_mode"]],
        on="grower_id", how="left",
    )

    baseline_open = wa["opened_status"].mean() if len(wa) else 0
    top_q         = df["receptivity_score"].quantile(0.75)
    top_growers   = df[df["receptivity_score"] >= top_q]["grower_id"]
    top_wa        = wa[wa["grower_id"].isin(top_growers)]
    top_open      = top_wa["opened_status"].mean() if len(top_wa) else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Baseline Open Rate",    f"{baseline_open:.1%}")
    c2.metric("Top-Quartile Open Rate",f"{top_open:.1%}", delta=f"+{top_open - baseline_open:.1%}")
    c3.metric("Top-Quartile Growers",  len(top_growers))
    st.caption("Retrospective validation using the same dataset window used for scoring.")

    st.divider()
    l1, r1 = st.columns(2)

    with l1:
        st.markdown("**Score Distribution**")
        fig = px.histogram(df, x="receptivity_score", nbins=30, color_discrete_sequence=[_GREEN])
        fig.add_vline(x=0.30, line_dash="dash", line_color=_AMBER, annotation_text="Threshold")
        fig.update_layout(**_LAYOUT, xaxis_title="Receptivity Score", yaxis_title="Growers", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with r1:
        st.markdown("**Signal Contributions (Avg)**")
        bds = df["score_breakdown"].apply(lambda x: x.get("breakdown", {}) if isinstance(x, dict) else {})
        bd_df = pd.DataFrame(list(bds)).mean().reset_index()
        bd_df.columns = ["Signal", "Avg Contribution"]
        bd_df = bd_df.sort_values("Avg Contribution", ascending=True)
        fig2 = px.bar(bd_df, x="Avg Contribution", y="Signal", orientation="h",
                      color_discrete_sequence=[_GREEN])
        fig2.update_layout(**_LAYOUT)
        st.plotly_chart(fig2, use_container_width=True)

    l2, r2 = st.columns(2)
    with l2:
        st.markdown("**Open Rate by State**")
        state_data = (wa_df.groupby("state")
                      .agg(open_rate=("opened_status", "mean"))
                      .reset_index().sort_values("open_rate", ascending=False))
        fig3 = px.bar(state_data, x="state", y="open_rate",
                      color="open_rate", color_continuous_scale=[[0,"#d6ead9"],[1,_GREEN]],
                      labels={"open_rate":"Open Rate","state":"State"})
        fig3.add_hline(y=baseline_open, line_dash="dash", line_color=_AMBER, annotation_text="Baseline")
        fig3.update_layout(**_LAYOUT, xaxis_tickangle=-35)
        st.plotly_chart(fig3, use_container_width=True)

    with r2:
        st.markdown("**Open Rate by Farm Size Tier**")
        if "farm_tier" in df.columns:
            tier_df   = wa_df.merge(df[["grower_id","farm_tier"]], on="grower_id", how="left")
            tier_data = tier_df.groupby("farm_tier")["opened_status"].mean().reset_index()
            tier_data.columns = ["Farm Size Tier","Open Rate"]
            fig4 = px.bar(tier_data, x="Farm Size Tier", y="Open Rate",
                          color_discrete_sequence=["#3f9662"])
            fig4.add_hline(y=baseline_open, line_dash="dash", line_color=_AMBER)
            fig4.update_layout(**_LAYOUT)
            st.plotly_chart(fig4, use_container_width=True)

    l3, r3 = st.columns(2)
    with l3:
        st.markdown("**Channel Eligibility Split**")
        ch_df = df["device_type"].value_counts().reset_index()
        ch_df.columns = ["Device Type","Count"]
        fig5 = px.pie(ch_df, names="Device Type", values="Count",
                      color_discrete_sequence=[_GREEN,"#88bb97","#c7dcca"])
        fig5.update_layout(**_LAYOUT)
        st.plotly_chart(fig5, use_container_width=True)

    with r3:
        st.markdown("**Timing Mode Coverage**")
        tm_df = df["timing_mode"].value_counts().reset_index()
        tm_df.columns = ["Timing Mode","Count"]
        fig6 = px.pie(tm_df, names="Timing Mode", values="Count",
                      color_discrete_sequence=[_GREEN,"#6ea781","#d8e2d2"])
        fig6.update_layout(**_LAYOUT)
        st.plotly_chart(fig6, use_container_width=True)


# ── WELCOME ───────────────────────────────────────────────────────────────────
if view == "welcome":
    st.markdown(
        """
<div style="background:linear-gradient(135deg,#1a3d28 0%,#2f7d4c 60%,#1a3d28 100%);
border-radius:20px;padding:2rem 2.5rem 1.8rem;margin-bottom:1.8rem;
box-shadow:0 16px 48px rgba(47,125,76,0.22);">
  <span style="background:rgba(255,255,255,0.15);color:#d4edda;border-radius:999px;
  padding:0.22rem 0.8rem;font-size:0.72rem;font-weight:600;letter-spacing:0.06em;
  border:1px solid rgba(255,255,255,0.2);">SYNGENTA × IITM HACKATHON 2026</span>
  <h2 style="color:#fff;font-size:2rem;font-weight:700;margin:0.6rem 0 0.4rem;
  letter-spacing:-0.02em;">Campaign Builder</h2>
  <p style="color:rgba(255,255,255,0.80);font-size:0.97rem;margin:0;max-width:580px;
  line-height:1.65;">AI-driven targeting across 6,000+ growers — score, segment, generate
  multilingual content, and track receptivity. Select a campaign from the sidebar or start a new one.</p>
</div>""",
        unsafe_allow_html=True,
    )

    ic1, ic2, ic3 = st.columns(3)
    for col, (url, cap) in zip([ic1, ic2, ic3], SYNGENTA_IMAGES):
        col.markdown(
            f'<div style="border-radius:14px;overflow:hidden;border:1px solid #d7d2c7;'
            f'box-shadow:0 4px 14px rgba(0,0,0,0.07);">'
            f'<img src="{url}" style="width:100%;height:190px;object-fit:cover;display:block;"/>'
            f'<div style="padding:0.55rem 0.75rem;background:#fffdf7;font-size:0.76rem;'
            f'color:#4f6157;">{cap}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Campaigns",         len(digital) + len(saved_camps))
    s2.metric("Total Impressions", _fmt(funnel_df["social_post_impression"].sum()))
    s3.metric("Total Visits",      _fmt(funnel_df["landing_page_visits"].sum()))
    s4.metric("Total Leads",       _fmt(funnel_df["lead_form_submission"].sum()))


# ── DIGITAL CAMPAIGN ──────────────────────────────────────────────────────────
elif any(c["id"] == view for c in digital):
    c = next(x for x in digital if x["id"] == view)

    # Hero
    st.markdown(
        f"""
<div style="background:linear-gradient(135deg,#1a3d28 0%,#2f7d4c 55%,#1a3d28 100%);
border-radius:18px;padding:1.6rem 2rem 1.4rem;margin-bottom:1.5rem;
box-shadow:0 12px 36px rgba(47,125,76,0.2);">
  <div style="font-size:0.72rem;font-weight:600;letter-spacing:0.08em;
  color:rgba(212,237,218,0.7);text-transform:uppercase;margin-bottom:0.3rem;">
  Digital Campaign</div>
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

    tab_ov, tab_cg, tab_rx = st.tabs(["Overview", "Content Generation", "Receptivity"])

    with tab_ov:
        # Sparkline
        fig_sp = go.Figure(go.Scatter(
            x=c["weeks"], y=c["weekly_imp"], mode="lines",
            line=dict(color=_GREEN, width=2),
            fill="tozeroy", fillcolor="rgba(47,125,76,0.12)", hoverinfo="skip",
        ))
        fig_sp.update_layout(**_LAYOUT, height=160,
                             xaxis=dict(visible=True, showgrid=False),
                             yaxis=dict(visible=True, showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
                             showlegend=False, xaxis_title="Week", yaxis_title="Impressions")
        st.plotly_chart(fig_sp, use_container_width=True, config={"displayModeBar": False})

        st.markdown("#### Weekly Breakdown")
        wdf = (
            funnel_df[funnel_df["campaign_id"] == view]
            .sort_values("week_start_date")
            [["week_start_date","social_post_impression","landing_page_visits","lead_form_submission"]]
            .rename(columns={
                "week_start_date":"Week",
                "social_post_impression":"Impressions",
                "landing_page_visits":"Visits",
                "lead_form_submission":"Leads",
            })
        )
        st.dataframe(wdf, use_container_width=True, hide_index=True)

    with tab_cg:
        st.markdown(f"Build an AI targeting plan for **{c['crop'].title()}** growers.")
        growers_df = load_growers()
        unique_states = sorted(growers_df["state"].dropna().unique().tolist())

        f1, f2 = st.columns(2)
        ref_date   = f1.date_input("Reference Date", value=REFERENCE_DATE, key=f"date_{view}")
        state_sel  = f2.selectbox("State", ["All"] + unique_states, key=f"state_{view}")
        state_arg  = None if state_sel == "All" else state_sel

        b1, b2 = st.columns([2,1])
        build_clicked = b1.button("Build Targeting Plan", type="primary",
                                  use_container_width=True, key=f"build_{view}")
        gen_clicked   = (b2.button("Generate Content", use_container_width=True, key=f"gen_{view}")
                         if st.session_state.targeting_plan else False)

        if build_clicked:
            with st.spinner("Scoring growers…"):
                plan = run_targeting(ref_date, c["crop"], state_arg)
                st.session_state.targeting_plan   = plan
                st.session_state.content_variants = None
                data_dir = Path(__file__).parent.parent / "data"
                data_dir.mkdir(exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                (data_dir / f"campaign_{ts}.json").write_text(
                    json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8"
                )
            st.rerun()

        if gen_clicked:
            with st.spinner("Generating content…"):
                st.session_state.content_variants = run_content_generation(
                    st.session_state.targeting_plan)
            st.rerun()

        _render_content_variants()

    with tab_rx:
        _render_receptivity(crop_filter=c["crop"])


# ── AI CAMPAIGN ───────────────────────────────────────────────────────────────
elif any(c["_id"] == view for c in saved_camps):
    c    = next(x for x in saved_camps if x["_id"] == view)
    segs = c.get("segments", [])
    crops = sorted({s.get("crop","").title() for s in segs})
    qs   = c.get("quality_summary", {})
    gen_at = c.get("generated_at","")[:16].replace("T"," ")

    # Hero
    st.markdown(
        f"""
<div style="background:linear-gradient(135deg,#1a3d28 0%,#2f7d4c 55%,#1a3d28 100%);
border-radius:18px;padding:1.6rem 2rem 1.4rem;margin-bottom:1.5rem;
box-shadow:0 12px 36px rgba(47,125,76,0.2);">
  <div style="font-size:0.72rem;font-weight:600;letter-spacing:0.08em;
  color:rgba(212,237,218,0.7);text-transform:uppercase;margin-bottom:0.3rem;">
  AI Campaign</div>
  <h2 style="color:#fff;font-size:1.7rem;font-weight:700;margin:0 0 0.25rem;
  letter-spacing:-0.02em;">{c['_filename'].replace('.json','')}</h2>
  <div style="color:rgba(255,255,255,0.78);font-size:0.92rem;margin-bottom:0.8rem;">
    {', '.join(crops) or '—'} &nbsp;·&nbsp; Built {gen_at}
    &nbsp;·&nbsp; Ref date {c.get('reference_date','—')}
  </div>
  <div style="display:flex;gap:1.4rem;flex-wrap:wrap;">
    <span style="color:#fff;font-size:0.88rem;"><strong>{qs.get('total_growers','—')}</strong>
    <span style="opacity:.7;font-size:0.78rem;"> Scored</span></span>
    <span style="color:#fff;font-size:0.88rem;"><strong>{c.get('total_eligible','—')}</strong>
    <span style="opacity:.7;font-size:0.78rem;"> Eligible</span></span>
    <span style="color:#fff;font-size:0.88rem;"><strong>{len(segs)}</strong>
    <span style="opacity:.7;font-size:0.78rem;"> Segments</span></span>
    <span style="background:rgba(192,122,43,0.35);border-radius:999px;padding:0.18rem 0.7rem;
    font-size:0.78rem;color:#ffd8a0;font-weight:600;">
    {len(c.get('oos_blocked',[]))} OOS blocked</span>
  </div>
</div>""",
        unsafe_allow_html=True,
    )

    tab_ov, tab_cg, tab_rx = st.tabs(["Overview", "Content Generation", "Receptivity"])

    with tab_ov:
        if c.get("rationale"):
            st.markdown("#### Rationale")
            st.info(c["rationale"])

        if c.get("oos_blocked"):
            st.warning(
                f"**{len(c['oos_blocked'])} campaign(s) paused — out-of-stock risk**\n\n"
                + "\n".join(
                    f"- **{b['crop'].title()}** in {b['state']}: {b['product']} "
                    f"({b['grower_count']} growers) — {b['reason']}"
                    for b in c["oos_blocked"]
                )
            )

        if segs:
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
        if not st.session_state.targeting_plan:
            st.info("Run **Build Targeting Plan** again from a new campaign to generate content, "
                    "or the content may already have been generated in a separate session.")
        else:
            _render_content_variants()

    with tab_rx:
        crop_f = list(crops)[0].lower() if len(crops) == 1 else None
        _render_receptivity(crop_filter=crop_f)


# ── NEW CAMPAIGN ──────────────────────────────────────────────────────────────
elif view == "new":
    st.markdown(
        f"""
<div style="background:linear-gradient(135deg,#1a3d28 0%,#2f7d4c 55%,#1a3d28 100%);
border-radius:18px;padding:1.6rem 2rem 1.4rem;margin-bottom:1.5rem;
box-shadow:0 12px 36px rgba(47,125,76,0.2);">
  <div style="font-size:0.72rem;font-weight:600;letter-spacing:0.08em;
  color:rgba(212,237,218,0.7);text-transform:uppercase;margin-bottom:0.3rem;">New Campaign</div>
  <h2 style="color:#fff;font-size:1.7rem;font-weight:700;margin:0 0 0.25rem;">
  AI Targeting Builder</h2>
  <p style="color:rgba(255,255,255,0.75);font-size:0.9rem;margin:0;">
  Configure filters, score growers, segment them into micro-clusters, and generate
  multilingual campaign content.</p>
</div>""",
        unsafe_allow_html=True,
    )

    growers_df = load_growers()
    raw_crops  = (growers_df["grower_crop_calendar"].dropna()
                  .apply(lambda x: x.get("crop","") if isinstance(x, dict) else ""))
    unique_crops  = sorted(c for c in raw_crops.unique() if c)
    unique_states = sorted(growers_df["state"].dropna().unique().tolist())

    f1, f2, f3 = st.columns(3)
    ref_date     = f1.date_input("Reference Date", value=REFERENCE_DATE)
    crop_filter  = f2.selectbox("Crop",  ["All"] + unique_crops)
    state_filter = f3.selectbox("State", ["All"] + unique_states)
    crop_arg  = None if crop_filter  == "All" else crop_filter
    state_arg = None if state_filter == "All" else state_filter

    b1, b2 = st.columns([2,1])
    build_clicked = b1.button("Build Targeting Plan", type="primary", use_container_width=True)
    gen_clicked   = (b2.button("Generate Content", use_container_width=True)
                     if st.session_state.targeting_plan else False)

    if build_clicked:
        with st.spinner("Scoring growers and building segments…"):
            plan = run_targeting(ref_date, crop_arg, state_arg)
            st.session_state.targeting_plan   = plan
            st.session_state.content_variants = None
            data_dir = Path(__file__).parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            (data_dir / f"campaign_{ts}.json").write_text(
                json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        st.rerun()

    if gen_clicked:
        with st.spinner("Generating multilingual content…"):
            st.session_state.content_variants = run_content_generation(
                st.session_state.targeting_plan)
        st.rerun()

    tab_ov, tab_cg, tab_rx = st.tabs(["Overview", "Content Generation", "Receptivity"])

    with tab_ov:
        plan = st.session_state.targeting_plan
        if not plan:
            st.markdown(
                '<div style="border:1px dashed #c8c0b0;border-radius:14px;padding:2.5rem;'
                'text-align:center;background:#fafaf7;color:#999;">'
                '<div style="font-size:1.8rem;margin-bottom:0.5rem;">🌾</div>'
                'Set filters above and click <strong>Build Targeting Plan</strong></div>',
                unsafe_allow_html=True,
            )
        else:
            st.info(plan.get("rationale","-"))
            qs = plan.get("quality_summary",{})
            m1,m2,m3,m4 = st.columns(4)
            m1.metric("Growers Scored",     qs.get("total_growers","-"))
            m2.metric("Eligible",           plan.get("total_eligible","-"))
            m3.metric("OOS Blocked",        qs.get("oos_blocked_growers","-"))
            m4.metric("No Digital Channel", qs.get("non_smartphone","-"))

            if plan.get("oos_blocked"):
                st.warning(
                    f"**{len(plan['oos_blocked'])} paused — OOS risk**\n\n"
                    + "\n".join(
                        f"- **{b['crop'].title()}** in {b['state']}: {b['product']} "
                        f"({b['grower_count']} growers)"
                        for b in plan["oos_blocked"]
                    )
                )
            segs = plan.get("segments",[])
            if segs:
                st.markdown(f"#### Targeting Segments ({len(segs)})")
                st.dataframe(pd.DataFrame([{
                    "ID":s["segment_id"],"Crop":s["crop"].title(),"State":s["state"],
                    "Language":s["language"],"Channel":s["channel"],"Persona":s["persona"],
                    "Product":s["product"],"Stage":s["stage_context"],
                    "Growers":s["grower_count"],"Avg Score":s["avg_score"],
                } for s in segs]), use_container_width=True, hide_index=True)

    with tab_cg:
        _render_content_variants()

    with tab_rx:
        _render_receptivity(crop_filter=crop_arg)
