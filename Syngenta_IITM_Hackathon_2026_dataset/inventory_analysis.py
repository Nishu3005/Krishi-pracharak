"""
inventory_analysis.py
Standalone module (no Streamlit) that analyses retailer_inventory_weekly.csv
and returns a rich insights dict for use by the Krishi Pracharak app.
"""

import os
import numpy as np
import pandas as pd


_CSV_PATH = os.path.join(os.path.dirname(__file__), "retailer_inventory_weekly.csv")


def get_inventory_insights() -> dict:
    """Load retailer_inventory_weekly.csv and return a comprehensive insights dict."""

    df = pd.read_csv(_CSV_PATH, parse_dates=["week_end_date"])

    # ── 1. Basic counts ────────────────────────────────────────────────────────
    total_records: int = len(df)
    unique_skus: int = df["sku_name"].nunique()
    unique_retailers: int = df["retailer_id"].nunique()

    # ── 2. Week range ──────────────────────────────────────────────────────────
    all_weeks_sorted = sorted(df["week_end_date"].unique())
    week_start = pd.Timestamp(all_weeks_sorted[0])
    week_end = pd.Timestamp(all_weeks_sorted[-1])
    num_weeks = len(all_weeks_sorted)
    week_range = {
        "start": week_start.strftime("%Y-%m-%d"),
        "end": week_end.strftime("%Y-%m-%d"),
        "weeks": num_weeks,
    }

    # ── 3. SKU names ───────────────────────────────────────────────────────────
    sku_names: list = sorted(df["sku_name"].unique().tolist())

    # ── 4. Avg stock by SKU (sorted desc) ─────────────────────────────────────
    avg_by_sku_series = df.groupby("sku_name")["sku_qty"].mean().round(1)
    avg_stock_by_sku: dict = dict(
        avg_by_sku_series.sort_values(ascending=False)
    )

    # ── 5. Peak stock by SKU ───────────────────────────────────────────────────
    peak_stock_by_sku: dict = dict(df.groupby("sku_name")["sku_qty"].max())

    # ── 6. OOS metrics ────────────────────────────────────────────────────────
    oos_mask = df["sku_qty"] == 0
    total_oos_events: int = int(oos_mask.sum())

    oos_weeks_by_sku: dict = dict(
        df[oos_mask].groupby("sku_name").size()
    )
    # ensure every SKU present even if zero OOS
    for s in sku_names:
        if s not in oos_weeks_by_sku:
            oos_weeks_by_sku[s] = 0

    # OOS rate per SKU = oos_records / total_records for that SKU
    total_by_sku = df.groupby("sku_name").size()
    oos_count_series = df[oos_mask].groupby("sku_name").size().reindex(total_by_sku.index, fill_value=0)
    oos_rate_by_sku: dict = dict(
        ((oos_count_series / total_by_sku) * 100).round(1)
    )

    retailers_with_any_oos: int = int(df.loc[oos_mask, "retailer_id"].nunique())

    # top 15 retailers by OOS event count
    top_oos_series = (
        df[oos_mask]
        .groupby("retailer_id")
        .size()
        .sort_values(ascending=False)
        .head(15)
    )
    top_oos_retailers: dict = {str(k): int(v) for k, v in top_oos_series.items()}

    # ── 7. Weekly avg stock (across all SKUs+retailers) ────────────────────────
    weekly_avg_series = (
        df.groupby("week_end_date")["sku_qty"]
        .mean()
        .round(1)
        .sort_index()
    )
    weekly_avg_stock: dict = {
        k.strftime("%Y-%m-%d"): float(v)
        for k, v in weekly_avg_series.items()
    }

    # ── 8. SKU weekly avg — top 6 SKUs by total volume ────────────────────────
    top6_skus = (
        avg_by_sku_series.sort_values(ascending=False).head(6).index.tolist()
    )
    df_top6 = df[df["sku_name"].isin(top6_skus)]
    sku_weekly_pivot = (
        df_top6.groupby(["sku_name", "week_end_date"])["sku_qty"]
        .mean()
        .round(1)
        .reset_index()
    )
    sku_weekly_avg: dict = {}
    for sku in top6_skus:
        rows = sku_weekly_pivot[sku_weekly_pivot["sku_name"] == sku].sort_values("week_end_date")
        sku_weekly_avg[sku] = {
            row["week_end_date"].strftime("%Y-%m-%d"): round(float(row["sku_qty"]), 1)
            for _, row in rows.iterrows()
        }

    # ── 9. Stock trend slope by SKU (linear regression over weekly avg) ───────
    all_weeks_list = sorted(df["week_end_date"].unique())
    week_index = {w: i for i, w in enumerate(all_weeks_list)}

    sku_week_avg = (
        df.groupby(["sku_name", "week_end_date"])["sku_qty"]
        .mean()
        .reset_index()
    )

    stock_trend_slope_by_sku: dict = {}
    for sku in sku_names:
        rows = sku_week_avg[sku_week_avg["sku_name"] == sku].sort_values("week_end_date")
        if len(rows) < 2:
            stock_trend_slope_by_sku[sku] = 0.0
            continue
        x = np.array([week_index[w] for w in rows["week_end_date"]], dtype=float)
        y = rows["sku_qty"].values.astype(float)
        slope = float(np.polyfit(x, y, 1)[0])
        stock_trend_slope_by_sku[sku] = round(slope, 3)

    # ── 10. At-risk SKUs ──────────────────────────────────────────────────────
    overall_median_avg = float(np.median(list(avg_stock_by_sku.values())))
    at_risk_skus: list = sorted(
        [
            sku
            for sku in sku_names
            if avg_stock_by_sku.get(sku, 0) < overall_median_avg
            and stock_trend_slope_by_sku.get(sku, 0) < 0
        ],
        key=lambda s: stock_trend_slope_by_sku[s],  # ascending = most at-risk first
    )

    # ── 11. OOS heatmap — top 8 SKUs by total OOS events ─────────────────────
    top8_oos_skus = (
        oos_count_series.sort_values(ascending=False).head(8).index.tolist()
    )
    df_top8 = df[df["sku_name"].isin(top8_oos_skus)]

    # per SKU per week: count retailers OOS / total retailers that week
    oos_heatmap: dict = {}
    for sku in top8_oos_skus:
        sku_df = df_top8[df_top8["sku_name"] == sku]
        total_per_week = sku_df.groupby("week_end_date")["retailer_id"].count()
        oos_per_week = (
            sku_df[sku_df["sku_qty"] == 0]
            .groupby("week_end_date")["retailer_id"]
            .count()
            .reindex(total_per_week.index, fill_value=0)
        )
        rate_series = ((oos_per_week / total_per_week) * 100).round(1).sort_index()
        oos_heatmap[sku] = {
            k.strftime("%Y-%m-%d"): float(v) for k, v in rate_series.items()
        }

    # ── Return ─────────────────────────────────────────────────────────────────
    return {
        "total_records": total_records,
        "unique_skus": unique_skus,
        "unique_retailers": unique_retailers,
        "week_range": week_range,
        "sku_names": sku_names,
        "avg_stock_by_sku": avg_stock_by_sku,
        "peak_stock_by_sku": peak_stock_by_sku,
        "oos_weeks_by_sku": oos_weeks_by_sku,
        "oos_rate_by_sku": oos_rate_by_sku,
        "total_oos_events": total_oos_events,
        "retailers_with_any_oos": retailers_with_any_oos,
        "top_oos_retailers": top_oos_retailers,
        "weekly_avg_stock": weekly_avg_stock,
        "sku_weekly_avg": sku_weekly_avg,
        "stock_trend_slope_by_sku": stock_trend_slope_by_sku,
        "at_risk_skus": at_risk_skus,
        "oos_heatmap": oos_heatmap,
    }


if __name__ == "__main__":
    insights = get_inventory_insights()
    print(f"Total records      : {insights['total_records']:,}")
    print(f"Unique SKUs        : {insights['unique_skus']}")
    print(f"Unique retailers   : {insights['unique_retailers']}")
    print(f"Week range         : {insights['week_range']}")
    print(f"Total OOS events   : {insights['total_oos_events']:,}")
    print(f"Retailers with OOS : {insights['retailers_with_any_oos']:,}")
    print(f"At-risk SKUs       : {insights['at_risk_skus']}")
