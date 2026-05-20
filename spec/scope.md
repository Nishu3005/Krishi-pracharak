# Realistic Scope — What We're Actually Building

## Deadline Context
May 20, 2026. One day. We need a working prototype + doc.

---

## What the Problem Statement Literally Asks For (4 things)

1. **Content generation** — crop × region × stage × language × tone → actual messages
2. **Targeting + timing** — who gets what, when, via which channel
3. **Receptivity prediction** — score which format/message will get highest engagement
4. **Scale personalization** — 5-10 variants → thousands, without human effort

**Success metric:** campaign-to-action conversion rate.

---

## What Our Data Supports (vs What It Doesn't)

### Data we HAVE and CAN use:
- Grower profiles + crop calendars → targeting + timing
- WA engagement history (open/click) → receptivity model training signal
- Device type → channel routing (WA vs SMS vs rep visit)
- Language → content language
- Territory + state → regional calibration
- POS + inventory → OOS-aware campaign gating
- Offline campaign attendance + product scans → cross-channel context

### Data explicitly mentioned in problem but NOT provided:
- Weather data (public domain)
- Satellite imagery
- Pest surveillance reports

**We acknowledge these in the doc as "in production, these signals would be added."
We don't fake or simulate them.**

---

## Actual Build Scope (Realistic for 1 day)

### What we build:
1. **Receptivity Scorer** (`utils/receptivity_score.py`)
   - Input: grower profile + context
   - Output: 0-1 score based on: stage timing, state, farm size, device, engagement history, cross-channel fatigue
   - This is the "predict campaign receptivity" requirement — it's a scoring function, not ML training
   - Backed by the 10 data findings (these ARE the model)

2. **Targeting Agent** (`agents/targeting_agent.py`)
   - Claude + data tools
   - Reads scored growers, groups into micro-segments, outputs targeting plan JSON
   - Decides: who gets WA vs SMS vs rep visit
   - Blocks campaigns where product is OOS in territory

3. **Content Agent** (`agents/content_agent.py`)
   - Claude + segment spec
   - Generates actual messages: WhatsApp text, SMS variant, voice script
   - In all 6 languages natively
   - Adapts tone by persona (pre-stage alert, hot lead, re-engagement)

### What we show in Streamlit (3 pages max):
- **Page 1: Campaign Builder** — select crop + week → Agent 1 runs → shows targeting plan with Claude's rationale → click Generate Content → Agent 2 shows messages per segment in all languages
- **Page 2: Receptivity Insights** — visualize the scoring model: show which segments score highest and why, backed by actual WA data
- **Page 3: Rep Briefing (lightweight)** — select rep → show OOS alerts + which keypad growers need in-person visits. No full Agent 3. Just data queries surfaced cleanly.

### What we DON'T build:
- Data chat interface (impressive, not core to the 4 requirements)
- Full Rep Intelligence Agent (mention in doc as "production extension")
- Weather/pest signal integration (note as future signal in doc)
- Streaming UI (nice but not worth the time)
- ML model training (scoring function is sufficient and more explainable)

---

## The Pitch Angle
"We used the provided data to find 10 statistically significant signals that predict engagement.
We encoded these into a receptivity scorer. Claude then uses that scorer to build micro-targeted
campaigns and generate content at scale in 6 languages — without a proportional increase in 
human effort."

That directly answers all 4 requirements.

---

## File Structure (Final)

```
syngenta/
├── spec/                          # planning docs
├── app.py                         # Streamlit entry
├── pages/
│   ├── 1_campaign_builder.py
│   ├── 2_receptivity_insights.py
│   └── 3_rep_briefing.py
├── agents/
│   ├── targeting_agent.py         # Claude + tools → targeting_plan.json
│   └── content_agent.py           # Claude → content_variants.json
├── utils/
│   ├── data_loader.py             # load + cache all CSVs
│   ├── receptivity_score.py       # scoring function (the "model")
│   └── crop_calendar.py           # stage window logic
└── data/
    ├── targeting_plan.json
    └── content_variants.json
```

---

## Doc Outline (10 pages)

1. Problem interpretation — mass campaigns fail because of hyper-locality
2. Our approach — receptivity scoring + AI-native content generation
3. Data strategy — 10 signals, what each predicts, why we used it
4. Receptivity model — the scoring function, feature weights backed by data
5. Targeting architecture — Agent 1: how segments are built
6. Content generation — Agent 2: how Claude scales to 6 languages
7. System architecture diagram — data flow, agents, Streamlit
8. Expected impact — projected open rate lift: ~23.5% baseline → estimated 27-29% with scoring
9. Production extensions — weather signals, pest data, rep agent, ML model training
10. Limitations and honest acknowledgements
