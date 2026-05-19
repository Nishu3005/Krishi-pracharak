# KrishiPulse AI — Database Table Schema

## Purpose

This schema is designed for an AI-powered agricultural marketing system that can decide:

> **Which product** should be marketed to **which farmer**, in **which region**, for **which crop**, under **which ecosystem/outbreak condition**, through **which channel**, at **which moment**.

The schema supports:

- Hyperlocal farmer targeting
- Product-to-crop recommendation
- Outbreak-triggered campaigns
- Vernacular campaign generation
- Channel optimization
- Field representative action planning
- Campaign response tracking and learning loop

---

# 1. Core Entity Relationship Overview

## Main entities

| Entity | Purpose |
|---|---|
| `products` | Stores crop protection products, seeds, and biological products |
| `crops` | Stores crop master data and growth-stage information |
| `regions` | Stores geography from country to village level |
| `ecosystem_conditions` | Stores time-varying weather, soil, and irrigation data |
| `outbreaks` | Stores pest, disease, and weed outbreak information |
| `farmers` | Stores farmer profile and segmentation data |
| `languages` | Stores preferred communication languages |
| `farming_practices` | Stores farmer cultivation behavior and method of farming |
| `farmer_assets` | Stores farmer tools, equipment, and assets |
| `product_crop_fit` | Maps products to relevant crops, crop stages, and threats |
| `channel_preferences` | Stores farmer communication and trust-channel behavior |
| `campaigns` | Stores marketing campaign metadata |
| `campaign_messages` | Stores generated campaign content variants |
| `campaign_targets` | Stores farmer-level campaign targeting decisions |
| `campaign_responses` | Stores delivery, engagement, inquiry, and purchase response |
| `retailers` | Stores retailer network and influence information |
| `influencers` | Stores trusted local/agri influencers who can amplify campaigns |
| `influencer_campaigns` | Maps influencers to campaigns and tracks planned influencer activation |
| `influencer_performance` | Stores influencer-level reach, engagement, inquiry, and conversion performance |

---

# 2. Recommended MVP Tables

For a hackathon MVP, use these first:

1. `products`
2. `crops`
3. `regions`
4. `farmers`
5. `ecosystem_conditions`
6. `outbreaks`
7. `farming_practices`
8. `channel_preferences`
9. `product_crop_fit`
10. `campaigns`
11. `campaign_targets`
12. `campaign_responses`

For a stronger production version, add:

- `languages`
- `farmer_assets`
- `campaign_messages`
- `retailers`
- `influencers`
- `influencer_campaigns`
- `influencer_performance`

---

# 3. Table Schemas

---

## 3.1 `products`

Stores product master information.

| Column | Type | Key | Description |
|---|---|---|---|
| `product_id` | SERIAL / INT | PK | Unique product ID |
| `product_name` | VARCHAR(150) |  | Product name |
| `product_category` | VARCHAR(50) |  | Insecticide, fungicide, herbicide, seed, biological, etc. |
| `product_type` | VARCHAR(50) |  | Chemical, organic, biological, hybrid seed, etc. |
| `sustainable_flag` | BOOLEAN |  | Whether product is positioned as sustainable |
| `organic_flag` | BOOLEAN |  | Whether product can be used in organic context |
| `price_per_unit` | DECIMAL(10,2) |  | Product price per unit |
| `unit_type` | VARCHAR(30) |  | Kg, litre, packet, ml, etc. |
| `active_ingredient` | VARCHAR(150) |  | Active ingredient, if applicable |
| `target_pest_type` | VARCHAR(100) |  | Insect, fungus, weed, nematode, multi-threat, etc. |
| `crop_stage_relevance` | VARCHAR(100) |  | Sowing, vegetative, flowering, fruiting, harvest, etc. |
| `description` | TEXT |  | Short product description |
| `status` | VARCHAR(20) |  | Active, inactive, discontinued |

### CMO note

Product marketing should not be based only on price. It should also depend on:

- Crop fit
- Crop stage fit
- Threat fit
- Regional relevance
- Farmer affordability
- Sustainability positioning

---

## 3.2 `crops`

Stores crop master information.

| Column | Type | Key | Description |
|---|---|---|---|
| `crop_id` | SERIAL / INT | PK | Unique crop ID |
| `crop_name` | VARCHAR(100) |  | Rice, cotton, wheat, chilli, maize, etc. |
| `crop_category` | VARCHAR(50) |  | Cereal, cash crop, vegetable, pulse, oilseed, etc. |
| `season` | VARCHAR(20) |  | Kharif, Rabi, Zaid, perennial |
| `average_duration_days` | INT |  | Typical crop duration in days |
| `typical_growth_stages` | TEXT |  | Sowing, tillering, vegetative, flowering, fruiting, harvest |

