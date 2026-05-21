# Krishi Pracharak — Solution Document

---

## Team

| Name | Role |
|---|---|
| Rohit Raj | Architecture, AI Pipeline |
| Shivam Kumar | Backend, Product Design |
| Nisha Singh | Frontend, Streamlit Workflow |
| Alok Sharma | Data Collection, Analysis |

**GitHub:** https://github.com/Nishu3005/Krishi-pracharak

---

## Problem Statement

Syngenta field managers spend hours manually identifying which farmers to target, writing campaign messages in multiple languages, and briefing field reps — all from raw spreadsheets. The result is slow campaigns, generic messaging, and missed timing windows tied to crop growth stages.

**Core challenge:** How do you turn a dataset of 6,000 farmer profiles into personalised, timely, multilingual campaign actions — at scale, with no manual effort?

---

## Our Solution — Krishi Pracharak ("Farm Advocate")

An AI-native agricultural marketing platform that takes a crop, a product, and a target region — and automatically produces:

1. A **ranked list of receptive farmers** scored by 7 data signals
2. **Micro-segments** clustered by crop × state × channel × persona
3. **Multilingual campaign content** — WhatsApp, SMS, IVR, poster — in Hindi, Punjabi, Marathi, Gujarati, Kannada, Bengali
4. A **field rep briefing** with ranked actions, restock alerts, and visit gap flags

Everything runs end-to-end from a single UI with no manual steps between data and deployment.

---

## How AI / ML Adds Value

### 1. Receptivity Scoring Model (7 signals)

Every grower in the dataset is scored 0–1 before any campaign is sent. The score combines:

| Signal | Weight | Logic |
|---|---|---|
| Timing urgency | +0.25 | Peaks 7 days before a critical crop stage (sowing, heading, harvest) |
| State baseline | +0.15 | Madhya Pradesh highest; Haryana lowest (calibrated from dataset) |
| Farm size tier | +0.10 | 1–2 acre farms respond best to digital campaigns |
| Scan signal | +0.06 | Grower scanned a Syngenta product QR — strong buying-intent signal |
| Engagement history | +0.05 | Previous WhatsApp message opened |
| Gender signal | +0.02 | Female growers show documented uplift in this dataset |
| Fatigue penalty | −0.08 | Contradictory device signals — likely stale data, deprioritised |

**Eligibility threshold: score ≥ 0.30.** Below this, the grower is not targeted. This prevents wasted spend on unreceptive farmers.

### 2. AI Segmentation Agent (Claude Sonnet)

After scoring, the targeting agent clusters eligible growers by (crop × state × language × channel × persona). A minimum cluster size of 20 growers prevents micro-fragments. The agent then calls Claude Sonnet once to produce a campaign rationale — explaining which segments to prioritise and why, grounded in the score distribution and crop calendar.

### 3. Content Generation Agent (Claude Haiku)

One LLM call per segment (not per grower) produces all four content formats:
- **WhatsApp** — ≤200 chars, native language, persona-matched tone
- **SMS** — ≤120 chars, native language
- **IVR script** — 30-second spoken script
- **Poster image** — AI-generated via Gemini 2.5 Flash

Each call includes automatic retry and a safe fallback — no campaign fails silently.

### 4. OOS Gate (Out-of-Stock Intelligence)

Before any content is generated, the system checks inventory trends across 4,000 retailers. If a product is trending out-of-stock in a territory, that segment is blocked — preventing campaigns that drive demand for unavailable products.

### 5. Rep Briefing Agent (Claude Haiku)

For growers without smartphones (≈26% of the dataset), campaigns route to `rep_assist` instead of digital channels. The rep agent computes OOS slope from 4 weekly inventory snapshots, detects visit gaps (21-day threshold), and generates a ranked action briefing for each field rep.

---

## Architecture

