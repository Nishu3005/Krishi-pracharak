import sys
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from agents.rep_agent import run_rep_briefing
from utils.data_loader import load_growers, load_reps
from utils.ui_theme import apply_theme, render_hero

sys.path.insert(0, str(Path(__file__).parent.parent / "Syngenta_IITM_Hackathon_2026_dataset"))


@st.cache_data
def _load_inv_insights():
    from inventory_analysis import get_inventory_insights

    return get_inventory_insights()


# ── Plotly base layout ────────────────────────────────────────────────────────
_INV_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=10, r=10, t=30, b=10),
    font=dict(color="#1d2a22", family="Space Grotesk"),
)

st.set_page_config(page_title="Rep Briefing · Krishi Pracharak", layout="wide")
apply_theme()
render_hero(
    "Field Rep Briefing",
    "Turn territory signals into ranked weekly actions with stock-risk and visit coverage evidence.",
    kicker="Execution Layer",
)

# ═══════════════════════════════════════════════════════════════════════════════
# INVENTORY INTELLIGENCE SECTION
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("### 📦 Inventory Intelligence")
st.caption("Stock health, OOS risk, and depletion trends across 4,000 retailers.")
st.divider()

inv = _load_inv_insights()

# ── Row 1: metric cards ───────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total SKUs", inv["unique_skus"])
m2.metric("Total Retailers", f"{inv['unique_retailers']:,}")
m3.metric("Total OOS Events", f"{inv['total_oos_events']:,}")
m4.metric("Retailers with OOS", f"{inv['retailers_with_any_oos']:,}")

# ── Row 2: tabs ───────────────────────────────────────────────────────────────
tab_oos, tab_trends, tab_heat = st.tabs(["📉 OOS Risk", "📈 Stock Trends", "🔥 Risk Heatmap"])

# ── Tab: OOS Risk ─────────────────────────────────────────────────────────────
with tab_oos:
    col_left, col_right = st.columns(2, gap="medium")

    with col_left:
        st.markdown("**OOS Rate (%) by SKU**")
        oos_rate = inv["oos_rate_by_sku"]
        oos_df = (
            pd.DataFrame({"sku": list(oos_rate.keys()), "oos_rate": list(oos_rate.values())})
            .sort_values("oos_rate", ascending=True)  # ascending for horizontal bar (top = highest)
        )
        mean_oos = float(pd.Series(list(oos_rate.values())).mean())

        fig_oos = go.Figure()
        fig_oos.add_trace(
            go.Bar(
                x=oos_df["oos_rate"],
                y=oos_df["sku"],
                orientation="h",
                marker_color="#c07a2b",
                name="OOS Rate %",
            )
        )
        fig_oos.add_vline(
            x=mean_oos,
            line_dash="dash",
            line_color="#1a5c35",
            annotation_text=f"Mean {mean_oos:.1f}%",
            annotation_position="top right",
            annotation_font_color="#1a5c35",
        )
        fig_oos.update_layout(
            **_INV_LAYOUT,
            xaxis_title="OOS Rate (%)",
            yaxis_title=None,
            showlegend=False,
        )
        st.plotly_chart(fig_oos, use_container_width=True, config={"displayModeBar": False})

    with col_right:
        st.markdown("**Avg Stock Level by SKU**")
        avg_stock = inv["avg_stock_by_sku"]
        at_risk_set = set(inv["at_risk_skus"])

        avg_df = (
            pd.DataFrame({"sku": list(avg_stock.keys()), "avg_qty": list(avg_stock.values())})
            .sort_values("avg_qty", ascending=True)
        )
        bar_colors = [
            "#c07a2b" if sku in at_risk_set else "#2f7d4c"
            for sku in avg_df["sku"]
        ]

        fig_avg = go.Figure()
        fig_avg.add_trace(
            go.Bar(
                x=avg_df["avg_qty"],
                y=avg_df["sku"],
                orientation="h",
                marker_color=bar_colors,
                name="Avg Stock",
            )
        )
        fig_avg.update_layout(
            **_INV_LAYOUT,
            xaxis_title="Avg Qty (units)",
            yaxis_title=None,
            showlegend=False,
        )
        st.plotly_chart(fig_avg, use_container_width=True, config={"displayModeBar": False})
        st.caption("Orange bars = at-risk SKUs (below-median stock AND declining trend)")

