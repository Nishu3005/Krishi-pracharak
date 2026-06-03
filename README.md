# Krishi Pracharak

Krishi Pracharak is a full-stack agricultural marketing intelligence MVP built for a Syngenta-style hackathon. It helps teams turn farmer, product, region, influencer, and campaign-history data into explainable farmer segments and compliant campaign packs.

## Problem Statement

Agricultural marketing teams often have fragmented survey files, product notes, influencer lists, and campaign history. This makes it hard to choose the right farmer persona, channel, message, and field activation strategy quickly enough for seasonal windows.

## Solution Overview

Krishi Pracharak uses real AI through TokenRouter for CSV ingestion intelligence and farmer persona segmentation. TokenRouter classifies uploaded CSV files, extracts mixed entities from each row, maps columns to the approved database schema, validates rows, and generates farmer segments from product, region, crop, farmer, ecosystem, outbreak, and campaign-history context.

There is no local fallback for the required AI workflows. If TokenRouter is not configured, the CSV upload and segment generation workflows are blocked with a clear error.

## Website Workflow

1. Upload or manage farmer survey, product, influencer, and campaign data.
2. CSV uploads are staged first: `uploaded_files` → `data_ingestion_jobs` → `schema_mappings` → `staging_records` → `validation_errors`.
3. Review TokenRouter mixed-entity extraction, confidence, reasoning, column mappings, row validation, warnings, suggested fixes, and import recommendation.
4. Approve import before any staged rows are inserted into final database tables.
5. Open **Create Campaign**.
6. Select a mandatory product and optional region, channel, influencer, and additional info.
7. Click **Create Segments** to call TokenRouter and generate farmer personas. Channel and influencer are not used for segmentation.
8. Click **Generate** on a segment to create WhatsApp, SMS, voice, video, image, influencer, field rep, and retailer content.

## Tech Stack

- Next.js App Router
- TypeScript
- Tailwind CSS
- shadcn/ui-style local components
- SQLite
- Prisma
- Recharts
- PapaParse
- Zod
- TokenRouter Responses API

## Database Schema Summary

The Prisma schema models products, crops, product-crop fit, regions, languages, farmers, farmer assets, farming practices, channel preferences, ecosystem conditions, outbreaks, retailers, influencers, campaigns, messages, targets, responses, CSV uploads, ingestion jobs, schema mappings, staging records, validation errors, AI generation logs, and data-health issues.

Campaign generation stores campaign briefs, channel scripts, influencer and field scripts, retailer nudges, visual prompts, compliance status, compliance notes, and expected metrics in `campaign_messages`.

## How To Run

Create `.env.local` or update `.env`:

```bash
DATABASE_URL="file:./dev.db"
TOKENROUTER_API_KEY="your-tokenrouter-key"
TOKENROUTER_BASE_URL="https://api.tokenrouter.io/v1/responses"
OPENAI_MODEL="auto:balance"
AI_PROVIDER="tokenrouter"
AI_REQUIRE_REAL_API="true"
AI_SEND_FULL_CSV="true"
TOKENROUTER_TIMEOUT_MS="60000"
```

Optional CSV limits:

```bash
AI_MAX_CSV_BYTES="500000"
AI_MAX_CSV_ROWS="1000"
```

```bash
npm install
npx prisma migrate dev
npm run dev
```

Open:

```text
http://localhost:3000
```

Build check:

```bash
npm run lint
npm run build
```

## Real AI Workflows

- CSV type detection and mixed-entity extraction use TokenRouter.
- CSV column mapping uses TokenRouter and is schema-guarded.
- CSV validation intelligence uses TokenRouter and writes row issues to `validation_errors`.
- Farmer segment generation uses TokenRouter.

The LLM never inserts into final database tables. It only returns JSON analysis. The app stores staged normalized entities and waits for user approval before importing.

Full CSV content is sent to TokenRouter for CSV analysis. Do not upload sensitive data unless this is acceptable for your environment.

## Sample CSV Test

Use a farmer survey CSV like:

```csv
farmer name,state,district,village,crop grown,land size,mobile type,language,uses whatsapp,retailer influence
Ravi Kumar,Bihar,Begusarai,Barauni,Maize,3,Smartphone,Hindi,yes,72
Sita Devi,Bihar,Begusarai,Teghra,Maize,2,Feature phone,Hindi,no,61
```

Expected flow:

1. Upload the CSV from `/data`.
2. TokenRouter detects the type, extracts farmer + region + crop + language + channel preference entities, maps columns, validates rows, and stages records.
3. Review the mapping and validation report.
4. Approve import.
5. Confirm `regions`, `languages`, `crops`, `farmers`, and `channel_preferences` update only after approval.

## Demo Flow

1. Go to `/campaigns/create`.
2. Click **Run Bihar Seed Campaign Demo**.
3. Review the TokenRouter-generated Bihar maize farmer segments.
4. Click **Generate** on a segment.
5. Review the campaign brief, content tabs, compliance notes, expected metrics, generic-vs-AI comparison, and agent trace.
6. Ask suggested chat questions such as “Why was this segment selected?” or “What is the expected inquiry rate?”
7. Click **Export Campaign Pack**.

## Future Production Roadmap

- Add authentication, role-based permissions, and audit logs.
- Add production-grade CSV review queues and human approval workflows.
- Integrate live weather, outbreak, retailer, and sales data feeds.
- Add multilingual campaign generation and compliance review by market.
- Add experiment tracking for A/B campaign variants and closed-loop ROI learning.