```
app.py  ──  Home: Grower network + field force analytics
│
├── pages/1_campaign_builder.py
│       ├── agents/targeting_agent.py
│       │       └── utils/receptivity_score.py
│       │               └── utils/crop_calendar.py
│       └── agents/content_agent.py
│               └── utils/ai_client.py  (Token Router)
│
└── pages/2_rep_briefing.py
        └── agents/rep_agent.py
```

**Agent coordination:** `targeting_agent` writes `data/targeting_plan.json`. `rep_agent` reads it — agents share state via plain JSON, no message bus required.

**No database.** State flows through JSON files. Simple to inspect, simple to demo.

---

## Key Features

### Campaign Builder
- Create a campaign: crop, product, states, date window, channel mix
- AI targeting runs automatically — scores all 6,000 growers, segments, checks OOS
- 4 tabs per campaign: **Overview**, **Content Generation**, **Receptivity**, **Rep Briefing**

### Overview Tab
- Dark campaign header with key metrics and pill badges
- Live weather cards for each active state (Open-Meteo, no API key needed)
- AI agent insight block — campaign rationale in plain language
- OOS warning block if any products are blocked
- Segment stats: scored growers, eligible count, offline growers, segments

### Content Generation Tab
- Per-segment content scope table
- One click generates all formats for all segments
- WhatsApp + SMS side by side, IVR full width, poster with prompt
- Each variant shows status badge, character count, model used

### Receptivity Tab
- Score distribution histogram with eligibility threshold line
- Per-signal contribution bar chart
- Open rate by state and farm size tier
- Channel eligibility split (smartphone vs non-smartphone)

### Rep Briefing Tab
- Pick a rep and date → AI generates a ranked action plan
- Restock alerts, visit gaps, offline grower list
- Inventory intelligence: OOS rate by SKU, stock trends, risk heatmap

### Home Dashboard (`localhost:8501`)
- Grower network: 6,000 farmers, 10 states, 33 districts
- Geography, crop, technology, and demographic analytics
- Full Syngenta field imagery hero with live metric strip

---

## Models Used

| Task | Model | Reason |
|---|---|---|
| Targeting rationale | `claude-sonnet-4-6` | Reasoning quality; called once per campaign |
| WhatsApp / SMS / IVR content | `claude-haiku-4-5` | High throughput, low cost; called per segment |
| Rep briefings | `claude-haiku-4-5` | Short output, low latency |
| Poster images | `gemini-2.5-flash-image` | Image generation; failure is non-blocking |

All calls go through a single OpenAI-compatible client pointed at the Token Router base URL.

---

## Dataset Coverage

| Metric | Value |
|---|---|
| Total growers | 6,000 |
| States | 10 |
| Districts | 33 |
| Retailers tracked | 4,000 |
| Languages supported | 6 (Hindi, Punjabi, Marathi, Gujarati, Kannada, Bengali) |
| Avg farm size | 1.97 acres |
| Product scan rate | 19.28% |
| Non-smartphone growers | ~26% |

---

## Core Innovation

> A crop-stage-aware, OOS-gated, multilingual AI campaign engine that scores every farmer in real time and delivers deployment-ready content and rep briefings in under two minutes — replacing days of manual field planning.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit + custom CSS (Space Grotesk + Source Serif 4) |
| Charts | Plotly |
| AI agents | Anthropic Claude (Sonnet 4.6 + Haiku 4.5) via Token Router |
| Image generation | Google Gemini 2.5 Flash |
| Weather | Open-Meteo (free, no key) |
| Storage | JSON files (no database) |
| Language | Python 3.11 |

---

## Setup

```bash
git clone https://github.com/Nishu3005/Krishi-pracharak.git
cd Krishi-pracharak
pip install -r requirements.txt

# Create .env with:
# OPENAI_API_KEY=your_token_router_key
# OPENAI_BASE_URL=your_token_router_base_url

streamlit run app.py
```

Open `http://localhost:8501`

---