---

## 3.3 `regions`

Stores geography and location information.

| Column | Type | Key | Description |
|---|---|---|---|
| `region_id` | SERIAL / INT | PK | Unique region ID |
| `country` | VARCHAR(100) |  | Country name |
| `state` | VARCHAR(100) |  | State name |
| `district` | VARCHAR(100) |  | District name |
| `block_taluk` | VARCHAR(100) |  | Block, taluk, mandal, or tehsil |
| `village` | VARCHAR(100) |  | Village name |
| `latitude` | DECIMAL(10,6) |  | Latitude |
| `longitude` | DECIMAL(10,6) |  | Longitude |
| `agro_climatic_zone` | VARCHAR(100) |  | Agro-climatic classification |

### CMO note

Agriculture marketing is hyperlocal. A campaign relevant in one district may be irrelevant in another. This table supports village-level precision.

---

## 3.4 `languages`

Stores language preferences.

| Column | Type | Key | Description |
|---|---|---|---|
| `language_id` | SERIAL / INT | PK | Unique language ID |
| `language_name` | VARCHAR(50) |  | Tamil, Hindi, Marathi, Telugu, Kannada, etc. |
| `script_type` | VARCHAR(50) |  | Native script, Romanized, both |
| `rtl_flag` | BOOLEAN |  | Right-to-left script flag, useful for future expansion |

---

## 3.5 `farmers`

Stores farmer profile information.

| Column | Type | Key | Description |
|---|---|---|---|
| `farmer_id` | SERIAL / INT | PK | Unique farmer ID |
| `farmer_name` | VARCHAR(150) |  | Farmer name |
| `region_id` | INT | FK → `regions.region_id` | Farmer location |
| `primary_crop_id` | INT | FK → `crops.crop_id` | Main crop cultivated |
| `land_size_acres` | DECIMAL(8,2) |  | Farm size in acres |
| `annual_income_band` | VARCHAR(30) |  | Low, medium, high, premium, etc. |
| `literacy_level` | VARCHAR(30) |  | Low, moderate, high |
| `smartphone_user` | BOOLEAN |  | Whether farmer uses smartphone |
| `feature_phone_user` | BOOLEAN |  | Whether farmer uses feature phone |
| `preferred_language_id` | INT | FK → `languages.language_id` | Preferred language |
| `gender` | VARCHAR(20) |  | Optional demographic field |
| `age_band` | VARCHAR(30) |  | Example: 18–30, 31–45, 46–60, 60+ |
| `farmer_segment` | VARCHAR(50) |  | Smallholder, progressive, commercial, price-sensitive, etc. |
| `trust_channel` | VARCHAR(50) |  | Retailer, field rep, WhatsApp, voice call, community leader |
| `created_at` | TIMESTAMP |  | Record creation timestamp |

### CMO note

The farmer table should help answer:

- Who is the farmer?
- What does the farmer grow?
- What is the farmer's communication comfort?
- Who does the farmer trust?
- What is the farmer's likely purchase behavior?

---

## 3.6 `ecosystem_conditions`

Stores dynamic weather, soil, and irrigation conditions by region and date.

| Column | Type | Key | Description |
|---|---|---|---|
| `ecosystem_id` | SERIAL / INT | PK | Unique ecosystem record ID |
| `region_id` | INT | FK → `regions.region_id` | Region where data is observed |
| `observation_date` | DATE |  | Date of observation |
| `temperature_avg` | DECIMAL(5,2) |  | Average temperature |
| `rainfall_mm` | DECIMAL(8,2) |  | Rainfall in mm |
| `humidity_percent` | DECIMAL(5,2) |  | Humidity percentage |
| `soil_type` | VARCHAR(50) |  | Sandy, loamy, clay, black soil, red soil, etc. |
| `soil_ph` | DECIMAL(4,2) |  | Soil pH |
| `soil_moisture` | DECIMAL(5,2) |  | Soil moisture score or percentage |
| `irrigation_type` | VARCHAR(50) |  | Rainfed, canal, borewell, drip, sprinkler |
| `weather_summary` | VARCHAR(50) |  | Hot, humid, dry, wet, cloudy, windy, etc. |
| `risk_level` | VARCHAR(20) |  | Low, medium, high |

### CMO note

Do not store weather directly in the `regions` table. Weather changes daily or weekly, so it needs its own time-series table.

---

## 3.7 `outbreaks`

Stores pest, disease, and weed threat information.

