# Krishi Pracharak — Design Brief for AI-Assisted UI Redesign

> Paste this entire file into Claude, v0.dev, Lovable, or any AI design tool to get a high-quality UI redesign. The brief covers product context, data model, user flows, design goals, and current implementation details.

---

## Product Overview

**Krishi Pracharak** ("Farm Advocate") is an AI-native agricultural marketing platform built for Syngenta India. It turns raw field data about 6,000+ farmers into hyper-local campaign decisions, multilingual content, and ranked field-rep actions.

**Built with:** Python · Streamlit · Plotly · Anthropic Claude API

**Users:** Syngenta marketing managers and field operations teams in India.

**Core value:** A marketing manager can open the app, create a campaign for wheat farmers in Uttar Pradesh, automatically score which farmers are most receptive right now (based on their crop stage, engagement history, device type, and farm size), generate WhatsApp messages in Hindi, and brief the field rep — all in under 10 minutes.

---

## Pages & Navigation

### Left sidebar (Streamlit page nav)
- **Landing / Home** (`app.py`) — Grower network overview + field force analytics
- **Campaign Builder** (`1_campaign_builder.py`) — All campaign work lives here

### Campaign Builder sidebar (sub-navigation)
- List of digital campaigns (from dataset: these are real historical campaigns)
- List of AI campaigns (user-created, saved to JSON)
- Each AI campaign has: name button (opens it) + ✕ delete button
- "＋ New Campaign" button → modal dialog → name entry → creates draft

---

## The Four Campaign Tabs

Every campaign (digital or AI-created) has four tabs:

### 1. Overview
- Hero banner: campaign name, objective, date range, key metrics
- Gantt timeline (crop stage windows per segment)
- India map (dots on active states, sized by grower count)
- Live weather cards for each active state (Open-Meteo API, no key required)
- AI-generated rationale paragraph
- OOS (out-of-stock) warnings if products are blocked
- Targeting segments table

### 2. Content Generation
- Step 1 (collapsible): Build targeting plan — reference date, state filter → scores all growers
- Metrics: growers scored, eligible count, segments, OOS blocked
- Content scope table: all segments with crop, state, language, persona, product, grower count, formats to generate
- "Generate Multilingual Content →" primary button
- After generation: per-segment content cards (WhatsApp + SMS side by side, IVR full width, poster with prompt)

### 3. Receptivity
- Score distribution histogram with threshold line
- Signal contribution bar chart (7 signals)
- Open rate by state, by farm size tier
- Channel eligibility pie (smartphone vs non-smartphone)
- Timing mode coverage pie

### 4. Rep Briefing
- Rep selector + reference date → "Generate Briefing" button
- Metrics: total actions, restock alerts, visit gaps, offline growers
- AI-generated weekly briefing paragraph
- Priority actions (ranked expanders): assisted campaigns, restock alerts, visit gaps
- Offline growers table
- Collapsible: Inventory Intelligence (OOS rate charts, stock trends, risk heatmap)

---

## Data Entities

### Grower
- `grower_id`, `state`, `tehsil`, `district`
- `device_type`: "smartphone" | "feature_phone"
- `gender`
- `grower_farm_size` (acres)
- `grower_crop_calendar`: `{crop, sowing_date, stages: [{stage, date}]}`
- `offline_campaign_attended` (bool)
- `product_scan` (bool — scanned product QR)

### Campaign Segment (output of targeting agent)
- `segment_id`, `crop`, `state`, `language`, `channel`, `persona`
- `product` (Syngenta SKU)
- `stage_context` (e.g. "Heading in 5 days")
- `grower_count`, `avg_score` (0–1 receptivity)
- `grower_ids` list

### Personas (4 types)
| Persona | Trigger | Tone |
|---|---|---|
| `hot_lead` | Scanned QR, not yet attended offline | Direct conversion CTA |
| `pre_stage_alert` | Critical crop stage within 14 days | Urgent, time-sensitive |
| `offline_reinforcement` | Attended field event, no scan | Warm follow-up |
| `awareness` | None of the above | Educational |

### Content Variant (per segment)
- `whatsapp` (≤200 chars, native language)
- `sms` (≤120 chars, native language)
- `ivr_script` (30-second spoken script)
- `poster_image_url` (AI-generated image)
- Each format has metadata: `status`, `char_count`, `model`, `generated_at`

### Languages supported
Hindi, Punjabi, Marathi, Gujarati, Kannada, Bengali

### Field Rep
- `rep_id`, `territory_name`, `state`, `district`
- `tehsil_list` (list of tehsils covered)
- Priority actions: restock alerts, visit gaps, assisted campaign targets

---

## Scoring Model (7 signals)

| Signal | Weight | Logic |
|---|---|---|
| Timing urgency | +0.25 | Peaks 7 days before crop stage |
| State baseline | +0.15 | MP highest; Haryana lowest |
| Farm size tier | +0.10 | 1–2 ac best |
| Scan signal | +0.06 | Grower scanned product QR |
| Engagement history | +0.05 | Previous WA message opened |
| Gender signal | +0.02 | Female grower (uplift in data) |
| Fatigue penalty | −0.08 | Contradictory signals (offline+scan) |

**Threshold: score ≥ 0.30** to be eligible for targeting.

---

## Current Design System

### Colors
| Token | Hex | Usage |
|---|---|---|
| `--accent` | `#2f7d4c` | Primary green (buttons, highlights, active states) |
| `--accent-mid` | `#3d9960` | Hover states, gradients |
| `--accent-soft` | `#d4ead9` | Backgrounds, tags |
| `--signal` | `#b8701f` | Amber (warnings, OOS, lead rate) |
| `--signal-soft` | `#fdf0e0` | Amber backgrounds |
| `--bg` | `#f5f1e8` | App background (warm off-white) |
| `--paper` | `#fffdf7` | Card/panel backgrounds |
| `--ink` | `#1a2520` | Primary text |
| `--muted` | `#5a6b62` | Secondary text |
| `--line` | `#ddd8cc` | Borders |

