-- CreateTable
CREATE TABLE "products" (
    "product_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "product_name" TEXT NOT NULL,
    "product_category" TEXT NOT NULL,
    "product_type" TEXT,
    "sustainable_flag" BOOLEAN NOT NULL DEFAULT false,
    "organic_flag" BOOLEAN NOT NULL DEFAULT false,
    "price_per_unit" DECIMAL,
    "unit_type" TEXT,
    "active_ingredient" TEXT,
    "target_pest_type" TEXT,
    "crop_stage_relevance" TEXT,
    "description" TEXT,
    "status" TEXT NOT NULL DEFAULT 'active'
);

-- CreateTable
CREATE TABLE "crops" (
    "crop_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "crop_name" TEXT NOT NULL,
    "crop_category" TEXT,
    "season" TEXT,
    "average_duration_days" INTEGER,
    "typical_growth_stages" TEXT
);

-- CreateTable
CREATE TABLE "regions" (
    "region_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "country" TEXT NOT NULL DEFAULT 'India',
    "state" TEXT NOT NULL,
    "district" TEXT,
    "block_taluk" TEXT,
    "village" TEXT,
    "latitude" DECIMAL,
    "longitude" DECIMAL,
    "agro_climatic_zone" TEXT
);

-- CreateTable
CREATE TABLE "languages" (
    "language_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "language_name" TEXT NOT NULL,
    "script_type" TEXT,
    "rtl_flag" BOOLEAN NOT NULL DEFAULT false
);

