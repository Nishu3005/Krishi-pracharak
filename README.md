# 🌾 Krishi Pracharak

> AI-Native Agricultural Marketing Platform · Syngenta × IITM Hackathon 2026

Krishi Pracharak ("Farm Advocate") turns raw field data into hyper-local campaign decisions, multilingual content, and ranked field-rep actions — all from a single operational flow.

---

## What it does

| Problem Statement Requirement | How this platform addresses it |
|---|---|
| Context-aware content in multiple languages | Content agent generates WhatsApp, SMS, IVR, and poster variants in Hindi, Punjabi, Marathi, Gujarati, Kannada, and Bengali — one call per segment, language-aware prompts |
| Optimise campaign targeting and timing | Targeting agent scores every grower, applies crop-stage timing logic, gates out OOS territories, and routes to the right channel before sending anything |
| Predict campaign receptivity | 7-signal heuristic scoring model (0–1) combining timing urgency, engagement history, farm size, state baseline, fatigue penalty, scan signal, and gender signal |
| Scale personalisation to thousands | Micro-segmentation clusters growers by (crop × state × channel × persona) with a 20-grower minimum; a single LLM call produces content for each cluster, not each individual |

---

## Architecture

```
app.py  (Streamlit home — grower network + field force analytics)
│
├── pages/1_campaign_builder.py      ← Campaign list + detail (Overview / Content / Receptivity)
│       │
│       ├── agents/targeting_agent.py
│       │       └── utils/features.py  →  utils/receptivity_score.py
│       │               └── utils/crop_calendar.py
│       │
│       └── agents/content_agent.py
│               └── utils/ai_client.py  (Token Router)
│
└── pages/2_rep_briefing.py          ← Inventory intelligence + field execution layer
        └── agents/rep_agent.py
                ├── reads data/targeting_plan.json  (written by targeting_agent)
                └── utils/ai_client.py
```

**Agent coordination:** `targeting_agent` writes `data/targeting_plan.json`. `rep_agent` reads it to surface rep-assist growers — agents share state via a plain JSON file, no message bus needed.

---

## Pages

### 1 — Campaign Builder

- Sidebar lists all active campaigns by name and a **＋ New Campaign** entry.
- Clicking a campaign opens a hero banner, then three horizontal tabs:
  - **Overview** — Gantt timeline, India geo map of active states, live weather cards (Open-Meteo, no key), rationale, and segments table.
  - **Content Generation** — generates WhatsApp, SMS, IVR, and poster variants per segment. Each asset shows status badge (success / fallback), character count, and model used. One automatic retry on API failure before falling back to a safe placeholder.
  - **Receptivity** — score distribution, per-signal contribution, state and farm-size breakdowns, channel split.
- **New Campaign form**: campaign name, objective, crop, state, date window (start → end), channel mix multi-select, and optional budget. These are stored top-level in the campaign JSON, not buried in `source_meta`.

### 2 — Rep Briefing

- **Inventory Intelligence** section shows stock health across 4 000 retailers: OOS rate by SKU, weekly stock trends, and an OOS-rate heatmap (SKU × week).
- Pick a rep and reference date, then **Generate Briefing** computes OOS slope from last 4 weekly inventory snapshots, detects visit gaps (21-day threshold), pulls rep-assist growers from the targeting plan, and asks Haiku for a 3–4 sentence action briefing.
- Shows metric cards, ranked action expanders, and an offline-grower table.

---

## Scoring model — 7 signals

| Signal | Max contribution | Notes |
|---|---|---|
| Timing urgency | 0.25 | Peaks 7 days before crop stage; season-phase fallback for other crops |
| State baseline | 0.15 | MP highest; Haryana lowest |
| Farm size tier | 0.10 | 1–2 ac best; 5+ ac lowest |
| Scan signal | +0.06 | Grower scanned QR and is reachable digitally |
| Engagement history | +0.05 | Previous WA message opened |
| Gender signal | +0.02 | Female grower (documented uplift in data) |
| Fatigue penalty | −0.08 | Offline device AND scan signal both present (contradictory — likely stale data) |

Eligibility threshold: **score ≥ 0.30**. Scores below this are not targeted.

---

## Models used

| Task | Model | Why |
|---|---|---|
| Targeting rationale (1 call) | `anthropic/claude-sonnet-4-6` | Needs reasoning quality; called once per run |
| WA / SMS / IVR content | `anthropic/claude-haiku-4-5` | High throughput, low cost; called per segment |
| Rep briefings | `anthropic/claude-haiku-4-5` | Short output, low latency |
| Poster images | `google/gemini-2.5-flash-image` | Only model available via Token Router for image gen; failure is non-blocking |

All calls go through a single OpenAI-compatible client (`utils/ai_client.py`) pointed at the Token Router base URL.

