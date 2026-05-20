"""
reps_analysis.py
Standalone module — loads reps_territory.csv from the same directory and
returns field-force insights as a dict via get_reps_insights().
"""

import json
import os

import pandas as pd

_CSV_PATH = os.path.join(os.path.dirname(__file__), "reps_territory.csv")


def _parse_tehsil_list(val) -> list:
    """Parse tehsil_list JSON column into a Python list. Returns [] on failure."""
    if pd.isna(val):
        return []
    try:
        parsed = json.loads(val)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def get_reps_insights() -> dict:
    df = pd.read_csv(_CSV_PATH)

    # ── Parse tehsil_list ─────────────────────────────────────────────────────
    df["tehsil_list_parsed"] = df["tehsil_list"].apply(_parse_tehsil_list)
    df["tehsil_count"] = df["tehsil_list_parsed"].apply(len)

    # ── 1. Basic counts ────────────────────────────────────────────────────────
    total_reps = int(len(df))
    total_territories = int(df["territory_id"].nunique())
    total_states = int(df["state"].nunique())
    total_districts = int(df["district"].nunique())

    # Total unique tehsils across all reps
    all_tehsils: set = set()
    for t_list in df["tehsil_list_parsed"]:
        all_tehsils.update(t_list)
    total_tehsils = len(all_tehsils)

    # ── 2. Reps per state ─────────────────────────────────────────────────────
    reps_per_state = df["state"].value_counts().sort_values(ascending=False).to_dict()
    reps_per_state = {str(k): int(v) for k, v in reps_per_state.items()}

    # ── 3. Territories per state ──────────────────────────────────────────────
    territories_per_state = (
        df.groupby("state")["territory_id"]
        .nunique()
        .sort_values(ascending=False)
        .to_dict()
    )
    territories_per_state = {str(k): int(v) for k, v in territories_per_state.items()}

    # ── 4. Unique districts per state ─────────────────────────────────────────
    districts_per_state = (
        df.groupby("state")["district"]
        .nunique()
        .sort_values(ascending=False)
        .to_dict()
    )
    districts_per_state = {str(k): int(v) for k, v in districts_per_state.items()}

    # ── 5. Top 20 reps per district ────────────────────────────────────────────
    reps_per_district = (
        df["district"]
        .value_counts()
        .head(20)
        .to_dict()
    )
    reps_per_district = {str(k): int(v) for k, v in reps_per_district.items()}

    # ── 6. Tehsils per rep stats ──────────────────────────────────────────────
    tc = df["tehsil_count"]
    tehsils_per_rep_stats = {
        "mean": round(float(tc.mean()), 2),
        "median": round(float(tc.median()), 2),
        "min": int(tc.min()),
        "max": int(tc.max()),
        "total": int(tc.sum()),
    }

    # ── 7. Tehsils per state (total covered) ─────────────────────────────────
    # We explode tehsil lists to count unique tehsils per state
    exploded = df.explode("tehsil_list_parsed")
    tehsils_per_state = (
        exploded.dropna(subset=["tehsil_list_parsed"])
        .groupby("state")["tehsil_list_parsed"]
        .nunique()
        .sort_values(ascending=False)
        .to_dict()
    )
    tehsils_per_state = {str(k): int(v) for k, v in tehsils_per_state.items()}

    # ── 8. Avg tehsils per rep by state ──────────────────────────────────────
    avg_tehsils_per_rep_by_state = (
        df.groupby("state")["tehsil_count"]
        .mean()
        .round(2)
        .sort_values(ascending=False)
        .to_dict()
    )
    avg_tehsils_per_rep_by_state = {str(k): float(v) for k, v in avg_tehsils_per_rep_by_state.items()}

    # ── 9. Top 15 districts by total tehsils covered ──────────────────────────
    district_tehsil_counts = (
        exploded.dropna(subset=["tehsil_list_parsed"])
        .groupby("district")["tehsil_list_parsed"]
        .nunique()
        .sort_values(ascending=False)
        .head(15)
        .to_dict()
    )
    top_districts_by_tehsil_coverage = {str(k): int(v) for k, v in district_tehsil_counts.items()}

    # ── 10. Coverage density: reps / districts per state ─────────────────────
    coverage_density: dict = {}
    for state in reps_per_state:
        n_reps = reps_per_state[state]
        n_dist = districts_per_state.get(state, 1)
        coverage_density[state] = round(n_reps / n_dist, 3) if n_dist > 0 else 0.0

    return {
        "total_reps": total_reps,
        "total_territories": total_territories,
        "total_states": total_states,
        "total_districts": total_districts,
        "total_tehsils": total_tehsils,
        "reps_per_state": reps_per_state,
        "territories_per_state": territories_per_state,
        "districts_per_state": districts_per_state,
        "reps_per_district": reps_per_district,
        "tehsils_per_rep_stats": tehsils_per_rep_stats,
        "tehsils_per_state": tehsils_per_state,
        "avg_tehsils_per_rep_by_state": avg_tehsils_per_rep_by_state,
        "top_districts_by_tehsil_coverage": top_districts_by_tehsil_coverage,
        "coverage_density": coverage_density,
    }


if __name__ == "__main__":
    import pprint
    pprint.pprint(get_reps_insights())
