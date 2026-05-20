"""
growers_analysis.py
Standalone module — loads growers.csv from the same directory and returns
rich insights as a dict via get_grower_insights().
"""

import json
import os

import numpy as np
import pandas as pd

_CSV_PATH = os.path.join(os.path.dirname(__file__), "growers.csv")


def _parse_crop(calendar_str) -> str:
    """Extract crop name from grower_crop_calendar JSON string. Returns '' on failure."""
    if pd.isna(calendar_str):
        return ""
    try:
        obj = json.loads(calendar_str)
        return str(obj.get("crop", "")).strip().lower()
    except Exception:
        return ""


def get_grower_insights() -> dict:
    df = pd.read_csv(_CSV_PATH)

    # ── Parse crop from JSON calendar ─────────────────────────────────────────
    df["crop"] = df["grower_crop_calendar"].apply(_parse_crop)

    # ── 1. Basic counts ────────────────────────────────────────────────────────
    total_growers = int(len(df))
    total_states = int(df["state"].nunique())
    total_districts = int(df["district"].nunique())
    total_tehsils = int(df["tehsil"].nunique())

    # ── 2. Farmers per state (sorted descending) ───────────────────────────────
    farmers_per_state = (
        df["state"].value_counts().sort_values(ascending=False).to_dict()
    )
    farmers_per_state = {str(k): int(v) for k, v in farmers_per_state.items()}

    # ── 3. Unique districts per state ─────────────────────────────────────────
    districts_per_state = (
        df.groupby("state")["district"]
        .nunique()
        .sort_values(ascending=False)
        .to_dict()
    )
    districts_per_state = {str(k): int(v) for k, v in districts_per_state.items()}

    # ── 4. Top 25 farmers per district ────────────────────────────────────────
    farmers_per_district = (
        df["district"]
        .value_counts()
        .head(25)
        .to_dict()
    )
    farmers_per_district = {str(k): int(v) for k, v in farmers_per_district.items()}

    # ── 5. Dominant crop by state ──────────────────────────────────────────────
    crop_df = df[df["crop"] != ""]
    dominant_crop_by_state: dict = {}
    if not crop_df.empty:
        dominant_crop_by_state = (
            crop_df.groupby(["state", "crop"])
            .size()
            .reset_index(name="cnt")
            .sort_values("cnt", ascending=False)
            .groupby("state")
            .first()["crop"]
            .to_dict()
        )
        dominant_crop_by_state = {str(k): str(v) for k, v in dominant_crop_by_state.items()}

    # ── 6. Crop × state matrix for heatmap ────────────────────────────────────
    crop_state_matrix: dict = {}
    if not crop_df.empty:
        matrix = (
            crop_df.groupby(["crop", "state"])
            .size()
            .unstack(fill_value=0)
        )
        crop_state_matrix = {
            str(crop): {str(state): int(cnt) for state, cnt in row.items()}
            for crop, row in matrix.to_dict(orient="index").items()
        }

    # ── 7. Crop distribution overall ──────────────────────────────────────────
    crop_distribution: dict = {}
    if not crop_df.empty:
        crop_distribution = (
            crop_df["crop"].value_counts().to_dict()
        )
        crop_distribution = {str(k): int(v) for k, v in crop_distribution.items()}

    # ── 8. Device types ───────────────────────────────────────────────────────
    device_types = df["device_type"].value_counts().to_dict()
    device_types = {str(k): int(v) for k, v in device_types.items()}

    # ── 9. Age stats overall ──────────────────────────────────────────────────
    ages = df["grower_age"].dropna()
    age_stats_overall = {
        "mean": round(float(ages.mean()), 1),
        "median": round(float(ages.median()), 1),
        "min": int(ages.min()),
        "max": int(ages.max()),
        "std": round(float(ages.std()), 1),
    }

    # ── 10. Age by state ──────────────────────────────────────────────────────
    age_by_state = (
        df.groupby("state")["grower_age"]
        .agg(mean="mean", median="median")
        .round(1)
        .to_dict(orient="index")
    )
    age_by_state = {
        str(state): {"mean": float(v["mean"]), "median": float(v["median"])}
        for state, v in age_by_state.items()
    }

    # ── 11. Languages ─────────────────────────────────────────────────────────
    languages = df["language"].value_counts().to_dict()
    languages = {str(k): int(v) for k, v in languages.items()}

    # ── 12. Language → distinct districts ─────────────────────────────────────
    language_district_coverage = (
        df.groupby("language")["district"]
        .nunique()
        .sort_values(ascending=False)
        .to_dict()
    )
    language_district_coverage = {str(k): int(v) for k, v in language_district_coverage.items()}

    # ── 13. Language → distinct states ───────────────────────────────────────
    language_state_coverage = (
        df.groupby("language")["state"]
        .nunique()
        .sort_values(ascending=False)
        .to_dict()
    )
    language_state_coverage = {str(k): int(v) for k, v in language_state_coverage.items()}

    # ── 14. Gender counts ────────────────────────────────────────────────────
    gender_counts = df["gender"].str.lower().value_counts()
    gender = {
        "male": int(gender_counts.get("male", 0)),
        "female": int(gender_counts.get("female", 0)),
    }

    # ── 15. Gender by state (%) ──────────────────────────────────────────────
    gender_by_state: dict = {}
    for state, grp in df.groupby("state"):
        total = len(grp)
        if total == 0:
            continue
        male_pct = round(100.0 * (grp["gender"].str.lower() == "male").sum() / total, 1)
        female_pct = round(100.0 * (grp["gender"].str.lower() == "female").sum() / total, 1)
        gender_by_state[str(state)] = {"male": male_pct, "female": female_pct}

    # ── 16. Farm size stats ──────────────────────────────────────────────────
    farm = df["grower_farm_size"].dropna()
    farm_size_stats = {
        "mean": round(float(farm.mean()), 2),
        "median": round(float(farm.median()), 2),
        "min": round(float(farm.min()), 2),
        "max": round(float(farm.max()), 2),
    }

    # ── 17. Farm size buckets ────────────────────────────────────────────────
    bins = [0, 1, 2, 5, 10, float("inf")]
    labels = ["<1 ac", "1–2 ac", "2–5 ac", "5–10 ac", "10+ ac"]
    bucketed = pd.cut(farm, bins=bins, labels=labels, right=True)
    farm_size_buckets = {str(label): int(count) for label, count in bucketed.value_counts().reindex(labels, fill_value=0).items()}

    # ── 18. Product scan rate ────────────────────────────────────────────────
    product_scan_rate_pct = round(
        100.0 * df["product_scan"].fillna(False).astype(bool).sum() / total_growers, 2
    )

    # ── 19. Offline campaign attendance rate ─────────────────────────────────
    offline_campaign_rate_pct = round(
        100.0 * df["offline_campaign_attended"].fillna(False).astype(bool).sum() / total_growers, 2
    )

    # ── 20. Scan rate by state ───────────────────────────────────────────────
    scan_by_state: dict = {}
    for state, grp in df.groupby("state"):
        total_s = len(grp)
        if total_s == 0:
            continue
        pct = round(
            100.0 * grp["product_scan"].fillna(False).astype(bool).sum() / total_s, 2
        )
        scan_by_state[str(state)] = pct

    return {
        "total_growers": total_growers,
        "total_states": total_states,
        "total_districts": total_districts,
        "total_tehsils": total_tehsils,
        "farmers_per_state": farmers_per_state,
        "districts_per_state": districts_per_state,
        "farmers_per_district": farmers_per_district,
        "dominant_crop_by_state": dominant_crop_by_state,
        "crop_state_matrix": crop_state_matrix,
        "crop_distribution": crop_distribution,
        "device_types": device_types,
        "age_stats_overall": age_stats_overall,
        "age_by_state": age_by_state,
        "languages": languages,
        "language_district_coverage": language_district_coverage,
        "language_state_coverage": language_state_coverage,
        "gender": gender,
        "gender_by_state": gender_by_state,
        "farm_size_stats": farm_size_stats,
        "farm_size_buckets": farm_size_buckets,
        "product_scan_rate_pct": product_scan_rate_pct,
        "offline_campaign_rate_pct": offline_campaign_rate_pct,
        "scan_by_state": scan_by_state,
    }


if __name__ == "__main__":
    import pprint
    insights = get_grower_insights()
    pprint.pprint({k: v for k, v in insights.items() if k != "crop_state_matrix"})
