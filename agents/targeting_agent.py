import json
import os
from datetime import date, datetime

import pandas as pd

from utils.features import build_grower_features
from utils.receptivity_score import score_dataframe
from utils.product_catalog import get_campaign_product
from utils.ai_client import call_text, TEXT_MODEL_HEAVY

DATA_DIR = "data"
OUTPUT_PATH = os.path.join(DATA_DIR, "targeting_plan.json")
SCORE_THRESHOLD = 0.30
MIN_SEGMENT_SIZE = 20

LANGUAGE_MAP = {
    "Uttar Pradesh": "Hindi",
    "Rajasthan":     "Hindi",
    "Madhya Pradesh":"Hindi",
    "Bihar":         "Hindi",
    "Haryana":       "Hindi",
    "Punjab":        "Punjabi",
    "Maharashtra":   "Marathi",
    "Gujarat":       "Gujarati",
    "Karnataka":     "Kannada",
    "West Bengal":   "Bengali",
}


def run_targeting(
    reference_date: date,
    crop_filter: str | None = None,
    state_filter: str | None = None,
) -> dict:
    os.makedirs(DATA_DIR, exist_ok=True)

    df = build_grower_features(reference_date)
    df = score_dataframe(df)

    if crop_filter:
        df = df[df["crop"].str.lower() == crop_filter.lower()]
    if state_filter:
        df = df[df["state"] == state_filter]

    total_scored = len(df)
    eligible = df[df["receptivity_score"] >= SCORE_THRESHOLD].copy()

    # channel routing
    eligible["channel"] = eligible["device_type"].apply(
        lambda d: "whatsapp" if str(d).lower() == "smartphone" else "rep_assist"
    )

    # persona assignment
    eligible["persona"] = eligible.apply(_assign_persona, axis=1)

    # product per grower
    eligible["campaign_product"] = eligible["crop"].apply(
        lambda c: get_campaign_product(c) or _pos_fallback_product(c)
    )

    # OOS gate
    eligible["inventory_ok"] = ~eligible["oos_risk_product"].fillna(False)

    segments_raw, oos_blocked = _build_segments(eligible)
    segments = _merge_small_segments(segments_raw)

    rationale = _get_rationale(segments, oos_blocked, reference_date, total_scored)

    plan = {
        "generated_at": datetime.utcnow().isoformat(),
        "reference_date": reference_date.isoformat(),
        "rationale": rationale,
        "total_growers_scored": total_scored,
        "total_eligible": len(eligible),
        "segments": segments,
        "oos_blocked": oos_blocked,
        "quality_summary": _quality_summary(df, eligible),
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)

    return plan


def _assign_persona(row: pd.Series) -> str:
    scan = bool(row.get("product_scan", False))
    offline = bool(row.get("offline_campaign_attended", False))
    days = row.get("days_to_next_stage")

    if scan and not offline:
        return "hot_lead"
    try:
        d = int(days)
        if 0 <= d <= 14:
            return "pre_stage_alert"
    except (TypeError, ValueError):
        pass
    if offline and not scan:
        return "offline_reinforcement"
    return "awareness"


def _build_segments(df: pd.DataFrame) -> tuple[list, list]:
    segments = []
    oos_blocked = []
    seg_id = 1

    for keys, group in df.groupby(["crop", "state", "channel", "persona"]):
        crop, state, channel, persona = keys
        language = LANGUAGE_MAP.get(state, "Hindi")
        product = group["campaign_product"].iloc[0] if len(group) else None

        eligible_group = group[group["inventory_ok"]]
        blocked_group  = group[~group["inventory_ok"]]

        if not eligible_group.empty:
            days_vals = eligible_group["days_to_next_stage"].dropna()
            if not days_vals.empty:
                days_int = int(days_vals.median())
                stage_label = eligible_group["timing_label"].iloc[0]
                stage_context = f"{stage_label} in {days_int} days" if days_int >= 0 else f"{stage_label} ({abs(days_int)} days ago)"
            else:
                stage_context = eligible_group["timing_label"].iloc[0] if len(eligible_group) else "unknown"

            segments.append({
                "segment_id": f"SEG_{seg_id:03d}",
                "crop": crop,
                "state": state,
                "language": language,
                "channel": channel,
                "persona": persona,
                "product": product,
                "stage_context": stage_context,
                "grower_count": len(eligible_group),
                "avg_score": round(eligible_group["receptivity_score"].mean(), 3),
                "inventory_ok": True,
                "grower_ids": eligible_group["grower_id"].tolist(),
            })
            seg_id += 1

        if not blocked_group.empty:
            oos_blocked.append({
                "crop": crop,
                "state": state,
                "product": product,
                "grower_count": len(blocked_group),
                "reason": "OOS risk — inventory_blocked=True in territory",
            })

    return segments, oos_blocked