| Column | Type | Key | Description |
|---|---|---|---|
| `outbreak_id` | SERIAL / INT | PK | Unique outbreak ID |
| `region_id` | INT | FK → `regions.region_id` | Affected region |
| `crop_id` | INT | FK → `crops.crop_id` | Affected crop |
| `outbreak_type` | VARCHAR(50) |  | Pest, disease, weed, nutrient issue |
| `outbreak_name` | VARCHAR(100) |  | Aphids, stem borer, blast, blight, etc. |
| `severity` | VARCHAR(20) |  | Low, medium, high, severe |
| `detected_date` | DATE |  | Date of detection |
| `source` | VARCHAR(100) |  | Field survey, government report, internal report, satellite inference |
| `symptoms` | TEXT |  | Farmer-readable symptom description |
| `recommendation_window_days` | INT |  | Number of days within which action is recommended |
| `active_flag` | BOOLEAN |  | Whether outbreak is currently active |

### CMO note

This table powers **moment-based marketing**. Campaigns should be triggered when risk is real, not randomly.

---

## 3.8 `farming_practices`

Stores the farmer's cultivation method and behavior.

| Column | Type | Key | Description |
|---|---|---|---|
| `practice_id` | SERIAL / INT | PK | Unique practice ID |
| `farmer_id` | INT | FK → `farmers.farmer_id` | Farmer |
| `crop_id` | INT | FK → `crops.crop_id` | Crop |
| `farming_type` | VARCHAR(50) |  | Traditional, organic, precision, mixed, contract farming |
| `sowing_period` | VARCHAR(50) |  | Early, normal, late |
| `irrigation_method` | VARCHAR(50) |  | Drip, flood, rainfed, sprinkler |
| `mechanization_level` | VARCHAR(20) |  | Low, medium, high |
| `fertilizer_practice` | VARCHAR(50) |  | Organic, chemical, mixed |
| `pesticide_practice` | VARCHAR(50) |  | Regular, need-based, organic-only, preventive |
| `labor_dependency` | VARCHAR(50) |  | Family, hired, mixed |
| `cultivation_frequency` | VARCHAR(50) |  | Seasonal, multi-season, annual |

---

## 3.9 `farmer_assets`

Stores tools and assets available to the farmer.

| Column | Type | Key | Description |
|---|---|---|---|
| `asset_id` | SERIAL / INT | PK | Unique asset ID |
| `farmer_id` | INT | FK → `farmers.farmer_id` | Farmer |
| `asset_type` | VARCHAR(50) |  | Tractor, sprayer, pump, drip system, harvester, storage unit |
| `asset_name` | VARCHAR(100) |  | Specific asset name |
| `ownership_type` | VARCHAR(50) |  | Owned, rented, shared, cooperative |
| `quantity` | INT |  | Number of assets |
| `usable_flag` | BOOLEAN |  | Whether asset is usable |

---

## 3.10 `product_crop_fit`

Maps product relevance to crop, outbreak, and crop stage.

| Column | Type | Key | Description |
|---|---|---|---|
| `fit_id` | SERIAL / INT | PK | Unique fit ID |
| `product_id` | INT | FK → `products.product_id` | Product |
| `crop_id` | INT | FK → `crops.crop_id` | Crop |
| `outbreak_type` | VARCHAR(50) |  | Pest, disease, weed, nutrient issue |
| `outbreak_name` | VARCHAR(100) |  | Specific threat name |
| `recommended_stage` | VARCHAR(50) |  | Recommended crop stage |
| `relevance_score` | DECIMAL(5,2) |  | Product relevance score from 0 to 100 |
| `approved_flag` | BOOLEAN |  | Whether mapping is approved by agronomy/business team |

### CMO note

This is one of the most important tables. It prevents random product promotion and ensures that campaigns are contextually relevant.

---

## 3.11 `channel_preferences`

Stores communication and engagement behavior.

| Column | Type | Key | Description |
|---|---|---|---|
| `preference_id` | SERIAL / INT | PK | Unique preference ID |
| `farmer_id` | INT | FK → `farmers.farmer_id` | Farmer |
| `whatsapp_opt_in` | BOOLEAN |  | Whether WhatsApp communication is allowed |
| `sms_opt_in` | BOOLEAN |  | Whether SMS communication is allowed |
| `voice_call_opt_in` | BOOLEAN |  | Whether voice/IVR communication is allowed |
| `retailer_influence_score` | DECIMAL(5,2) |  | Retailer influence score from 0 to 100 |
| `field_rep_influence_score` | DECIMAL(5,2) |  | Field representative influence score from 0 to 100 |
| `preferred_contact_time` | VARCHAR(30) |  | Morning, afternoon, evening |
| `engagement_score` | DECIMAL(5,2) |  | Historical engagement score from 0 to 100 |
| `last_contacted_at` | TIMESTAMP |  | Last campaign contact timestamp |

### CMO note

This table enables channel personalization:

- Low literacy + feature phone → voice/IVR
- Smartphone + high engagement → WhatsApp
- Retailer-trusting farmer → retailer nudge
- High urgency + high value → field rep visit

