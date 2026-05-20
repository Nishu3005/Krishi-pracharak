# Deep Data Analysis - Hard Findings (Implementation-Oriented)

## Dataset Summary

- Season window: Rabi 2025-26
- Calendar window: October 2025 to April 2026
- 6,000 growers
- 4,000 retailers
- 500 reps
- 12 products (SKUs)
- 235,042 POS transactions
- 310,544 inventory snapshots
- 30,000 rep visit logs
- 4,479 WhatsApp message records

---

## Finding 1: WhatsApp Coverage Is Broad But Not Targeted

Observed:
- 4,479 WA rows map to 4,479 unique growers
- every WA grower has exactly one message row

Performance baseline:
- delivery: 98.37%
- open: 23.15%
- click overall: 5.05%
- click among opens: 21.79%

Design implication:
- this dataset supports one-shot targeting uplift simulation, not multi-touch sequence optimization.

---

## Finding 2: Stage Timing Works, But Only for Some Crops

In `grower_crop_calendar`, stage dates are present for:
- wheat
- mustard
- chickpea

Several crops have empty stage arrays (barley, potato, lentil, maize, cumin, safflower).

Design implication:
- implement dual timing logic:
  1. stage-based urgency where stage dates exist
  2. season-phase fallback where stage dates are missing

---

## Finding 3: 25%+ of Growers Are Not WhatsApp Eligible

Device split from growers:
- smartphone: 4,479
- keypad: 1,028
- unknown: 493

Total non-smartphone: 1,521 (25.35%).

Design implication:
- channel routing is mandatory:
  - smartphone -> WA eligible
  - keypad/unknown -> SMS/IVR/rep-assisted outreach

---

## Finding 4: Inventory OOS Risk Rises Through the Season

Monthly OOS rates from inventory snapshots:
- 2025-10: 0.33%
- 2025-11: 1.75%
- 2025-12: 2.99%
- 2026-01: 3.89%
- 2026-02: 4.38%
- 2026-03: 4.64%

Design implication:
- inventory gate must block campaigns in low-stock territories.
- rep briefings must escalate replenishment action in late-season weeks.

---

## Finding 5: POS Demand Trends Are Strong for Product Prioritization

Monthly total sold quantity:
- 2025-10: 430,369
- 2025-11: 425,636
- 2025-12: 386,477
- 2026-01: 344,396
- 2026-02: 290,996
- 2026-03: 295,767

Design implication:
- use POS velocity in rep action ranking and product push recommendations.

---

## Finding 6: Cross-Channel Interaction Suggests Fatigue Risk

Observed pattern (from prior analysis):
- scan-only growers show stronger click behavior
- offline + scan overlap performs worse

Design implication:
- avoid over-targeting growers who recently got heavy offline touch plus digital nudges.
- shift these cohorts toward rep-contextual follow-up rather than repeated WA pushes.

---

## Finding 7: State and Farm-Size Effects Should Be Explicit in Scoring

Observed in analysis:
- state-level open rates vary significantly
- 1-2 acre cohort is more responsive than larger farm brackets

Design implication:
- receptivity scoring should include state baseline and farm-size tier weights.

---

## Finding 8: Female Growers Show Better Engagement But Lower Representation

Observed:
- female growers are a smaller share of base but show stronger open rates.

Design implication:
- include targeted segment experiments for women growers with appropriate language/tone.

---

## Finding 9: Digital Funnel Data Is Aggregate-Level

`digital_funnel_weekly.csv` contains campaign-level metrics (4 campaigns over 26 weeks), not grower-level rows.

Design implication:
- use it for top-funnel benchmark context and campaign-level narrative, not micro-targeting decisions.

---

## Finding 10: Cross-Table Join Integrity Is Strong

Cross-file checks show:
- WA grower IDs align with growers table
- inventory and POS retailer IDs align with retailers table
- visit territory/rep IDs align with reps table

Design implication:
- multi-table feature engineering is feasible and reliable for prototype.

---

## Data Quality Notes to Handle Explicitly

1. `grower_crop_calendar` missing for 450 growers (7.5%).
2. 61 rows have `product_scan=true` but blank `product_name`.
3. stage availability differs by crop.
4. dictionary naming mismatch: docs mention `whatsapp_message_log.csv`; actual file is `whatsapp_campaign.csv`.

Mitigation:
- add null-safe fallbacks and data-quality flags in outputs.

---

## Evaluation Risks If Not Addressed

1. Time leakage in validation:
- If future weeks are used to score past weeks, uplift claims become invalid.

2. Coverage inflation:
- Reporting only smartphone cohorts can hide performance on 25%+ offline growers.

3. OOS-blind uplift:
- Better open rates are not meaningful if recommended SKUs are unavailable locally.

4. Over-segmentation artifacts:
- Very small segments can show unstable rates and misleading performance.

Required response:
- enforce time-aware backtesting, report channel coverage, track OOS-blocked decisions, and enforce minimum segment size.

---

## Updated Micro-Segmentation Dimensions

Recommended dimensions:
1. crop
2. state and language
3. timing urgency (stage-based or season-phase)
4. channel eligibility (smartphone vs non-smartphone)
5. engagement profile (scan/offline interaction pattern)
6. farm-size tier

Practical target:
- generate 20 to 40 operational segments per run.

---

## What This Means for the Final Prototype

The strongest demo is not "fancy model claims".
The strongest demo is:
1. trustworthy joins
2. explainable targeting logic
3. multilingual content generation
4. inventory-aware campaign control
5. rep action briefings that include offline growers

That directly matches the problem statement and field reality.
