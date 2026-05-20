# Brainstorm - AI Native Platform (Level-Up Version)

## Core Philosophy

The model is the reasoning engine.
Python modules are deterministic data tools that provide clean, explainable inputs.

Design rule: model creativity for messaging, deterministic logic for eligibility, routing, and safety gates.

---

## Problem-First Design Lens

Every feature must map to at least one hackathon requirement:

1. Context-aware content
2. Targeting and timing optimization
3. Receptivity prediction
4. Scaled personalization

If a feature does not improve one of these, it is not in MVP.

---

## The 3 Agents (Data-Grounded)

### Agent 1: Campaign Intelligence Agent

Role: Decide who should be targeted, with what product, in which week, via which channel.
Trigger: Weekly or on-demand from Streamlit.

Reasoning tasks:
1. Build grower micro-segments by crop, language, state, channel eligibility, and engagement profile.
2. Compute urgency using crop stage dates where available (wheat/mustard/chickpea).
3. For crops without stage dates, use season-phase fallback from sowing/harvest windows.
4. Apply territory-level inventory OOS gate before recommending any campaign push.
5. Score receptivity with transparent weighted signals.

Important dataset constraint:
- WhatsApp history has one row per grower in this dataset window, so "last 3 message" fatigue logic is not valid for this prototype.

Core tools:
- `get_growers(filters)`
- `get_crop_timing_features(grower_id)`
- `get_receptivity_score(grower_id)`
- `get_inventory_risk(territory_id, sku_name, week)`
- `get_channel_eligibility(grower_id)`

Output: `data/targeting_plan.json`

---

### Agent 2: Content Generation Agent

Role: Generate localized, channel-ready campaign content per segment.
Trigger: Runs after Agent 1 output is finalized.

Per segment outputs:
1. WhatsApp message
2. SMS variant
3. IVR script (approximately 30 seconds)
4. Poster concept prompt

Tone/persona mapping:
- `pre_stage_alert`: urgency and prevention
- `conversion_push`: scanner-driven action CTA
- `low_touch_reengage`: lighter and trust-building
- `offline_followup`: reinforce field interaction
- `new_or_uncertain`: educational framing

Core tools:
- `get_segment_spec(segment_id)`
- `get_product_context(sku_name)`
- `get_language_style_guide(language)`
- `get_few_shot_examples(crop, language, channel)`

Output: `data/content_variants.json`

---

### Agent 3: Rep Intelligence Agent

Role: Produce weekly rep action plans with ranked priorities.
Trigger: Weekly batch or rep-specific on-demand generation.

Reasoning tasks:
1. Identify tehsils with rising OOS risk and active demand.
2. Detect mismatches: high demand or engagement but low recent field coverage.
3. Prioritize actions by impact score (stock risk, demand velocity, visit recency).
4. Explicitly include non-smartphone growers for assisted outreach.

Core tools:
- `get_rep_scope(rep_id)`
- `get_tehsil_oos_trends(territory_id)`
- `get_sku_sales_velocity(territory_id)`
- `get_visit_recency(territory_id, tehsil)`
- `get_offline_priority_growers(territory_id)`

Output: `data/rep_briefings.json`

---

## Streamlit Pages (Judge-Focused)

### Page 1: Campaign Builder

Purpose: show targeting plus generated multilingual content in one flow.

Flow:
1. user picks week, optional state/crop filters
2. run Agent 1 and show segment table with rationale
3. run Agent 2 and show WA/SMS/IVR/poster prompts by segment
4. export JSON artifacts

### Page 2: Receptivity and Targeting Insights

Purpose: explain why the system targeted specific segments.

Display:
- top features driving receptivity
- channel split (WA vs SMS/IVR/rep)
- stock-risk blockers and prevented campaigns

### Page 3: Rep Briefing

Purpose: turn analytics into field action.

Display:
- ranked action cards
- OOS alerts by tehsil/product
- assisted-outreach list for keypad/unknown growers

Optional stretch page (only if time permits): Data Q&A assistant.

---

## Frontend Direction (No Generic Dashboard Feel)

UI strategy for hackathon demo:
1. The app should feel like a weekly command center, not a static BI dashboard.
2. Every page needs one hero message and one clear action path.
3. Show decisions first, charts second. Lead with "what to do now".
4. Use a consistent visual identity (earth-tone palette, serif headline + modern body font).
5. Keep interaction density high but scannable: cards, short rationale blocks, ranked actions.

Page-level choreography:
1. Campaign Builder:
- Step sequence: Inputs -> Targeting rationale -> Segment table -> Content variants -> JSON export.
- Explicitly show blocked campaigns to build trust.

2. Receptivity Insights:
- Start with baseline vs targeted lift.
- Then show score distribution and top signals.
- End with channel/timing coverage to prove practical rollout feasibility.

3. Rep Briefing:
- Start with ranked actions and why each action is ranked.
- Keep offline grower list visible for immediate field execution.

Demo polish requirements:
1. No placeholder text in final run.
2. No empty cards without explanation.
3. If image generation fails, preserve text flow and show graceful fallback.
4. Keep a single visual language across all pages.

---

## What Upgrades This Spec

1. Uses all 8 CSVs with explicit role definitions.
2. Removes assumptions unsupported by current data.
3. Adds deterministic safety gates (inventory-aware campaign blocking).
4. Balances digital and offline channels for the 25%+ non-smartphone cohort.
5. Produces explainable artifacts judges can inspect quickly.

---

## MVP Priorities (Execution Order)

1. Build reliable data joins and feature layer.
2. Implement receptivity scoring and channel eligibility.
3. Implement Agent 1 targeting plus OOS gate.
4. Implement Agent 2 multilingual content variants.
5. Implement Agent 3 rep briefing actions.
6. Wire Streamlit pages and export pipeline.

---

## Unattended Areas (Now Explicitly Covered)

1. Missing crop calendar rows:
- Fallback to season-phase timing plus confidence downgrade.

2. Crops without stage arrays:
- Use dual timing mode (`stage_based` vs `season_phase`) instead of forcing stage logic.

3. Product choice ambiguity per segment:
- Use campaign mapping first, then POS-demand fallback, then in-stock downgrade.

4. Tiny segment explosion:
- Merge segments below minimum grower count threshold to keep outputs actionable.

5. Data-quality explainability:
- Include quality flags in targeting outputs so judges can see where fallbacks were applied.

---

## Build Checklist (Execution-Grade)

1. Add loader validation and parse-warning counters.
2. Implement features join with territory mapping fallbacks.
3. Implement scoring plus score-confidence output.
4. Implement targeting output contract including `quality_summary`.
5. Implement content output contract with per-segment model metadata.
6. Implement rep briefing ranking formula and evidence fields.
7. Add insights page baseline-vs-targeted lift panel.
8. Dry-run one full end-to-end export before demo lock.

---

## Open Decisions (With Recommendation)

1. Include Data Chat page?
- Recommendation: defer unless core 3 pages are stable.

2. Show map visualizations?
- Recommendation: simple tables plus rationale first; add maps only if spare time.

3. Simulate message sending?
- Recommendation: no live send; show export-ready payloads and action queues.

4. Model trace visibility?
- Recommendation: show compact rationale, not full chain-of-thought.