---

## 3.12 `campaigns`

Stores campaign-level metadata.

| Column | Type | Key | Description |
|---|---|---|---|
| `campaign_id` | SERIAL / INT | PK | Unique campaign ID |
| `campaign_name` | VARCHAR(150) |  | Campaign title |
| `product_id` | INT | FK → `products.product_id` | Product promoted |
| `crop_id` | INT | FK → `crops.crop_id` | Crop focus |
| `region_id` | INT | FK → `regions.region_id` | Target region |
| `outbreak_id` | INT | FK → `outbreaks.outbreak_id` | Triggering outbreak, if any |
| `language_id` | INT | FK → `languages.language_id` | Campaign language |
| `channel` | VARCHAR(50) |  | WhatsApp, SMS, voice, retailer, field rep |
| `message_type` | VARCHAR(50) |  | Advisory, alert, promotion, reminder, education |
| `campaign_goal` | VARCHAR(50) |  | Awareness, inquiry, purchase, field visit |
| `launch_date` | DATE |  | Campaign launch date |
| `end_date` | DATE |  | Campaign end date |
| `created_by` | VARCHAR(100) |  | Creator or system name |
| `status` | VARCHAR(30) |  | Draft, approved, live, paused, closed |

---

## 3.13 `campaign_messages`

Stores content variants generated for campaigns.

| Column | Type | Key | Description |
|---|---|---|---|
| `message_id` | SERIAL / INT | PK | Unique message ID |
| `campaign_id` | INT | FK → `campaigns.campaign_id` | Campaign |
| `message_variant` | VARCHAR(20) |  | A, B, C, test variant, etc. |
| `whatsapp_text` | TEXT |  | WhatsApp message |
| `sms_text` | TEXT |  | SMS message |
| `voice_script` | TEXT |  | IVR or voice-call script |
| `field_rep_script` | TEXT |  | Field representative talking points |
| `retailer_script` | TEXT |  | Retailer-facing message |
| `visual_prompt` | TEXT |  | Visual concept or AI image prompt |
| `compliance_approved` | BOOLEAN |  | Whether content is approved |

### CMO note

This table separates campaign strategy from actual content. It supports A/B testing and multilingual adaptation.

---

## 3.14 `campaign_targets`

Stores who receives a campaign and why.

| Column | Type | Key | Description |
|---|---|---|---|
| `target_id` | SERIAL / INT | PK | Unique target ID |
| `campaign_id` | INT | FK → `campaigns.campaign_id` | Campaign |
| `farmer_id` | INT | FK → `farmers.farmer_id` | Target farmer |
| `recommended_channel` | VARCHAR(50) |  | Best channel for this farmer |
| `priority_score` | DECIMAL(8,2) |  | Overall priority score |
| `predicted_engagement_probability` | DECIMAL(5,2) |  | Expected engagement probability |
| `predicted_inquiry_probability` | DECIMAL(5,2) |  | Expected inquiry probability |
| `recommended_send_time` | VARCHAR(30) |  | Best time to send |
| `status` | VARCHAR(30) |  | Pending, sent, delivered, responded, skipped |

---

## 3.15 `campaign_responses`

Stores feedback and campaign performance.

| Column | Type | Key | Description |
|---|---|---|---|
| `response_id` | SERIAL / INT | PK | Unique response ID |
| `target_id` | INT | FK → `campaign_targets.target_id` | Campaign target |
| `delivery_status` | VARCHAR(30) |  | Delivered, failed, pending |
| `opened_flag` | BOOLEAN |  | Whether farmer opened or listened |
| `clicked_flag` | BOOLEAN |  | Whether farmer clicked a link |
| `replied_flag` | BOOLEAN |  | Whether farmer replied |
| `inquiry_flag` | BOOLEAN |  | Whether farmer made an inquiry |
| `purchase_flag` | BOOLEAN |  | Whether purchase was recorded |
| `response_date` | TIMESTAMP |  | Response date and time |
| `notes` | TEXT |  | Field/sales remarks |

### CMO note

This is the learning-loop table. It helps the system improve future targeting and message selection.

---

## 3.16 `retailers`

Stores retailer and dealer network information.

| Column | Type | Key | Description |
|---|---|---|---|
| `retailer_id` | SERIAL / INT | PK | Unique retailer ID |
| `retailer_name` | VARCHAR(150) |  | Retailer or shop name |
| `region_id` | INT | FK → `regions.region_id` | Retailer location |
| `contact_person` | VARCHAR(150) |  | Contact person |
| `phone` | VARCHAR(30) |  | Phone number |
| `major_crops_served` | VARCHAR(200) |  | Major crops in retailer catchment |
| `key_products_stocked` | TEXT |  | Important products stocked |
| `influence_score` | DECIMAL(5,2) |  | Influence score from 0 to 100 |

