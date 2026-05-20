# Syngenta Hackathon - Master Spec (Execution-Ready)

This file is canonical. `scope.md` and `brainstorm.md` are supporting context.

---

## 1) Problem Alignment

We must satisfy all 4 required outcomes:

1. Generate context-aware content (crop, region, stage, language, channel)
2. Optimize targeting and timing (who gets what, when, which channel)
3. Predict campaign receptivity (segment-level response likelihood)
4. Scale personalization (few variants to many micro-segments without proportional human effort)

Primary business metric:
- campaign-to-action conversion rate

Operational guardrails:
- avoid promoting products in territories with near-term stockout risk
- ensure non-smartphone growers receive planned outreach path

---

## 2) Data Reality Constraints (Hard Rules)

1. `whatsapp_campaign.csv` has exactly 1 message row per smartphone grower (4,479 rows). No multi-touch history.
2. Crop stage dates exist only for wheat, mustard, and chickpea; other crops have empty `stages` arrays.
3. `digital_funnel_weekly.csv` is campaign-level aggregate (4 campaigns x 26 weeks), not grower-level.
4. `grower_crop_calendar` is missing for 450 growers (7.5%).
5. Weather, satellite, and pest signals are not provided in this dataset.

Design rule:
- no feature may assume unavailable signals.

---

## 3) Architecture Overview

```text
8 CSV files
  -> utils/data_loader.py       (typed loading, parsing, cache)
  -> utils/features.py          (joins + feature derivation)
  -> utils/crop_calendar.py     (timing logic and fallback)
  -> utils/receptivity_score.py (transparent weighted scoring)
  -> agents/targeting_agent.py  (eligibility, routing, segmentation, rationale)
  -> agents/content_agent.py    (multilingual content variants)
  -> agents/rep_agent.py        (territory action briefings)
  -> Streamlit pages            (campaign builder, insights, rep briefing)
```

---

## 4) File Structure (Definitive)

