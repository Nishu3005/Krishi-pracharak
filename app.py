import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.ui_theme import apply_theme
from utils.home_theme import inject_home_css, home_hero_html, home_metrics_html, home_section

st.set_page_config(
    page_title="Krishi Pracharak",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()
inject_home_css()

# ── Dataset path on sys.path for analysis modules ─────────────────────────────
sys.path.insert(0, str(Path(__file__).parent / "Syngenta_IITM_Hackathon_2026_dataset"))


@st.cache_data
def _load_grower_insights():
    from growers_analysis import get_grower_insights
    return get_grower_insights()


@st.cache_data
def _load_reps_insights():
    from reps_analysis import get_reps_insights
    return get_reps_insights()



st.markdown(
    home_hero_html(
        "From 6,000 growers and a product catalog to ranked field actions, "
        "multilingual campaign content, and rep briefings — fully AI-driven, in one operational flow."
    ),
    unsafe_allow_html=True,
)


_CHART_LAYOUT = dict(
    paper_bgcolor="#fffdf7",
    plot_bgcolor="#fffdf7",
    margin=dict(l=10, r=10, t=30, b=10),
    font=dict(color="#1a2520", family="Space Grotesk"),
    title_font=dict(color="#1a2520", size=13),
    xaxis=dict(
        color="#1a2520",
        tickfont=dict(color="#4a5e54"),
        title=dict(font=dict(color="#4a5e54")),
        gridcolor="#e8e4da",
        linecolor="#e8e4da",
    ),
    yaxis=dict(
        color="#1a2520",
        tickfont=dict(color="#4a5e54"),
        title=dict(font=dict(color="#4a5e54")),
        gridcolor="#e8e4da",
        linecolor="#e8e4da",
    ),
)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION A — Grower Network Intelligence
# ─────────────────────────────────────────────────────────────────────────────

home_section(
    "Grower Network Intelligence",
    "Geo-demographic profile of 6,000 growers across 10 states — crop patterns, language reach, technology adoption, and farm economics.",
)

gi = _load_grower_insights()

st.markdown(
    home_metrics_html([
        (f"{gi['total_growers']:,}", "Total Growers", False),
        (str(gi["total_states"]), "States", False),
        (str(gi["total_districts"]), "Districts", False),
        (f"{gi['farm_size_stats']['mean']} ac", "Avg Farm Size", False),
        (f"{gi['product_scan_rate_pct']}%", "Scan Rate", True),
    ]),
    unsafe_allow_html=True,
)

tab_geo, tab_crops, tab_tech, tab_demo = st.tabs(
    ["🌍 Geography", "🌾 Crops", "📱 Technology & Reach", "👥 Demographics"]
)

# ── Tab: Geography ─────────────────────────────────────────────────────────
with tab_geo:
    col_geo_l, col_geo_r = st.columns(2)

    with col_geo_l:
        top12_states = dict(list(gi["farmers_per_state"].items())[:12])
        states_df = pd.DataFrame(
            {"state": list(top12_states.keys()), "farmers": list(top12_states.values())}
        ).sort_values("farmers")

        fig_states = px.bar(
            states_df,
            x="farmers",
            y="state",
            orientation="h",
            title="Top 12 States by Farmer Count",
            color_discrete_sequence=["#2f7d4c"],
        )
        fig_states.update_layout(**_CHART_LAYOUT)
        fig_states.update_traces(marker_color="#2f7d4c")
        st.markdown('<div class="kp-home-chart"><div class="kp-home-chart-title">Farmers per State</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_states, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.caption("Longer bars = more growers in that state. Uttar Pradesh and Rajasthan dominate the network.")

    with col_geo_r:
        lang_dist = gi["language_district_coverage"]
        languages_r = list(lang_dist.keys())
        district_counts_r = list(lang_dist.values())

        fig_radar = go.Figure(
            go.Scatterpolar(
                r=district_counts_r + [district_counts_r[0]],
                theta=languages_r + [languages_r[0]],
                fill="toself",
                fillcolor="rgba(47,125,76,0.3)",
                line=dict(color="#2f7d4c", width=2),
                name="District Coverage",
            )
        )
        fig_radar.update_layout(
            title="Language Coverage by Districts",
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    tickfont=dict(color="#4a5e54", size=10),
                    gridcolor="#e8e4da",
                    linecolor="#e8e4da",
                ),
                angularaxis=dict(
                    tickfont=dict(color="#1a2520", size=12),
                    linecolor="#e8e4da",
                ),
                bgcolor="#fffdf7",
            ),
            showlegend=False,
            **_CHART_LAYOUT,
        )
        st.markdown('<div class="kp-home-chart"><div class="kp-home-chart-title">Language District Coverage</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_radar, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.caption("Each spoke = a language. Distance from centre = number of districts covered. Wider area = broader reach.")

# ── Tab: Crops ─────────────────────────────────────────────────────────────
with tab_crops:
    # Heatmap — crop × state
    matrix = gi["crop_state_matrix"]
    crops_list = sorted(matrix.keys())
    all_states = sorted({s for crop_data in matrix.values() for s in crop_data.keys()})
    z_data = [[matrix[crop].get(state, 0) for state in all_states] for crop in crops_list]

    fig_heat = go.Figure(
        go.Heatmap(
            z=z_data,
            x=all_states,
            y=crops_list,
            colorscale=[[0, "#f0f7f2"], [1, "#1a5c35"]],
            hoverongaps=False,
            colorbar=dict(title="Growers"),
        )
    )
    fig_heat.update_layout(
        title="Grower Crop Distribution by State",
        xaxis_title="State",
        yaxis_title="Crop",
        **_CHART_LAYOUT,
    )
    st.markdown('<div class="kp-home-chart"><div class="kp-home-chart-title">Crop × State Heatmap</div>', unsafe_allow_html=True)
    st.plotly_chart(fig_heat, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.caption("Darker green = more growers growing that crop in that state. Use this to identify crop-state combinations with the largest audience for a campaign.")

    crop_dist = gi["crop_distribution"]
    crop_colors = ["#2f7d4c", "#5aa876", "#88bb97", "#c07a2b", "#e8a85b"]
    fig_crop_pie = go.Figure(
        go.Pie(
            labels=list(crop_dist.keys()),
            values=list(crop_dist.values()),
            hole=0.45,
            marker=dict(colors=crop_colors),
        )
    )
    fig_crop_pie.update_layout(title="Overall Crop Distribution", **_CHART_LAYOUT)
    st.markdown('<div class="kp-home-chart"><div class="kp-home-chart-title">Crop Distribution</div>', unsafe_allow_html=True)
    st.plotly_chart(fig_crop_pie, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.caption("Share of growers by primary crop. A larger slice means more potential reach for that crop's campaign.")

# ── Tab: Technology & Reach ────────────────────────────────────────────────
with tab_tech:
    col_tech_l, col_tech_r = st.columns(2)

    with col_tech_l:
        dev = gi["device_types"]
        fig_dev = go.Figure(
            go.Pie(
                labels=list(dev.keys()),
                values=list(dev.values()),
                hole=0.45,
                marker=dict(colors=["#2f7d4c", "#88bb97", "#d0e8d5"]),
            )
        )
        fig_dev.update_layout(title="Device Type Distribution", **_CHART_LAYOUT)
        st.markdown('<div class="kp-home-chart"><div class="kp-home-chart-title">Device Types</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_dev, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.caption("Smartphone owners can receive WhatsApp and SMS campaigns. Non-smartphone growers need a rep field visit.")

    with col_tech_r:
        scan_by_state = gi["scan_by_state"]
        scan_df = (
            pd.DataFrame(
                {"state": list(scan_by_state.keys()), "scan_pct": list(scan_by_state.values())}
            )
            .sort_values("scan_pct")
        )
        overall_scan_mean = gi["product_scan_rate_pct"]

        fig_scan = px.bar(
            scan_df,
            x="scan_pct",
            y="state",
            orientation="h",
            title="Product Scan Rate by State (%)",
            color_discrete_sequence=["#c07a2b"],
        )
        fig_scan.add_vline(
            x=overall_scan_mean,
            line_dash="dash",
            line_color="#2f7d4c",
            annotation_text=f"Avg {overall_scan_mean}%",
            annotation_position="top right",
            annotation_font=dict(color="#2f7d4c", size=11),
        )
        fig_scan.update_layout(**_CHART_LAYOUT)
        fig_scan.update_traces(marker_color="#c07a2b")
        st.markdown('<div class="kp-home-chart"><div class="kp-home-chart-title">Scan Rate by State</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_scan, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.caption("States to the right of the dashed average line have higher product awareness — growers there are warmer leads.")

# ── Tab: Demographics ─────────────────────────────────────────────────────
with tab_demo:
    col_demo_l, col_demo_r = st.columns(2)

    with col_demo_l:
        age_by_state = gi["age_by_state"]
        age_df = (
            pd.DataFrame(
                {"state": list(age_by_state.keys()), "mean_age": [v["mean"] for v in age_by_state.values()]}
            )
            .sort_values("mean_age")
        )
        fig_age = px.bar(
            age_df,
            x="mean_age",
            y="state",
            orientation="h",
            title="Average Age by State",
            color_discrete_sequence=["#5aa876"],
        )
        fig_age.update_layout(**_CHART_LAYOUT)
        fig_age.update_traces(marker_color="#5aa876")
        st.markdown('<div class="kp-home-chart"><div class="kp-home-chart-title">Average Age by State</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_age, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.caption("Younger farmers tend to adopt digital channels faster. Higher average age may mean more rep-assist outreach is needed.")

    with col_demo_r:
        gender = gi["gender"]
        fig_gender = go.Figure(
            go.Pie(
                labels=["Male", "Female"],
                values=[gender["male"], gender["female"]],
                hole=0.45,
                marker=dict(colors=["#2f7d4c", "#c07a2b"]),
                title=dict(text="Gender Split"),
            )
        )
        fig_gender.update_layout(**_CHART_LAYOUT)
        st.markdown('<div class="kp-home-chart"><div class="kp-home-chart-title">Gender Split</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_gender, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.caption("Female farmers show slightly higher response rates in this dataset — a small receptivity bonus is applied during scoring.")

        buckets = gi["farm_size_buckets"]
        farm_colors = ["#1a5c35", "#2f7d4c", "#5aa876", "#88bb97", "#c5e0ca"]
        fig_farm = go.Figure(
            go.Pie(
                labels=list(buckets.keys()),
                values=list(buckets.values()),
                hole=0.45,
                marker=dict(colors=farm_colors),
                title=dict(text="Farm Size Distribution"),
            )
        )
        fig_farm.update_layout(**_CHART_LAYOUT)
        st.markdown('<div class="kp-home-chart"><div class="kp-home-chart-title">Farm Size Distribution</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_farm, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.caption("Small farms (1–2 ac) engage most with campaigns. Large holdings (>10 ac) tend to rely more on direct rep contact.")


st.markdown("<br>", unsafe_allow_html=True)