# ── Tab: Stock Trends ─────────────────────────────────────────────────────────
with tab_trends:
    _PALETTE = ["#2f7d4c", "#5aa876", "#88bb97", "#c07a2b", "#e8a85b", "#1a5c35"]
    sku_weekly = inv["sku_weekly_avg"]

    fig_trend = go.Figure()
    for idx, (sku, week_data) in enumerate(sku_weekly.items()):
        weeks_sorted = sorted(week_data.keys())
        fig_trend.add_trace(
            go.Scatter(
                x=weeks_sorted,
                y=[week_data[w] for w in weeks_sorted],
                mode="lines+markers",
                name=sku,
                line=dict(color=_PALETTE[idx % len(_PALETTE)], width=2),
                marker=dict(size=5),
            )
        )
    fig_trend.update_layout(
        **_INV_LAYOUT,
        title="Weekly Average Stock by SKU",
        xaxis_title="Week End Date",
        yaxis_title="Avg Qty (units)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=10, r=10, t=60, b=10),
    )
    st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False})

    at_risk = inv["at_risk_skus"]
    if at_risk:
        badges = " ".join(
            f'<span style="background:#fff3e0;border:1px solid #c07a2b;border-radius:6px;'
            f'padding:2px 10px;color:#c07a2b;font-size:0.82rem;margin-right:4px;">⚠️ {s}</span>'
            for s in at_risk
        )
        st.markdown(
            f'<div style="margin-top:0.5rem;"><strong style="color:#1d2a22;">At-Risk SKUs: </strong>{badges}</div>',
            unsafe_allow_html=True,
        )

# ── Tab: Risk Heatmap ─────────────────────────────────────────────────────────
with tab_heat:
    heatmap_data = inv["oos_heatmap"]
    skus_hm = list(heatmap_data.keys())

    # Collect all unique weeks across all SKUs, sorted
    all_hm_weeks = sorted(
        {w for sku_weeks in heatmap_data.values() for w in sku_weeks.keys()}
    )

    z_matrix = [
        [heatmap_data[sku].get(wk, 0.0) for wk in all_hm_weeks]
        for sku in skus_hm
    ]

    fig_hm = go.Figure(
        go.Heatmap(
            z=z_matrix,
            x=all_hm_weeks,
            y=skus_hm,
            colorscale=[[0, "#f0f7f2"], [0.5, "#e8a85b"], [1, "#c0392b"]],
            colorbar=dict(title="OOS %", ticksuffix="%"),
            hoverongaps=False,
            hovertemplate="SKU: %{y}<br>Week: %{x}<br>OOS Rate: %{z:.1f}%<extra></extra>",
        )
    )
    fig_hm.update_layout(
        **_INV_LAYOUT,
        title="OOS Rate (%) by SKU × Week",
        xaxis_title="Week End Date",
        yaxis_title=None,
        margin=dict(l=10, r=10, t=50, b=10),
    )
    st.plotly_chart(fig_hm, use_container_width=True, config={"displayModeBar": False})

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# EXISTING PAGE CONTENT (unchanged)
# ═══════════════════════════════════════════════════════════════════════════════
reps = load_reps()
rep_ids = sorted(reps["rep_id"].tolist())

if "briefing" not in st.session_state:
    st.session_state.briefing = None
if "last_rep" not in st.session_state:
    st.session_state.last_rep = None

# ── Page layout: left panel + main content ────────────────────────────────────
left, main = st.columns([1, 3], gap="large")