### CMO note

Retailers are a major trust and conversion channel in agriculture. Many farmers act after retailer confirmation, not just after digital campaigns.

---

## 3.17 `influencers`

Stores trusted local and digital influencers who can amplify agricultural campaigns.

In agriculture, an influencer does not only mean a social-media creator. It can also be a progressive farmer, FPO leader, agri YouTuber, village champion, WhatsApp group admin, local agronomist, or respected retailer-linked advisor.

| Column | Type | Key | Description |
|---|---|---|---|
| `influencer_id` | SERIAL / INT | PK | Unique influencer ID |
| `influencer_name` | VARCHAR(150) |  | Influencer name |
| `influencer_type` | VARCHAR(80) |  | Progressive farmer, agri creator, FPO leader, agronomist, retailer champion, WhatsApp group admin, village leader |
| `region_id` | INT | FK → `regions.region_id` | Primary influence region |
| `primary_language_id` | INT | FK → `languages.language_id` | Main communication language |
| `primary_crop_focus` | VARCHAR(150) |  | Crops where influencer has credibility |
| `platform` | VARCHAR(80) |  | WhatsApp, YouTube, Instagram, Facebook, village meeting, retailer network, FPO network |
| `follower_count` | INT |  | Digital follower count, if available |
| `estimated_farmer_reach` | INT |  | Estimated number of farmers reachable |
| `trust_score` | DECIMAL(5,2) |  | Trust score from 0 to 100 |
| `engagement_rate` | DECIMAL(5,2) |  | Historical engagement rate |
| `content_strength` | VARCHAR(100) |  | Voice, video, field demo, testimonial, WhatsApp forwarding, village meeting |
| `contact_phone` | VARCHAR(30) |  | Contact number |
| `contact_email` | VARCHAR(150) |  | Email, if available |
| `commercial_terms` | VARCHAR(100) |  | Paid, unpaid, commission, community partner, field demo honorarium |
| `compliance_status` | VARCHAR(50) |  | Pending, approved, restricted, blocked |
| `status` | VARCHAR(30) |  | Active, inactive, under review |

### CMO note

This table helps the system identify who can create trust locally. For smallholder marketing, influence often comes from community credibility rather than celebrity reach.

---

## 3.18 `influencer_campaigns`

Maps influencers to specific campaigns and planned activation tasks.

| Column | Type | Key | Description |
|---|---|---|---|
| `influencer_campaign_id` | SERIAL / INT | PK | Unique influencer-campaign mapping ID |
| `campaign_id` | INT | FK → `campaigns.campaign_id` | Linked campaign |
| `influencer_id` | INT | FK → `influencers.influencer_id` | Linked influencer |
| `activation_role` | VARCHAR(80) |  | Awareness, testimonial, demo, reminder, retailer pull, field-event support |
| `content_format` | VARCHAR(80) |  | Short video, voice note, WhatsApp forward, field demo, live session, poster |
| `planned_publish_date` | DATE |  | Planned activation date |
| `expected_reach` | INT |  | Expected farmer reach |
| `budget_allocated` | DECIMAL(10,2) |  | Planned spend or honorarium |
| `approval_status` | VARCHAR(50) |  | Draft, pending approval, approved, rejected, completed |
| `tracking_code` | VARCHAR(100) |  | Code/link/coupon/UTM to attribute response |
| `notes` | TEXT |  | Campaign-specific remarks |

### CMO note

This table makes influencer marketing measurable. It connects influencer activity with actual campaign goals such as inquiry, retailer visit, or purchase.

---

## 3.19 `influencer_performance`

Stores performance results from influencer-led campaign activations.

| Column | Type | Key | Description |
|---|---|---|---|
| `performance_id` | SERIAL / INT | PK | Unique performance ID |
| `influencer_campaign_id` | INT | FK → `influencer_campaigns.influencer_campaign_id` | Linked influencer activation |
| `actual_reach` | INT |  | Number of farmers reached |
| `views_or_listens` | INT |  | Views/listens for video or voice content |
| `shares` | INT |  | Number of shares/forwards |
| `replies` | INT |  | Farmer replies/comments/messages |
| `inquiries_generated` | INT |  | Product or advisory inquiries generated |
| `retailer_visits_attributed` | INT |  | Retailer visits linked to influencer activity |
| `purchases_attributed` | INT |  | Purchases attributed to this activation |
| `cost_per_inquiry` | DECIMAL(10,2) |  | Cost divided by inquiries generated |
| `conversion_rate` | DECIMAL(5,2) |  | Inquiry or purchase conversion rate |
| `performance_notes` | TEXT |  | Qualitative remarks |

