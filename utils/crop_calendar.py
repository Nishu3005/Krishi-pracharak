from datetime import date, datetime


def get_timing(crop_calendar: dict | None, reference_date: date) -> dict:
    if crop_calendar is None:
        return _unknown()

    crop = crop_calendar.get("crop", "")
    stages = crop_calendar.get("stages", [])
    sowing = crop_calendar.get("sowing", {})
    harvest = crop_calendar.get("harvest", {})

    if stages:
        return _stage_based(stages, reference_date)

    if sowing and harvest:
        return _season_phase(sowing, harvest, reference_date, crop)

    return _unknown()


def _stage_based(stages: list, reference_date: date) -> dict:
    upcoming = []
    for s in stages:
        try:
            stage_date = _parse_date(s.get("approx", ""))
            if stage_date is None:
                continue
            days_until = (stage_date - reference_date).days
            upcoming.append((days_until, s.get("stage", "unknown"), stage_date))
        except Exception:
            continue

    # find next upcoming stage (days_until >= 0), or most recent past stage
    future = [(d, label, dt) for d, label, dt in upcoming if d >= 0]
    if future:
        future.sort(key=lambda x: x[0])
        days_until, label, _ = future[0]
    elif upcoming:
        upcoming.sort(key=lambda x: x[0], reverse=True)
        days_until, label, _ = upcoming[0]
    else:
        return _unknown()

    urgency = _urgency_from_days(days_until)
    return {
        "mode": "stage_based",
        "label": label,
        "days_until": days_until,
        "urgency": urgency,
        "quality_flag": "ok",
    }


def _season_phase(sowing: dict, harvest: dict, reference_date: date, crop: str) -> dict:
    sowing_end = _parse_date(sowing.get("end", ""))
    harvest_start = _parse_date(harvest.get("start", ""))

    if sowing_end is None or harvest_start is None:
        return _unknown()

    total_days = max((harvest_start - sowing_end).days, 1)
    elapsed = (reference_date - sowing_end).days

    if elapsed < 0:
        phase = "pre_sowing"
        urgency = 0.20
    elif elapsed < total_days * 0.33:
        phase = "early_season"
        urgency = 0.30
    elif elapsed < total_days * 0.66:
        phase = "mid_season"
        urgency = 0.55
    else:
        phase = "late_season"
        urgency = 0.70

    days_to_harvest = (harvest_start - reference_date).days

    return {
        "mode": "season_phase",
        "label": phase,
        "days_until": days_to_harvest,
        "urgency": urgency,
        "quality_flag": "missing_stages",
    }


def _urgency_from_days(days_until: int) -> float:
    if days_until < 0:
        # past stage — urgency decays
        return max(0.10, 0.25 + days_until * 0.01)
    if days_until <= 7:
        return 0.90
    if days_until <= 14:
        return 0.80
    if days_until <= 21:
        return 0.65
    if days_until <= 35:
        return 0.45
    if days_until <= 60:
        return 0.30
    return 0.20


def _unknown() -> dict:
    return {
        "mode": "unknown",
        "label": "unknown",
        "days_until": None,
        "urgency": 0.25,
        "quality_flag": "missing_calendar",
    }


def _parse_date(val: str | None) -> date | None:
    if not val:
        return None
    try:
        return datetime.strptime(val[:10], "%Y-%m-%d").date()
    except Exception:
        return None