-- CreateTable
CREATE TABLE "farmers" (
    "farmer_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "farmer_name" TEXT,
    "region_id" INTEGER NOT NULL,
    "primary_crop_id" INTEGER,
    "land_size_acres" DECIMAL,
    "annual_income_band" TEXT,
    "literacy_level" TEXT,
    "smartphone_user" BOOLEAN NOT NULL DEFAULT false,
    "feature_phone_user" BOOLEAN NOT NULL DEFAULT false,
    "preferred_language_id" INTEGER,
    "gender" TEXT,
    "age_band" TEXT,
    "farmer_segment" TEXT,
    "trust_channel" TEXT,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "farmers_region_id_fkey" FOREIGN KEY ("region_id") REFERENCES "regions" ("region_id") ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT "farmers_primary_crop_id_fkey" FOREIGN KEY ("primary_crop_id") REFERENCES "crops" ("crop_id") ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT "farmers_preferred_language_id_fkey" FOREIGN KEY ("preferred_language_id") REFERENCES "languages" ("language_id") ON DELETE SET NULL ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "ecosystem_conditions" (
    "ecosystem_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "region_id" INTEGER NOT NULL,
    "observation_date" DATETIME NOT NULL,
    "temperature_avg" DECIMAL,
    "rainfall_mm" DECIMAL,
    "humidity_percent" DECIMAL,
    "soil_type" TEXT,
    "soil_ph" DECIMAL,
    "soil_moisture" DECIMAL,
    "irrigation_type" TEXT,
    "weather_summary" TEXT,
    "risk_level" TEXT,
    CONSTRAINT "ecosystem_conditions_region_id_fkey" FOREIGN KEY ("region_id") REFERENCES "regions" ("region_id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "outbreaks" (
    "outbreak_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "region_id" INTEGER NOT NULL,
    "crop_id" INTEGER NOT NULL,
    "outbreak_type" TEXT NOT NULL,
    "outbreak_name" TEXT NOT NULL,
    "severity" TEXT,
    "detected_date" DATETIME NOT NULL,
    "source" TEXT,
    "symptoms" TEXT,
    "recommendation_window_days" INTEGER,
    "active_flag" BOOLEAN NOT NULL DEFAULT true,
    CONSTRAINT "outbreaks_crop_id_fkey" FOREIGN KEY ("crop_id") REFERENCES "crops" ("crop_id") ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT "outbreaks_region_id_fkey" FOREIGN KEY ("region_id") REFERENCES "regions" ("region_id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "farming_practices" (
    "practice_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "farmer_id" INTEGER NOT NULL,
    "crop_id" INTEGER NOT NULL,
    "farming_type" TEXT,
    "sowing_period" TEXT,
    "irrigation_method" TEXT,
    "mechanization_level" TEXT,
    "fertilizer_practice" TEXT,
    "pesticide_practice" TEXT,
    "labor_dependency" TEXT,
    "cultivation_frequency" TEXT,
    CONSTRAINT "farming_practices_crop_id_fkey" FOREIGN KEY ("crop_id") REFERENCES "crops" ("crop_id") ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT "farming_practices_farmer_id_fkey" FOREIGN KEY ("farmer_id") REFERENCES "farmers" ("farmer_id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "farmer_assets" (
    "asset_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "farmer_id" INTEGER NOT NULL,
    "asset_type" TEXT NOT NULL,
    "asset_name" TEXT,
    "ownership_type" TEXT,
    "quantity" INTEGER NOT NULL DEFAULT 1,
    "usable_flag" BOOLEAN NOT NULL DEFAULT true,
    CONSTRAINT "farmer_assets_farmer_id_fkey" FOREIGN KEY ("farmer_id") REFERENCES "farmers" ("farmer_id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "product_crop_fit" (
    "fit_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "product_id" INTEGER NOT NULL,
    "crop_id" INTEGER NOT NULL,
    "outbreak_type" TEXT,
    "outbreak_name" TEXT,
    "recommended_stage" TEXT,
    "relevance_score" DECIMAL,
    "approved_flag" BOOLEAN NOT NULL DEFAULT true,
    CONSTRAINT "product_crop_fit_crop_id_fkey" FOREIGN KEY ("crop_id") REFERENCES "crops" ("crop_id") ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT "product_crop_fit_product_id_fkey" FOREIGN KEY ("product_id") REFERENCES "products" ("product_id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "channel_preferences" (
    "preference_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "farmer_id" INTEGER NOT NULL,
    "whatsapp_opt_in" BOOLEAN NOT NULL DEFAULT false,
    "sms_opt_in" BOOLEAN NOT NULL DEFAULT false,
    "voice_call_opt_in" BOOLEAN NOT NULL DEFAULT false,
    "retailer_influence_score" DECIMAL,
    "field_rep_influence_score" DECIMAL,
    "preferred_contact_time" TEXT,
    "engagement_score" DECIMAL,
    "last_contacted_at" DATETIME,
    CONSTRAINT "channel_preferences_farmer_id_fkey" FOREIGN KEY ("farmer_id") REFERENCES "farmers" ("farmer_id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "campaigns" (
    "campaign_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "campaign_name" TEXT NOT NULL,
    "product_id" INTEGER NOT NULL,
    "crop_id" INTEGER,
    "region_id" INTEGER,
    "outbreak_id" INTEGER,
    "language_id" INTEGER,
    "channel" TEXT,
    "message_type" TEXT,
    "campaign_goal" TEXT,
    "launch_date" DATETIME,
    "end_date" DATETIME,
    "created_by" TEXT,
    "status" TEXT NOT NULL DEFAULT 'draft',
    CONSTRAINT "campaigns_crop_id_fkey" FOREIGN KEY ("crop_id") REFERENCES "crops" ("crop_id") ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT "campaigns_language_id_fkey" FOREIGN KEY ("language_id") REFERENCES "languages" ("language_id") ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT "campaigns_outbreak_id_fkey" FOREIGN KEY ("outbreak_id") REFERENCES "outbreaks" ("outbreak_id") ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT "campaigns_product_id_fkey" FOREIGN KEY ("product_id") REFERENCES "products" ("product_id") ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT "campaigns_region_id_fkey" FOREIGN KEY ("region_id") REFERENCES "regions" ("region_id") ON DELETE SET NULL ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "campaign_messages" (
    "message_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "campaign_id" INTEGER NOT NULL,
    "message_variant" TEXT,
    "whatsapp_text" TEXT,
    "sms_text" TEXT,
    "voice_script" TEXT,
    "field_rep_script" TEXT,
    "retailer_script" TEXT,
    "visual_prompt" TEXT,
    "compliance_approved" BOOLEAN NOT NULL DEFAULT false,
    CONSTRAINT "campaign_messages_campaign_id_fkey" FOREIGN KEY ("campaign_id") REFERENCES "campaigns" ("campaign_id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "campaign_targets" (
    "target_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "campaign_id" INTEGER NOT NULL,
    "farmer_id" INTEGER NOT NULL,
    "recommended_channel" TEXT,
    "priority_score" DECIMAL,
    "predicted_engagement_probability" DECIMAL,
    "predicted_inquiry_probability" DECIMAL,
    "recommended_send_time" TEXT,
    "status" TEXT NOT NULL DEFAULT 'pending',
    CONSTRAINT "campaign_targets_campaign_id_fkey" FOREIGN KEY ("campaign_id") REFERENCES "campaigns" ("campaign_id") ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT "campaign_targets_farmer_id_fkey" FOREIGN KEY ("farmer_id") REFERENCES "farmers" ("farmer_id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "campaign_responses" (
    "response_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "target_id" INTEGER NOT NULL,
    "delivery_status" TEXT,
    "opened_flag" BOOLEAN NOT NULL DEFAULT false,
    "clicked_flag" BOOLEAN NOT NULL DEFAULT false,
    "replied_flag" BOOLEAN NOT NULL DEFAULT false,
    "inquiry_flag" BOOLEAN NOT NULL DEFAULT false,
    "purchase_flag" BOOLEAN NOT NULL DEFAULT false,
    "response_date" DATETIME,
    "notes" TEXT,
    CONSTRAINT "campaign_responses_target_id_fkey" FOREIGN KEY ("target_id") REFERENCES "campaign_targets" ("target_id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "retailers" (
    "retailer_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "retailer_name" TEXT NOT NULL,
    "region_id" INTEGER NOT NULL,
    "contact_person" TEXT,
    "phone" TEXT,
    "major_crops_served" TEXT,
    "key_products_stocked" TEXT,
    "influence_score" DECIMAL,
    CONSTRAINT "retailers_region_id_fkey" FOREIGN KEY ("region_id") REFERENCES "regions" ("region_id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "influencers" (
    "influencer_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "influencer_name" TEXT NOT NULL,
    "influencer_type" TEXT,
    "region_id" INTEGER,
    "primary_language_id" INTEGER,
    "primary_crop_focus" TEXT,
    "platform" TEXT NOT NULL DEFAULT 'WhatsApp',
    "follower_count" INTEGER,
    "estimated_farmer_reach" INTEGER,
    "trust_score" DECIMAL,
    "engagement_rate" DECIMAL,
    "content_strength" TEXT,
    "contact_phone" TEXT,
    "contact_email" TEXT,
    "commercial_terms" TEXT,
    "compliance_status" TEXT NOT NULL DEFAULT 'pending',
    "status" TEXT NOT NULL DEFAULT 'active',
    CONSTRAINT "influencers_primary_language_id_fkey" FOREIGN KEY ("primary_language_id") REFERENCES "languages" ("language_id") ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT "influencers_region_id_fkey" FOREIGN KEY ("region_id") REFERENCES "regions" ("region_id") ON DELETE SET NULL ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "influencer_campaigns" (
    "influencer_campaign_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "campaign_id" INTEGER NOT NULL,
    "influencer_id" INTEGER NOT NULL,
    "activation_role" TEXT,
    "content_format" TEXT,
    "planned_publish_date" DATETIME,
    "expected_reach" INTEGER,
    "budget_allocated" DECIMAL,
    "approval_status" TEXT NOT NULL DEFAULT 'draft',
    "tracking_code" TEXT,
    "notes" TEXT,
    CONSTRAINT "influencer_campaigns_campaign_id_fkey" FOREIGN KEY ("campaign_id") REFERENCES "campaigns" ("campaign_id") ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT "influencer_campaigns_influencer_id_fkey" FOREIGN KEY ("influencer_id") REFERENCES "influencers" ("influencer_id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "influencer_performance" (
    "performance_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "influencer_campaign_id" INTEGER NOT NULL,
    "actual_reach" INTEGER,
    "views_or_listens" INTEGER,
    "shares" INTEGER,
    "replies" INTEGER,
    "inquiries_generated" INTEGER,
    "retailer_visits_attributed" INTEGER,
    "purchases_attributed" INTEGER,
    "cost_per_inquiry" DECIMAL,
    "conversion_rate" DECIMAL,
    "performance_notes" TEXT,
    CONSTRAINT "influencer_performance_influencer_campaign_id_fkey" FOREIGN KEY ("influencer_campaign_id") REFERENCES "influencer_campaigns" ("influencer_campaign_id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateIndex
CREATE UNIQUE INDEX "products_product_name_key" ON "products"("product_name");

-- CreateIndex
CREATE UNIQUE INDEX "crops_crop_name_key" ON "crops"("crop_name");

-- CreateIndex
CREATE UNIQUE INDEX "regions_country_state_district_block_taluk_village_key" ON "regions"("country", "state", "district", "block_taluk", "village");

-- CreateIndex
CREATE UNIQUE INDEX "languages_language_name_key" ON "languages"("language_name");

-- CreateIndex
CREATE UNIQUE INDEX "product_crop_fit_product_id_crop_id_outbreak_type_outbreak_name_recommended_stage_key" ON "product_crop_fit"("product_id", "crop_id", "outbreak_type", "outbreak_name", "recommended_stage");

-- CreateIndex
CREATE UNIQUE INDEX "campaign_responses_target_id_key" ON "campaign_responses"("target_id");

-- CreateIndex
CREATE UNIQUE INDEX "influencers_influencer_name_key" ON "influencers"("influencer_name");