### CMO note

This is important for proving whether influencer trust actually converts into farmer action. It also helps decide which influencers should be reused in future campaigns.

---

# 4. Relationships

## Relationship summary

| Relationship | Meaning |
|---|---|
| `regions` 1 → many `farmers` | One region can have many farmers |
| `regions` 1 → many `ecosystem_conditions` | One region has many weather/soil observations |
| `regions` 1 → many `outbreaks` | One region may have multiple outbreaks |
| `crops` 1 → many `farmers` | Many farmers can grow the same crop |
| `crops` 1 → many `outbreaks` | One crop can face many threats |
| `farmers` 1 → many `farming_practices` | One farmer may use different practices for different crops |
| `farmers` 1 → many `farmer_assets` | One farmer may own or rent many assets |
| `farmers` 1 → many `channel_preferences` | Communication behavior can be tracked over time |
| `products` many ↔ many `crops` | Managed through `product_crop_fit` |
| `campaigns` many → one `product` | A campaign usually promotes one product |
| `campaigns` many → one `crop` | A campaign targets one crop context |
| `campaigns` many → one `region` | A campaign may be region-specific |
| `campaign_targets` many → one `campaign` | One campaign targets many farmers |
| `campaign_targets` many → one `farmer` | One farmer can receive many campaigns |
| `campaign_responses` 1 → one `campaign_target` | Each response belongs to one target instance |
| `regions` 1 → many `influencers` | One region may have many local influencers |
| `languages` 1 → many `influencers` | One language may be used by many influencers |
| `influencers` many ↔ many `campaigns` | Managed through `influencer_campaigns` |
| `influencer_campaigns` 1 → many `influencer_performance` | One influencer activation can have performance records |

---

# 5. Priority Scoring Logic

## Recommended scoring formula

```text
Priority Score =
(Pest Risk Score × 0.30) +
(Crop Stage Relevance Score × 0.20) +
(Product Fit Score × 0.20) +
(Channel Receptivity Score × 0.15) +
(Urgency Score × 0.15)
```

## Score meanings

| Score | Meaning |
|---|---|
| Pest Risk Score | How serious the pest/disease/weed threat is |
| Crop Stage Relevance Score | Whether the farmer's crop is currently at a relevant growth stage |
| Product Fit Score | Whether the product is suitable for this crop and threat |
| Channel Receptivity Score | Whether the farmer is likely to engage through the chosen channel |
| Urgency Score | How quickly action must happen |

---

# 6. Channel Recommendation Rules

| Farmer situation | Recommended channel |
|---|---|
| Low literacy + feature phone | Voice call / IVR |
| Smartphone + high WhatsApp engagement | WhatsApp image or voice note |
| High retailer trust | Retailer nudge |
| High urgency + larger acreage | Field representative visit |
| Low engagement history | SMS + missed-call callback |
| High-value farmer + active outbreak | Field rep + WhatsApp follow-up |
| Community-trust driven village | Local influencer or progressive farmer testimonial |
| Low brand trust but strong peer influence | Influencer demo + retailer nudge |

---

# 7. Example Use Case

## Scenario

- Region: Tamil Nadu
- Crop: Rice
- Stage: Tillering
- Weather: High humidity + rainfall
- Threat: Fungal disease risk
- Farmer language: Tamil
- Farmer literacy: Low to moderate
- Smartphone access: Yes

## System decision

1. Detect high disease risk using `ecosystem_conditions` and `outbreaks`.
2. Match suitable products using `product_crop_fit`.
3. Select farmers using `farmers`, `regions`, and `farming_practices`.
4. Choose WhatsApp voice + field rep follow-up using `channel_preferences`.
5. Generate Tamil campaign content using `campaign_messages`.
6. Store targeting decision in `campaign_targets`.
7. Track inquiry/purchase using `campaign_responses`.

---

# 8. PostgreSQL Starter Schema