def _merge_small_segments(segments: list) -> list:
    small = [s for s in segments if s["grower_count"] < MIN_SEGMENT_SIZE]
    large = [s for s in segments if s["grower_count"] >= MIN_SEGMENT_SIZE]

    for s in small:
        best = _find_merge_target(s, large)
        if best:
            best["grower_ids"].extend(s["grower_ids"])
            best["grower_count"] += s["grower_count"]
            best["avg_score"] = round(
                (best["avg_score"] * (best["grower_count"] - s["grower_count"]) +
                 s["avg_score"] * s["grower_count"]) / best["grower_count"], 3
            )
        else:
            large.append(s)

    return large


def _find_merge_target(small: dict, candidates: list) -> dict | None:
    # prefer same crop + same channel
    for c in candidates:
        if c["crop"] == small["crop"] and c["channel"] == small["channel"]:
            return c
    # fallback: same crop
    for c in candidates:
        if c["crop"] == small["crop"]:
            return c
    return None


def _pos_fallback_product(crop: str) -> str | None:
    from utils.data_loader import load_pos
    pos = load_pos()
    top = (
        pos.groupby("sku_name")["sku_qty"]
        .sum()
        .sort_values(ascending=False)
    )
    return top.index[0] if not top.empty else None


def _get_rationale(segments: list, oos_blocked: list, reference_date: date, total: int) -> str:
    seg_summary = "\n".join(
        f"- {s['crop'].title()} / {s['state']} / {s['channel']} / {s['persona']}: "
        f"{s['grower_count']} growers, avg score {s['avg_score']}, product: {s['product']}"
        for s in segments[:15]
    )
    blocked_summary = "\n".join(
        f"- {b['crop'].title()} in {b['state']}: {b['product']} blocked ({b['grower_count']} growers)"
        for b in oos_blocked[:5]
    )

    prompt = f"""You are a Syngenta campaign planning analyst.
Reference date: {reference_date}. Total growers scored: {total}.

Targeting segments selected:
{seg_summary}

OOS-blocked (campaigns not running due to stock risk):
{blocked_summary if blocked_summary else "None"}

Write a concise 3-4 sentence campaign rationale explaining:
1. Why these segments were prioritised (timing, engagement signals)
2. What the inventory gate prevented
3. What the expected outcome is for field teams and conversion rates
Be direct, factual, and written for a Syngenta marketing manager."""

    return call_text(
        model=TEXT_MODEL_HEAVY,
        system="You are a precise agricultural marketing analyst at Syngenta India.",
        user=prompt,
        temperature=0.5,
    )


def _quality_summary(full_df: pd.DataFrame, eligible: pd.DataFrame) -> dict:
    total = len(full_df)
    return {
        "total_growers": total,
        "missing_calendar": int((full_df["timing_quality_flag"] == "missing_calendar").sum()),
        "stage_based": int((full_df["timing_mode"] == "stage_based").sum()),
        "season_phase": int((full_df["timing_mode"] == "season_phase").sum()),
        "below_threshold": int(total - len(eligible)),
        "oos_blocked_growers": int(eligible["oos_risk_product"].sum()),
        "non_smartphone": int((full_df["device_type"] != "smartphone").sum()),
    }
