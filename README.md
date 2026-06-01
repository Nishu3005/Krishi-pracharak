# KrishiPulse AI

KrishiPulse AI is a full-stack agricultural marketing intelligence MVP built for a Syngenta-style hackathon. It helps teams turn farmer, product, region, influencer, and campaign-history data into explainable farmer segments and compliant campaign packs.

## Problem Statement

Agricultural marketing teams often have fragmented survey files, product notes, influencer lists, and campaign history. This makes it hard to choose the right farmer persona, channel, message, and field activation strategy quickly enough for seasonal windows.

## Solution Overview

KrishiPulse AI simulates an AI campaign workflow without external paid APIs. Rule-based agents ingest database context, create farmer persona segments, generate channel-specific campaign content, check compliance, and predict campaign performance.

## Website Workflow

1. Upload or manage farmer survey, product, influencer, and campaign data.
2. Open **Create Campaign**.
3. Select a mandatory product and optional region, channel, influencer, and additional info.
4. Click **Create Segments** to generate farmer personas from product, region, crop, farmer, ecosystem, outbreak, and campaign-history data.
5. Click **Generate** on a segment to create WhatsApp, SMS, voice, video, image, influencer, field rep, and retailer content.
6. Use the right-pane AI chat for contextual strategy questions.
7. Export a campaign pack with generated content, compliance notes, metrics, and agent trace.

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

## Database Schema Summary

The Prisma schema models products, crops, product-crop fit, regions, languages, farmers, farmer assets, farming practices, channel preferences, ecosystem conditions, outbreaks, retailers, influencers, campaigns, messages, targets, responses, CSV uploads, ingestion jobs, schema mappings, staging records, and data-health issues.

Campaign generation stores campaign briefs, channel scripts, influencer and field scripts, retailer nudges, visual prompts, compliance status, compliance notes, and expected metrics in `campaign_messages`.

## How To Run

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
npm run build
```

## Demo Flow

1. Go to `/campaigns/create`.
2. Click **Run Bihar Seed Campaign Demo**.
3. Review the three high-priority Bihar maize farmer segments.
4. Click **Generate** on a segment.
5. Review the campaign brief, content tabs, compliance notes, expected metrics, generic-vs-AI comparison, and agent trace.
6. Ask suggested chat questions such as “Why was this segment selected?” or “What is the expected inquiry rate?”
7. Click **Export Campaign Pack**.

## Future Production Roadmap

- Replace rule-based AI modules with configurable LLM providers.
- Add authentication, role-based permissions, and audit logs.
- Add production-grade CSV review queues and human approval workflows.
- Integrate live weather, outbreak, retailer, and sales data feeds.
- Add multilingual campaign generation and compliance review by market.
- Add experiment tracking for A/B campaign variants and closed-loop ROI learning.