```sql
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(150) NOT NULL,
    product_category VARCHAR(50),
    product_type VARCHAR(50),
    sustainable_flag BOOLEAN DEFAULT FALSE,
    organic_flag BOOLEAN DEFAULT FALSE,
    price_per_unit DECIMAL(10,2),
    unit_type VARCHAR(30),
    active_ingredient VARCHAR(150),
    target_pest_type VARCHAR(100),
    crop_stage_relevance VARCHAR(100),
    description TEXT,
    status VARCHAR(20) DEFAULT 'Active'
);

CREATE TABLE crops (
    crop_id SERIAL PRIMARY KEY,
    crop_name VARCHAR(100) NOT NULL,
    crop_category VARCHAR(50),
    season VARCHAR(20),
    average_duration_days INT,
    typical_growth_stages TEXT
);

CREATE TABLE regions (
    region_id SERIAL PRIMARY KEY,
    country VARCHAR(100),
    state VARCHAR(100),
    district VARCHAR(100),
    block_taluk VARCHAR(100),
    village VARCHAR(100),
    latitude DECIMAL(10,6),
    longitude DECIMAL(10,6),
    agro_climatic_zone VARCHAR(100)
);

CREATE TABLE languages (
    language_id SERIAL PRIMARY KEY,
    language_name VARCHAR(50) NOT NULL,
    script_type VARCHAR(50),
    rtl_flag BOOLEAN DEFAULT FALSE
);

CREATE TABLE farmers (
    farmer_id SERIAL PRIMARY KEY,
    farmer_name VARCHAR(150),
    region_id INT REFERENCES regions(region_id),
    primary_crop_id INT REFERENCES crops(crop_id),
    land_size_acres DECIMAL(8,2),
    annual_income_band VARCHAR(30),
    literacy_level VARCHAR(30),
    smartphone_user BOOLEAN DEFAULT FALSE,
    feature_phone_user BOOLEAN DEFAULT TRUE,
    preferred_language_id INT REFERENCES languages(language_id),
    gender VARCHAR(20),
    age_band VARCHAR(30),
    farmer_segment VARCHAR(50),
    trust_channel VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ecosystem_conditions (
    ecosystem_id SERIAL PRIMARY KEY,
    region_id INT REFERENCES regions(region_id),
    observation_date DATE NOT NULL,
    temperature_avg DECIMAL(5,2),
    rainfall_mm DECIMAL(8,2),
    humidity_percent DECIMAL(5,2),
    soil_type VARCHAR(50),
    soil_ph DECIMAL(4,2),
    soil_moisture DECIMAL(5,2),
    irrigation_type VARCHAR(50),
    weather_summary VARCHAR(50),
    risk_level VARCHAR(20)
);

CREATE TABLE outbreaks (
    outbreak_id SERIAL PRIMARY KEY,
    region_id INT REFERENCES regions(region_id),
    crop_id INT REFERENCES crops(crop_id),
    outbreak_type VARCHAR(50),
    outbreak_name VARCHAR(100),
    severity VARCHAR(20),
    detected_date DATE,
    source VARCHAR(100),
    symptoms TEXT,
    recommendation_window_days INT,
    active_flag BOOLEAN DEFAULT TRUE
);

CREATE TABLE farming_practices (
    practice_id SERIAL PRIMARY KEY,
    farmer_id INT REFERENCES farmers(farmer_id),
    crop_id INT REFERENCES crops(crop_id),
    farming_type VARCHAR(50),
    sowing_period VARCHAR(50),
    irrigation_method VARCHAR(50),
    mechanization_level VARCHAR(20),
    fertilizer_practice VARCHAR(50),
    pesticide_practice VARCHAR(50),
    labor_dependency VARCHAR(50),
    cultivation_frequency VARCHAR(50)
);

CREATE TABLE farmer_assets (
    asset_id SERIAL PRIMARY KEY,
    farmer_id INT REFERENCES farmers(farmer_id),
    asset_type VARCHAR(50),
    asset_name VARCHAR(100),
    ownership_type VARCHAR(50),
    quantity INT,
    usable_flag BOOLEAN DEFAULT TRUE
);

CREATE TABLE product_crop_fit (
    fit_id SERIAL PRIMARY KEY,
    product_id INT REFERENCES products(product_id),
    crop_id INT REFERENCES crops(crop_id),
    outbreak_type VARCHAR(50),
    outbreak_name VARCHAR(100),
    recommended_stage VARCHAR(50),
    relevance_score DECIMAL(5,2),
    approved_flag BOOLEAN DEFAULT TRUE
);

CREATE TABLE channel_preferences (
    preference_id SERIAL PRIMARY KEY,
    farmer_id INT REFERENCES farmers(farmer_id),
    whatsapp_opt_in BOOLEAN DEFAULT FALSE,
    sms_opt_in BOOLEAN DEFAULT TRUE,
    voice_call_opt_in BOOLEAN DEFAULT TRUE,
    retailer_influence_score DECIMAL(5,2),
    field_rep_influence_score DECIMAL(5,2),
    preferred_contact_time VARCHAR(30),
    engagement_score DECIMAL(5,2),
    last_contacted_at TIMESTAMP
);

CREATE TABLE campaigns (
    campaign_id SERIAL PRIMARY KEY,
    campaign_name VARCHAR(150),
    product_id INT REFERENCES products(product_id),
    crop_id INT REFERENCES crops(crop_id),
    region_id INT REFERENCES regions(region_id),
    outbreak_id INT REFERENCES outbreaks(outbreak_id),
    language_id INT REFERENCES languages(language_id),
    channel VARCHAR(50),
    message_type VARCHAR(50),
    campaign_goal VARCHAR(50),
    launch_date DATE,
    end_date DATE,
    created_by VARCHAR(100),
    status VARCHAR(30)
);

CREATE TABLE campaign_messages (
    message_id SERIAL PRIMARY KEY,
    campaign_id INT REFERENCES campaigns(campaign_id),
    message_variant VARCHAR(20),
    whatsapp_text TEXT,
    sms_text TEXT,
    voice_script TEXT,
    field_rep_script TEXT,
    retailer_script TEXT,
    visual_prompt TEXT,
    compliance_approved BOOLEAN DEFAULT FALSE
);

CREATE TABLE campaign_targets (
    target_id SERIAL PRIMARY KEY,
    campaign_id INT REFERENCES campaigns(campaign_id),
    farmer_id INT REFERENCES farmers(farmer_id),
    recommended_channel VARCHAR(50),
    priority_score DECIMAL(8,2),
    predicted_engagement_probability DECIMAL(5,2),
    predicted_inquiry_probability DECIMAL(5,2),
    recommended_send_time VARCHAR(30),
    status VARCHAR(30)
);

CREATE TABLE campaign_responses (
    response_id SERIAL PRIMARY KEY,
    target_id INT REFERENCES campaign_targets(target_id),
    delivery_status VARCHAR(30),
    opened_flag BOOLEAN DEFAULT FALSE,
    clicked_flag BOOLEAN DEFAULT FALSE,
    replied_flag BOOLEAN DEFAULT FALSE,
    inquiry_flag BOOLEAN DEFAULT FALSE,
    purchase_flag BOOLEAN DEFAULT FALSE,
    response_date TIMESTAMP,
    notes TEXT
);

CREATE TABLE retailers (
    retailer_id SERIAL PRIMARY KEY,
    retailer_name VARCHAR(150),
    region_id INT REFERENCES regions(region_id),
    contact_person VARCHAR(150),
    phone VARCHAR(30),
    major_crops_served VARCHAR(200),
    key_products_stocked TEXT,
    influence_score DECIMAL(5,2)
);

CREATE TABLE influencers (
    influencer_id SERIAL PRIMARY KEY,
    influencer_name VARCHAR(150),
    influencer_type VARCHAR(80),
    region_id INT REFERENCES regions(region_id),
    primary_language_id INT REFERENCES languages(language_id),
    primary_crop_focus VARCHAR(150),
    platform VARCHAR(80),
    follower_count INT,
    estimated_farmer_reach INT,
    trust_score DECIMAL(5,2),
    engagement_rate DECIMAL(5,2),
    content_strength VARCHAR(100),
    contact_phone VARCHAR(30),
    contact_email VARCHAR(150),
    commercial_terms VARCHAR(100),
    compliance_status VARCHAR(50),
    status VARCHAR(30) DEFAULT 'Active'
);

CREATE TABLE influencer_campaigns (
    influencer_campaign_id SERIAL PRIMARY KEY,
    campaign_id INT REFERENCES campaigns(campaign_id),
    influencer_id INT REFERENCES influencers(influencer_id),
    activation_role VARCHAR(80),
    content_format VARCHAR(80),
    planned_publish_date DATE,
    expected_reach INT,
    budget_allocated DECIMAL(10,2),
    approval_status VARCHAR(50),
    tracking_code VARCHAR(100),
    notes TEXT
);

CREATE TABLE influencer_performance (
    performance_id SERIAL PRIMARY KEY,
    influencer_campaign_id INT REFERENCES influencer_campaigns(influencer_campaign_id),
    actual_reach INT,
    views_or_listens INT,
    shares INT,
    replies INT,
    inquiries_generated INT,
    retailer_visits_attributed INT,
    purchases_attributed INT,
    cost_per_inquiry DECIMAL(10,2),
    conversion_rate DECIMAL(5,2),
    performance_notes TEXT
);
```

---

# 9. Codex Instruction

Use this schema as the database and data-model foundation for the KrishiPulse AI app.

For the MVP, synthetic CSV files can be created for:

```text
products.csv
crops.csv
regions.csv
farmers.csv
ecosystem_conditions.csv
outbreaks.csv
farming_practices.csv
channel_preferences.csv
product_crop_fit.csv
campaigns.csv
campaign_targets.csv
campaign_responses.csv
influencers.csv
influencer_campaigns.csv
influencer_performance.csv
```

The Streamlit app should read these CSVs and simulate:

- Farmer segmentation
- Outbreak-based targeting
- Product-crop matching
- Channel recommendation
- Campaign content generation
- Campaign response prediction
- Field representative daily action plan
- Influencer-based campaign amplification
- Influencer reach, inquiry, and conversion tracking
