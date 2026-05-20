from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def data_dir() -> Path:
    path = Path(__file__).parent.parent / "data"
    path.mkdir(exist_ok=True)
    return path


def save_plan(plan: dict, path: Path | None = None, source_meta: dict | None = None) -> Path:
    if path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = data_dir() / f"campaign_{ts}.json"

    payload = dict(plan)
    if source_meta:
        payload["source_meta"] = source_meta
    payload.setdefault("artifacts", {})
    payload["artifacts"]["plan_saved_at"] = datetime.utcnow().isoformat()
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def attach_variants(path: Path, variants: dict) -> None:
    if not path.exists():
        return
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return
    payload["content_variants"] = variants
    payload.setdefault("artifacts", {})
    payload["artifacts"]["variants_saved_at"] = datetime.utcnow().isoformat()
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def delete_campaign(path: "str | Path") -> bool:
    p = Path(path)
    if p.exists() and p.is_file():
        p.unlink()
        return True
    return False


def load_saved_campaigns() -> list[dict]:
    root = data_dir()
    # Only load named campaign files — targeting_plan.json is a transient agent output,
    # not a user-created campaign, and including it causes duplicates in the sidebar.
    files = sorted(
        root.glob("campaign_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    campaigns: list[dict] = []
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        payload["_path"] = str(path)
        payload["_id"] = path.stem
        payload["_filename"] = path.name
        campaigns.append(payload)
    return campaigns

