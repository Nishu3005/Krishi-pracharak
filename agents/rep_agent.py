import json
import os
from datetime import date, datetime

import pandas as pd
import numpy as np

from utils.data_loader import load_reps, load_inventory, load_visits, load_growers
from utils.ai_client import call_text, TEXT_MODEL_FAST

DATA_DIR = "data"
OUTPUT_PATH = os.path.join(DATA_DIR, "rep_briefings.json")
TARGETING_PLAN_PATH = os.path.join(DATA_DIR, "targeting_plan.json")
VISIT_GAP_DAYS = 21
OOS_WEEKS_WINDOW = 4


def run_rep_briefing(rep_id: str, reference_date: date) -> dict:
    os.makedirs(DATA_DIR, exist_ok=True)

    reps = load_reps()
    rep_row = reps[reps["rep_id"] == rep_id]
    if rep_row.empty:
        raise ValueError(f"Rep {rep_id} not found in reps_territory.csv")

    rep_row = rep_row.iloc[0]
    territory_id = rep_row["territory_id"]
    tehsil_list  = rep_row["tehsil_list"]

    oos_actions   = _compute_oos_actions(territory_id, reference_date)
    gap_actions   = _compute_visit_gap_actions(territory_id, tehsil_list, reference_date)
    assist_actions = _get_rep_assist_growers(territory_id)
    offline_count = _count_offline_growers(tehsil_list)

    all_actions = _rank_actions(assist_actions, oos_actions, gap_actions)
    briefing_text = _gen_briefing(rep_id, territory_id, all_actions, offline_count, reference_date)

    result = {
        rep_id: {
            "generated_at":       datetime.utcnow().isoformat(),
            "briefing_text":      briefing_text,
            "priority_actions":   all_actions,
            "offline_growers_count": offline_count,
            "territory_id":       territory_id,
        }
    }

    existing = {}
    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except Exception:
                existing = {}

    existing.update(result)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    return result


def _compute_oos_actions(territory_id: str, reference_date: date) -> list:
    inventory = load_inventory()
    retailers  = load_reps()  # need retailer territory join instead
    from utils.data_loader import load_retailers
    retailers = load_retailers()

    territory_retailers = retailers[retailers["territory_id"] == territory_id]["retailer_id"].tolist()
    if not territory_retailers:
        return []

    ref_ts = pd.Timestamp(reference_date)
    window_start = ref_ts - pd.Timedelta(weeks=OOS_WEEKS_WINDOW)

    inv = inventory[
        (inventory["retailer_id"].isin(territory_retailers)) &
        (inventory["week_end_date"] >= window_start) &
        (inventory["week_end_date"] <= ref_ts)
    ]

    actions = []
    for sku, group in inv.groupby("sku_name"):
        weekly = group.groupby("week_end_date")["sku_qty"].sum().sort_index()
        if len(weekly) < 2:
            continue
        slope = np.polyfit(range(len(weekly)), weekly.values, 1)[0]
        avg   = weekly.mean()
        oos_weeks = int((weekly == 0).sum())

        if slope < -5 or avg < 15 or oos_weeks >= 2:
            weeks_until = max(1, int(avg / max(abs(slope), 1))) if slope < 0 else 99
            actions.append({
                "type":           "restock_alert",
                "sku":            sku,
                "tehsil":         "territory-wide",
                "weeks_until_oos": min(weeks_until, 8),
                "avg_stock":      round(float(avg), 1),
                "trend_slope":    round(float(slope), 2),
                "_impact":        max(0, 10 - weeks_until) + oos_weeks * 3,
            })

    return actions


def _compute_visit_gap_actions(territory_id: str, tehsil_list: list, reference_date: date) -> list:
    visits = load_visits()
    ref_ts = pd.Timestamp(reference_date)
    cutoff = ref_ts - pd.Timedelta(days=VISIT_GAP_DAYS)

    recent_tehsils = set(
        visits[
            (visits["territory_id"] == territory_id) &
            (visits["visit_date"] >= cutoff)
        ]["visit_tehsil"].tolist()
    )

    actions = []
    for tehsil in tehsil_list:
        if tehsil not in recent_tehsils:
            last_visit = visits[
                (visits["territory_id"] == territory_id) &
                (visits["visit_tehsil"] == tehsil)
            ]["visit_date"].max()

            days_since = (ref_ts - last_visit).days if pd.notna(last_visit) else 999

            actions.append({
                "type":             "visit_gap",
                "tehsil":           tehsil,
                "days_since_visit": int(days_since),
                "_impact":          min(days_since // 7, 10),
            })

    return actions


def _get_rep_assist_growers(territory_id: str) -> list:
    if not os.path.exists(TARGETING_PLAN_PATH):
        return []

    with open(TARGETING_PLAN_PATH, encoding="utf-8") as f:
        plan = json.load(f)

    growers = load_growers()
    from utils.data_loader import load_retailers
    retailers = load_retailers()
    territory_tehsils = set(
        retailers[retailers["territory_id"] == territory_id]["tehsil"].tolist()
    )

    actions = []
    for seg in plan.get("segments", []):
        if seg.get("channel") != "rep_assist":
            continue
        grower_ids = seg.get("grower_ids", [])
        matching = growers[
            growers["grower_id"].isin(grower_ids) &
            growers["tehsil"].isin(territory_tehsils)
        ]
        if matching.empty:
            continue
        actions.append({
            "type":        "rep_assist_campaign",
            "segment_id":  seg["segment_id"],
            "crop":        seg.get("crop"),
            "persona":     seg.get("persona"),
            "product":     seg.get("product"),
            "grower_count": len(matching),
            "tehsils":     matching["tehsil"].unique().tolist(),
            "_impact":     20,  # highest priority — from campaign plan
        })

    return actions


def _count_offline_growers(tehsil_list: list) -> int:
    growers = load_growers()
    return int(
        growers[
            growers["tehsil"].isin(tehsil_list) &
            (growers["device_type"] != "smartphone")
        ].shape[0]
    )


def _rank_actions(assist: list, oos: list, gaps: list) -> list:
    all_actions = assist + oos + gaps
    all_actions.sort(key=lambda x: -x.get("_impact", 0))
    for i, a in enumerate(all_actions, 1):
        a["rank"] = i
        a.pop("_impact", None)
    return all_actions[:10]


def _gen_briefing(
    rep_id: str,
    territory_id: str,
    actions: list,
    offline_count: int,
    reference_date: date,
) -> str:
    action_lines = "\n".join(
        f"{a['rank']}. [{a['type']}] "
        + (f"Visit {a.get('tehsil')} — {a.get('days_since_visit')} days since last visit" if a["type"] == "visit_gap"
           else f"Restock {a.get('sku')} — ~{a.get('weeks_until_oos')} weeks until OOS" if a["type"] == "restock_alert"
           else f"Campaign assist: {a.get('grower_count')} {a.get('crop')} growers need in-person visit for {a.get('product')}")
        for a in actions
    )

    system = "You are a Syngenta field operations analyst writing concise weekly rep briefings."
    user = f"""Rep: {rep_id} | Territory: {territory_id} | Date: {reference_date}
Non-smartphone growers needing personal visits: {offline_count}

Priority actions this week:
{action_lines}

Write a 3-4 sentence briefing paragraph for this rep. Be direct and practical.
Tell them what to do first, why it matters (stock risk or engagement opportunity),
and remind them about the {offline_count} offline growers who can only be reached in person."""

    return call_text(TEXT_MODEL_FAST, system, user, temperature=0.6)