---

## Setup

### 1. Clone and install

```bash
git clone <repo-url>
cd syngenta
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — fill in TOKEN_ROUTER_KEY and TOKEN_ROUTER_BASE_URL
```

See [.env.example](.env.example) for a description of every variable.

### 3. Weather integration (no setup required)

Weather data is fetched via [Open-Meteo](https://open-meteo.com) — a free, no-API-key weather service. The `utils/weather_client.py` module has a 5-second timeout and returns `None` on any failure; the UI renders gracefully when weather is unavailable. No additional configuration is needed.

### 4. Place the dataset

The `Syngenta_IITM_Hackathon_2026_dataset/` folder (8 CSV files + analysis modules) must sit at the repo root. This matches the default `DATA_DIR` value. Do not rename the folder unless you also update `DATA_DIR` in `.env`.

> **Data confidentiality** — the Syngenta dataset is strictly confidential and intended solely for use in the Syngenta IITM Hackathon 2026. Do not share, publish, or distribute it in any form.

### 5. Run

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## File structure

```text
syngenta/
├── app.py                          # Home page — grower network + field force analytics
├── pages/
│   ├── 1_campaign_builder.py       # Campaign list, detail view, content gen, receptivity
│   └── 2_rep_briefing.py           # Inventory intelligence + field rep briefing
├── agents/
│   ├── targeting_agent.py          # Scoring → segmentation → OOS gate → rationale
│   ├── content_agent.py            # Multilingual WA/SMS/IVR/poster generation
│   └── rep_agent.py                # OOS slope + visit gap + rep-assist actions
├── utils/
│   ├── ai_client.py                # Token Router singleton client
│   ├── campaign_store.py           # JSON persistence for campaigns (save, attach, load)
│   ├── crop_calendar.py            # Stage-based and season-phase timing logic
│   ├── data_loader.py              # @st.cache_data loaders for all 8 CSVs
│   ├── features.py                 # Joins all signals into a flat grower feature frame
│   ├── product_catalog.py          # Hardcoded 12-SKU catalog + campaign product mapping
│   ├── receptivity_score.py        # 7-signal heuristic scorer
│   ├── targeting_logic.py          # Shared product selection + OOS block lookup
│   ├── weather_client.py           # Open-Meteo weather fetch (free, no key, hard fallback)
│   └── ui_theme.py                 # apply_theme() and render_hero() shared by all pages
├── Syngenta_IITM_Hackathon_2026_dataset/
│   ├── growers_analysis.py         # Deep grower insights (demographics, crop, language, device)
│   ├── reps_analysis.py            # Field force coverage analysis (territory, tehsil density)
│   ├── inventory_analysis.py       # OOS risk, stock trends, depletion slope per SKU
│   └── *.csv                       # Raw dataset files (8 CSVs)
├── spec/                           # Design decisions, data analysis, model choices
├── data/                           # Runtime output: targeting_plan.json, etc. (git-ignored)
├── requirements.txt
├── .env.example
└── .env                            # Not committed — copy from .env.example
```

---

## Key design decisions

- **No database.** State flows through JSON files in `data/`. Agents read and write plain files — simple to inspect, simple to demo.
- **OOS gate.** If a product is trending out-of-stock in a territory, campaigns for that product are blocked. Showing judges an OOS-aware system is the differentiator.
- **Channel routing.** Non-smartphone growers (≈26% of the dataset) are never sent WhatsApp messages. They are routed to `rep_assist` and surfaced in the rep briefing.
- **Minimum segment size (20 growers).** Prevents micro-fragments that would generate content for 1–2 people. Sub-threshold clusters are merged into the nearest (crop, channel) peer.
- **Receptivity insights integrated into campaigns.** Rather than a separate page, receptivity charts live inside each campaign's detail view — so evidence is co-located with the targeting decision it validates.
- **Weather context without an API key.** Open-Meteo is called at runtime; `utils/weather_client.py` enforces a 5-second timeout and returns `None` on any failure. The UI renders cards that say "No data" rather than throwing an error.
- **Campaign identity as a first-class field.** `campaign_name`, `campaign_objective`, `date_window`, and `channel_mix` are stored top-level in the campaign JSON — not buried in `source_meta` — so the sidebar, hero banner, and overview tab can read them directly.
- **Content generation with retry + metadata.** Each format (WhatsApp, SMS, IVR, poster) is wrapped in a single-retry call. The variant JSON includes `status`, `char_count`, `generated_at`, and `model` per format so the UI can show evidence of quality without re-running.

---

## Requirements

- Python 3.10+
- See `requirements.txt` for package versions.
- A valid Token Router API key with access to `anthropic/claude-sonnet-4-6`, `anthropic/claude-haiku-4-5`, and `google/gemini-2.5-flash-image`.