with left:
    st.markdown("#### Parameters")
    rep_id = st.selectbox("Select Rep", rep_ids)
    reference_date = st.date_input("Reference Date", value=date(2026, 1, 15))
    st.markdown("")
    gen_clicked = st.button("Generate Briefing", type="primary", use_container_width=True)

if gen_clicked:
    with st.spinner(f"Analyzing territory and generating briefing for {rep_id}..."):
        result = run_rep_briefing(rep_id, reference_date)
        st.session_state.briefing = result.get(rep_id, {})
        st.session_state.last_rep = rep_id
    st.rerun()

with main:
    if not st.session_state.briefing or st.session_state.last_rep != rep_id:
        st.markdown(
            """
<div style="border:1px dashed #c8c0b0;border-radius:16px;padding:3rem 2rem;text-align:center;background:#fafaf7;color:#888;">
  <div style="font-size:2.5rem;margin-bottom:0.8rem;">🗺️</div>
  <div style="font-size:1rem;font-weight:600;color:#555;">Select a rep and click <strong>Generate Briefing</strong></div>
  <div style="font-size:0.85rem;margin-top:0.4rem;">The AI will compute stock risk, visit gaps, and offline growers for this territory.</div>
</div>
""",
            unsafe_allow_html=True,
        )
    else:
        briefing = st.session_state.briefing

        rep_row = reps[reps["rep_id"] == rep_id].iloc[0]
        st.subheader(f"{rep_id} - {rep_row['territory_name']} ({rep_row['state']}, {rep_row['district']})")

        actions = briefing.get("priority_actions", [])
        restock = [a for a in actions if a["type"] == "restock_alert"]
        gap = [a for a in actions if a["type"] == "visit_gap"]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Actions", len(actions))
        c2.metric("Restock Alerts", len(restock))
        c3.metric("Visit Gaps", len(gap))
        c4.metric(
            "Offline Growers",
            briefing.get("offline_growers_count", 0),
            help="Non-smartphone growers who need in-person or assisted outreach",
        )

        st.subheader("This Week Briefing")
        st.info(briefing.get("briefing_text", "-"))

        st.divider()
        st.subheader("Priority Actions")

        for action in actions:
            action_type = action["type"]
            rank = action["rank"]

            if action_type == "rep_assist_campaign":
                title = f"#{rank} Assisted Campaign - {action.get('crop', '').title()} ({action.get('persona', '')})"
                body = (
                    f"**Product:** {action.get('product')}  \n"
                    f"**Growers to visit:** {action.get('grower_count')}  \n"
                    f"**Tehsils:** {', '.join(action.get('tehsils', []))}"
                )
            elif action_type == "restock_alert":
                title = f"#{rank} Restock Alert - {action.get('sku')}"
                body = (
                    f"**Estimated weeks until OOS:** {action.get('weeks_until_oos')}  \n"
                    f"**Average stock:** {action.get('avg_stock')} units  \n"
                    f"**Trend:** {action.get('trend_slope')} units/week"
                )
            else:
                title = f"#{rank} Visit Gap - {action.get('tehsil')}"
                body = f"**Days since last visit:** {action.get('days_since_visit')}"

            with st.expander(title, expanded=rank <= 3):
                st.markdown(body)

        if briefing.get("offline_growers_count", 0) > 0:
            st.divider()
            st.subheader("Offline Growers (Non-Smartphone)")
            growers = load_growers()
            tehsil_list = rep_row["tehsil_list"]
            offline = growers[
                growers["tehsil"].isin(tehsil_list) & (growers["device_type"] != "smartphone")
            ][["grower_id", "tehsil", "device_type", "grower_crop_calendar", "grower_farm_size"]].copy()
            offline["crop"] = offline["grower_crop_calendar"].apply(
                lambda x: x.get("crop", "-") if isinstance(x, dict) else "-"
            )
            st.dataframe(
                offline[["grower_id", "tehsil", "crop", "device_type", "grower_farm_size"]],
                use_container_width=True,
                hide_index=True,
            )
