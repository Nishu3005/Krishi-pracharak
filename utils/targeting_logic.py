from __future__ import annotations

from datetime import date

import pandas as pd

from utils.product_catalog import PRODUCT_CATALOG, get_campaign_product


def _norm_crop(crop: str | None) -> str:
    return str(crop or "").strip().lower()


def get_pos_ranked_skus(pos_df: pd.DataFrame) -> list[str]:
    if pos_df is None or pos_df.empty:
        return []
    ranked = (
        pos_df.groupby("sku_name")["sku_qty"]
        .sum()
        .sort_values(ascending=False)
    )
    return [str(s) for s in ranked.index.tolist()]


def select_campaign_product(
    crop: str | None,
    pos_ranked_skus: list[str],
) -> tuple[str | None, str]:
    crop_key = _norm_crop(crop)
    if not crop_key:
        return (pos_ranked_skus[0], "pos_global_fallback") if pos_ranked_skus else (None, "missing_crop")

    mapped = get_campaign_product(crop_key)
    if mapped:
        return mapped, "campaign_map"

    crop_fit_skus = []
    for sku, ctx in PRODUCT_CATALOG.items():
        fit = [str(x).strip().lower() for x in ctx.get("crop_fit", [])]
        if crop_key in fit:
            crop_fit_skus.append(sku)

    if crop_fit_skus:
        for sku in pos_ranked_skus:
            if sku in crop_fit_skus:
                return sku, "pos_crop_fit"
        return crop_fit_skus[0], "catalog_crop_fit"

    return (pos_ranked_skus[0], "pos_global_fallback") if pos_ranked_skus else (None, "no_product_found")


def build_inventory_block_lookup(
    inventory_df: pd.DataFrame,
    retailers_df: pd.DataFrame,
    reference_date: date,
    weeks_window: int = 4,
) -> dict[tuple[str, str], bool]:
    if inventory_df.empty or retailers_df.empty:
        return {}

    ref_ts = pd.Timestamp(reference_date)
    window_start = ref_ts - pd.Timedelta(weeks=weeks_window)
    recent_inv = inventory_df[
        (inventory_df["week_end_date"] >= window_start)
        & (inventory_df["week_end_date"] <= ref_ts)
    ].copy()
    if recent_inv.empty:
        return {}

    retailer_territory = retailers_df[["retailer_id", "territory_id"]].drop_duplicates()
    recent_inv = recent_inv.merge(retailer_territory, on="retailer_id", how="left")
    recent_inv = recent_inv.dropna(subset=["territory_id", "sku_name"])

    grouped = (
        recent_inv.groupby(["territory_id", "sku_name"])
        .agg(
            avg_qty=("sku_qty", "mean"),
            oos_weeks=("sku_qty", lambda x: int((x == 0).sum())),
        )
        .reset_index()
    )
    grouped["inventory_blocked"] = (
        (grouped["avg_qty"] < 10)
        | (grouped["oos_weeks"] >= 2)
    )

    return {
        (str(r["territory_id"]), str(r["sku_name"])): bool(r["inventory_blocked"])
        for _, r in grouped.iterrows()
    }