### Typography
- **Display/headings:** Source Serif 4 (Google Fonts) — 400/600/700
- **Body/UI:** Space Grotesk (Google Fonts) — 300/400/500/600/700

### Hero banner pattern (all campaigns)
Dark green gradient header (`#1a3d28 → #2f7d4c → #1a3d28`) with white text, kicker tag, key metrics as inline chips.

### Component patterns
- Cards: white background, 1px `#ddd8cc` border, `border-radius: 14px`, subtle shadow
- Badges/chips: `border-radius: 999px`, colored by type
- Data tables: bordered, rounded corners, Streamlit `column_config` with progress bars for scores
- Charts: Plotly with transparent backgrounds matching app theme

---

## Design Goals & Gaps to Fix

### What works well
- Dark sidebar with green gradient feels premium
- Hero banners on each campaign are visually strong
- Color palette is distinctive and agricultural

### What needs improvement (highest priority)

1. **Content Generation tab** — currently shows text in plain boxes. Needs WhatsApp-style message bubbles, SMS as a phone mockup, IVR as a script card with microphone icon.

2. **Welcome / landing page of Campaign Builder** — three stock images with no real data hierarchy. Should feel like a proper dashboard with animated counters, a top-campaign highlight card, and a quick-access "recent campaigns" feed.

3. **Segment cards in Overview** — plain dataframe table. Should be visual cards: crop icon, state flag-style badge, persona color coding, grower count as a stat.

4. **Receptivity tab** — charts feel generic. Add contextual annotations, highlight best-performing states with callout boxes, show the score threshold as an annotated line with explanation.

5. **Weather cards** — currently small inline boxes. Should be styled like a proper weather widget: icon large, temp prominent, 3-day forecast as mini-bars.

6. **Mobile responsiveness** — Streamlit is desktop-first but the CSS should not break on 1024px viewport width.

7. **Loading states** — spinners are generic. Add skeleton screens for the heavy data loads (scoring, content generation).

8. **Empty states** — "no data" states are plain text. Should be illustrated empty states with a clear CTA.

---

## Key User Flows to Design Around

### Flow 1: Create and launch a new campaign
1. Click "＋ New Campaign" in sidebar → modal with name input → stub created, opens immediately
2. In Overview tab: fill targeting form (objective, crop, state, dates, channels) → "Build Targeting Plan"
3. Loading → rationale + map + timeline + segments appear
4. Switch to Content Generation tab → scope table shows what will be generated → click "Generate →"
5. Loading → per-segment cards with WhatsApp/SMS/IVR/poster content appear
6. Switch to Rep Briefing tab → select rep → "Generate Briefing" → actions appear

### Flow 2: Review an existing digital campaign
1. Click campaign in sidebar (e.g. "CAMP_WHEAT_001")
2. Overview: timeline + India map (grower states for wheat crop) + weather + weekly data table
3. Content Generation: see scope → generate → review content
4. Rep Briefing: get field actions

### Flow 3: Delete a campaign
1. Click ✕ next to campaign name in sidebar
2. Campaign removed from list, view resets to welcome screen

---

## Technical Constraints for Redesign

- **Streamlit only** — no React, no custom frontend server. All UI must be achievable via `st.markdown(unsafe_allow_html=True)`, CSS overrides in `ui_theme.py`, Plotly figures, and standard Streamlit widgets.
- **No external image hosting** — images must be URLs (e.g. Syngenta website, Unsplash) or base64-encoded SVGs inline in HTML.
- **Plotly for all charts** — no D3, no Recharts, no Chart.js.
- **Google Fonts** — already loaded: Space Grotesk + Source Serif 4. Can add more.
- **CSS injection** — via `st.markdown('<style>...</style>', unsafe_allow_html=True)` in `utils/ui_theme.py`'s `apply_theme()` function.
- **Custom HTML components** — via `st.markdown('<div>...</div>', unsafe_allow_html=True)`.
- **No JavaScript** — Streamlit does not allow custom JS (without `components.html`).

---

## Files to Edit for UI Changes

| File | What it controls |
|---|---|
| `utils/ui_theme.py` | Global CSS (`apply_theme()`), hero component (`render_hero()`) |
| `pages/1_campaign_builder.py` | All campaign UI: sidebar, tabs, charts, cards, forms |
| `app.py` | Landing page: grower network + field force analytics |

---

## Prompt for AI Design Tool

> "Design a premium agricultural marketing SaaS dashboard for Syngenta India. The app is called Krishi Pracharak ('Farm Advocate'). It helps marketing managers create hyper-targeted campaigns for 6,000+ farmers across India. Key pages: (1) Campaign Builder with 4 tabs — Overview (India map + Gantt timeline + weather cards + segments), Content Generation (multilingual WhatsApp/SMS/IVR content per farmer segment), Receptivity (ML score charts), Rep Briefing (field rep action lists + inventory intelligence). Design language: premium agricultural tech — warm off-white background (#f5f1e8), forest green primary (#2f7d4c), amber accent (#b8701f), Source Serif 4 for headings, Space Grotesk for UI. Dark sidebar with green gradient. Campaign hero banners as dark green full-width cards. All charts via Plotly. Constraints: Streamlit app — all UI via HTML/CSS injected via st.markdown, no React/JS. Show: campaign list sidebar, campaign overview tab, content generation tab with WhatsApp message bubble mockups, India state dot map."