```text
syngenta/
|-- app.py
|-- pages/
|   |-- 1_campaign_builder.py
|   |-- 2_receptivity_insights.py
|   |-- 3_rep_briefing.py
|-- agents/
|   |-- targeting_agent.py
|   |-- content_agent.py
|   |-- rep_agent.py
|-- utils/
|   |-- ai_client.py
|   |-- data_loader.py
|   |-- features.py
|   |-- receptivity_score.py
|   |-- crop_calendar.py
|-- data/
|   |-- targeting_plan.json
|   |-- content_variants.json
|   |-- rep_briefings.json
|-- spec/
|   |-- decisions.md
|   |-- brainstorm.md
|   |-- data_analysis.md
|   |-- models.md
|   `-- scope.md
```

---

## 5) Module Contracts

### `utils/data_loader.py`

All loaders are `@st.cache_data`, parse dates, and parse JSON-like columns.

- `load_growers()`
- `load_whatsapp()`
- `load_retailers()`
- `load_inventory()`
- `load_pos()`
- `load_reps()`
- `load_visits()`
- `load_digital_funnel()`

Validation performed during load:
- required columns present
- no duplicate primary keys where uniqueness is expected
- parse failures counted and surfaced as warnings

### `utils/crop_calendar.py`

`get_timing(crop_calendar: dict | None, reference_date: date) -> dict`

Returns:
- `mode`: `stage_based` | `season_phase` | `unknown`
- `label`: stage/phase label
- `days_until`: int | None
- `urgency`: float in [0, 1]
- `quality_flag`: `ok` | `missing_calendar` | `missing_stages`

### `utils/features.py`

`build_grower_features(reference_date: date) -> pd.DataFrame`

Adds normalized columns:
- `wa_delivered`, `wa_opened`, `wa_clicked`, `has_wa_history`
- `territory_id` (via tehsil/retailer mapping)
- `inventory_risk_score` and `inventory_blocked` (SKU + territory + recent weeks)
- `rep_visit_gap_days`
- `timing_mode`, `days_to_next_stage`, `season_phase`, `timing_urgency`
- `data_quality_flags` (list-like serialized field)

### `utils/receptivity_score.py`

`score_grower(row: pd.Series) -> dict`

Returns:
- `score`: float [0, 1]
- `breakdown`: feature-level contributions
- `score_confidence`: `high` | `medium` | `low` (depends on missingness)

Scoring policy:
- transparent weighted heuristic (no black-box training)
- contributions logged for explainability in UI

### `utils/ai_client.py`

- `get_client()` singleton from env
- `call_text(model, system, user, temperature=0.7) -> str`
- `call_image(model, prompt) -> str | None`

Failure policy:
- text call failure raises explicit exception
- image call failure returns `None` with warning

---

## 6) Agent Contracts

### `agents/targeting_agent.py`

`run_targeting(reference_date: date, crop_filter: str | None, state_filter: str | None) -> dict`

Pipeline:
1. Build features for all growers (target baseline is 6,000 scored rows).
2. Compute receptivity score and confidence.
3. Apply eligibility threshold (default >= 0.30).
4. Apply inventory gate (`inventory_blocked=True` => segment not campaign-eligible).
5. Route channels:
   - smartphone -> `whatsapp`
   - keypad/unknown -> `sms_ivr` or `rep_assist`
6. Assign personas:
   - `hot_lead` (scan=true and offline=false)
   - `pre_stage_alert` (days_to_next_stage in [0,14])
   - `offline_reinforcement` (offline=true and scan=false)
   - `awareness` (fallback)
7. Segment by `(crop, state, language, channel, persona)`.
8. One reasoning-model call for human-readable rationale.
9. Write `data/targeting_plan.json`.

Minimum output fields:
- `generated_at`, `reference_date`, `rationale`
- `total_growers_scored`
- `segments[]` with counts, score stats, confidence stats
- `oos_blocked[]`
- `quality_summary` (missingness and fallback counts)

### `agents/content_agent.py`

`run_content_generation(targeting_plan: dict) -> dict`

For each campaign-eligible segment:
1. Generate WA copy (when channel supports WA)
2. Generate SMS copy
3. Generate IVR script
4. Generate poster prompt and optional image

Output includes:
- language
- persona
- channel applicability
- text variants
- poster fields
- model ids used

### `agents/rep_agent.py`

`run_rep_briefing(rep_id: str, reference_date: date) -> dict`

Pipeline:
1. Resolve rep territory and tehsils.
2. Compute SKU-level stockout trend from recent inventory windows.
3. Compute visit gaps and demand velocity by tehsil.
4. Read `data/targeting_plan.json` — extract all growers with `channel=rep_assist` in this rep's territory. These become mandatory visit items ranked above all other actions.
5. Compute offline-priority grower counts (non-smartphone device types).
6. Rank actions: rep_assist growers first, then OOS risk DESC, then visit gap DESC, then POS velocity DESC.
7. One Haiku call for narrative briefing paragraph.
8. Write/update `data/rep_briefings.json`.

---

## 7) Product-Mapping Policy

Campaign product selection per segment:
1. If crop has a known campaign mapping (4 crops from campaign tables), use it.
2. Else: choose highest-demand SKU for that crop from POS history (all-territory aggregate).
3. If that SKU has inventory_blocked=True in the segment's territory, downgrade to the next highest-demand in-stock SKU.

Known campaign mappings (from digital_funnel_weekly.csv):
- wheat -> Topik 15 WP
- mustard -> Score 250 EC
- chickpea -> Actara 25 WG
- potato -> Kavach 75 WP

Remaining crops (barley, lentil, maize, cumin, safflower) -> POS fallback.

All product picks in output must carry `selection_reason` and `inventory_check_window`.

---

## 7b) Product Catalog (Hardcoded in `utils/product_catalog.py`)

The CSVs contain no product descriptions. Content generation requires knowing what each
product does and which pest/disease it targets. This is hardcoded — not inferred by the model.

```python
PRODUCT_CATALOG = {
    "Tilt 250 EC":       {"type": "fungicide",   "target": "leaf rust, powdery mildew", "crop_fit": ["wheat", "barley"]},
    "Score 250 EC":      {"type": "fungicide",   "target": "scab, alternaria blight",   "crop_fit": ["mustard", "potato"]},
    "Amistar 250 SC":    {"type": "fungicide",   "target": "sheath blight, blast",      "crop_fit": ["wheat", "maize"]},
    "Alto 5 SC":         {"type": "fungicide",   "target": "powdery mildew, rust",      "crop_fit": ["wheat", "chickpea"]},
    "Kavach 75 WP":      {"type": "fungicide",   "target": "early/late blight",         "crop_fit": ["potato", "tomato"]},
    "Actara 25 WG":      {"type": "insecticide", "target": "aphids, whitefly, thrips",  "crop_fit": ["chickpea", "cotton"]},
    "Cruiser 350 FS":    {"type": "seed treatment", "target": "soil insects, seedling pests", "crop_fit": ["wheat", "maize"]},
    "Vibrance Integral": {"type": "seed treatment", "target": "seed-borne diseases",    "crop_fit": ["wheat", "barley"]},
    "Axial 50 EC":       {"type": "herbicide",   "target": "grassy weeds",              "crop_fit": ["wheat", "barley"]},
    "Topik 15 WP":       {"type": "herbicide",   "target": "wild oat, grassy weeds",    "crop_fit": ["wheat"]},
    "Vertimec 1.8 EC":   {"type": "acaricide/insecticide", "target": "mites, leafminers", "crop_fit": ["potato", "vegetables"]},
    "Movondo":           {"type": "fungicide",   "target": "downy mildew, anthracnose", "crop_fit": ["maize", "sorghum"]},
}
```

content_agent.py calls `get_product_context(sku_name)` which reads from this catalog.
No LLM inference for product facts — facts come from catalog only.

---

## 8) Evaluation Protocol (Offline, Reproducible)

### 8.1 Validation Setup (Honest Framing)

This is retrospective correlation validation, not a true held-out predictive test.
We have 1 WA message per grower — no true train/test split is possible.

What we show: score growers using all available signals, then check whether
top-quartile growers have higher observed open/click rates in the historical data.
This demonstrates the scoring function aligns with real engagement patterns.

Framing in demo and doc: "historical correlation validation — in production, retraining
on new campaign data would enable true holdout evaluation."

Reference split (for narrative context only):
- calibration window: October 2025 to January 2026
- validation context: February 2026 to March 2026

### 8.2 Metrics

Primary:
- lift in open/click rate for top-scored cohort vs baseline

Secondary:
- OOS-prevented campaign count
- non-smartphone coverage rate
- segment quality (minimum growers per segment)

### 8.3 Acceptance Thresholds

- top-quartile open rate >= baseline + 2 percentage points
- 100% of blocked segments have explicit OOS reason
- >= 95% growers receive valid channel route
- 100% generated content has language and persona labels

---

## 9) Streamlit Pages

### `app.py`
- page config and navigation only

### `pages/1_campaign_builder.py`
- inputs: reference date, crop, optional state
- actions: build targeting plan, generate content, export JSON
- must display: rationale, blocked segments, quality summary

### `pages/2_receptivity_insights.py`
- no LLM calls
- charts: score distribution, feature contribution, state view, channel split
- include baseline vs targeted lift panel

### `pages/3_rep_briefing.py`
- rep selector and date
- display ranked actions, OOS alerts, visit gaps, offline-grower priorities

---

## 10) Execution Plan (What Was Missing)

### Phase P0 - Foundation
- implement loaders, parsers, and data validation
- implement feature joins and timing fallback

### Phase P1 - Decision Engine
- implement scoring and targeting logic
- implement OOS gate and segmentation

### Phase P2 - Generation Layer
- implement content generation and rep briefing narrative
- implement structured outputs and export

### Phase P3 - Demo Hardening
- add insight page metrics
- run backtest metrics and freeze demo dataset snapshots

---

## 11) Risk Register and Mitigations

1. Missing crop calendar rows
- mitigation: null-safe timing fallback and confidence downgrade

2. Missing scan product names for some scanned growers
- mitigation: keep scan signal but avoid product-personalized CTA for those rows

3. Weak territory mapping in sparse geographies
- mitigation: fallback to district-level aggregate when tehsil mapping fails

4. Over-segmentation leading to tiny segments
- mitigation: minimum segment size = 20 growers. Segments below this are merged into the nearest segment on (crop, channel) before output. No exceptions.

5. Image generation instability
- mitigation: never block text output on image failure

---

## 12) Out of Scope

- weather/satellite/pest integration
- live WhatsApp/SMS dispatch integrations
- online model retraining pipeline
- multi-touch sequential policy learning
- audio rendering (text IVR script only)

---

## 13) Environment Variables

- `TOKEN_ROUTER_KEY`
- `TOKEN_ROUTER_BASE_URL`
- `DATA_DIR=Syngenta_IITM_Hackathon_2026_dataset`

Loaded via `python-dotenv`.
