import type { PrismaClient } from "@prisma/client";
import Papa from "papaparse";

// Deprecated: retained for reference only. Active CSV AI workflows use
// TokenRouter via lib/ai/tokenrouter-csv-ingestion.ts and must not fall back
// to this local rule-based implementation.

export type CsvType = "farmer survey" | "product data" | "influencer data" | "campaign history" | "unknown";

export type ColumnMapping = {
  sourceColumn: string;
  targetTable: string;
  targetField: string;
  confidence: number;
  requiredFlag: boolean;
  transformNote?: string;
};

export type MappedPreviewRow = {
  rowNumber: number;
  raw: Record<string, string>;
  mapped: Record<string, unknown>;
  validationStatus: "valid" | "invalid";
  errors: string[];
  aiConfidence: number;
};

const CSV_TYPE_OPTIONS: CsvType[] = [
  "farmer survey",
  "product data",
  "influencer data",
  "campaign history",
  "unknown"
];

const TYPE_SIGNALS: Record<CsvType, string[]> = {
  "farmer survey": [
    "farmer",
    "farmername",
    "village",
    "cropgrown",
    "landsize",
    "mobiletype",
    "useswhatsapp",
    "preferredcommunication",
    "retailerinfluence"
  ],
  "product data": [
    "product",
    "productname",
    "productcategory",
    "producttype",
    "activeingredient",
    "priceperunit",
    "targetpest",
    "cropstage"
  ],
  "influencer data": [
    "influencer",
    "influencername",
    "platform",
    "followers",
    "crop expertise",
    "cropexpertise",
    "trustscore",
    "engagementrate"
  ],
  "campaign history": [
    "campaign",
    "campaignname",
    "engagementrate",
    "inquiryrate",
    "purchaseconversion",
    "farmerstargeted",
    "conversion"
  ],
  unknown: []
};

const FIELD_ALIASES: Record<CsvType, Array<{
  aliases: string[];
  targets: Array<{ table: string; field: string; required?: boolean; note?: string }>;
}>> = {
  "farmer survey": [
    { aliases: ["farmer name", "farmer", "name", "farmer_name"], targets: [{ table: "farmers", field: "farmerName", required: true }] },
    { aliases: ["state", "region", "location"], targets: [{ table: "regions", field: "state" }] },
    { aliases: ["district"], targets: [{ table: "regions", field: "district" }] },
    { aliases: ["village", "village name"], targets: [{ table: "regions", field: "village", required: true }] },
    {
      aliases: ["crop grown", "crop", "crop name", "primary crop", "crop_grown"],
      targets: [
        { table: "crops", field: "cropName", required: true },
        { table: "farmers", field: "primaryCropId", required: true, note: "Resolved through crops.cropName" }
      ]
    },
    { aliases: ["land size", "land size acres", "farm size", "acreage", "acres"], targets: [{ table: "farmers", field: "landSizeAcres" }] },
    {
      aliases: ["mobile type", "phone type", "mobile_type"],
      targets: [
        { table: "farmers", field: "smartphoneUser", note: "Smartphone-like values become true" },
        { table: "farmers", field: "featurePhoneUser", note: "Feature-phone values become true" }
      ]
    },
    { aliases: ["language", "preferred language"], targets: [{ table: "languages", field: "languageName" }] },
    { aliases: ["income", "income band", "annual income"], targets: [{ table: "farmers", field: "annualIncomeBand" }] },
    { aliases: ["preferred communication", "trust channel", "preferred channel"], targets: [{ table: "farmers", field: "trustChannel" }] },
    { aliases: ["preferred contact time", "contact time"], targets: [{ table: "channel_preferences", field: "preferredContactTime" }] },
    { aliases: ["uses whatsapp", "whatsapp", "whatsapp opt in"], targets: [{ table: "channel_preferences", field: "whatsappOptIn" }] },
    { aliases: ["retailer influence", "retailer influence score"], targets: [{ table: "channel_preferences", field: "retailerInfluenceScore" }] }
  ],
  "product data": [
    { aliases: ["product name", "product", "brand name"], targets: [{ table: "products", field: "productName", required: true }] },
    { aliases: ["category", "product category"], targets: [{ table: "products", field: "productCategory", required: true }] },
    { aliases: ["product type", "type"], targets: [{ table: "products", field: "productType" }] },
    { aliases: ["price", "price per unit"], targets: [{ table: "products", field: "pricePerUnit" }] },
    { aliases: ["unit", "unit type"], targets: [{ table: "products", field: "unitType" }] },
    { aliases: ["active ingredient"], targets: [{ table: "products", field: "activeIngredient" }] },
    { aliases: ["target pest", "target pest type", "threat"], targets: [{ table: "products", field: "targetPestType" }] },
    { aliases: ["crop stage", "crop stage relevance", "stage"], targets: [{ table: "products", field: "cropStageRelevance" }] },
    { aliases: ["description", "positioning"], targets: [{ table: "products", field: "description" }] },
    { aliases: ["crop", "crop name", "target crop"], targets: [{ table: "crops", field: "cropName" }] }
  ],
  "influencer data": [
    { aliases: ["influencer name", "influencer", "creator name"], targets: [{ table: "influencers", field: "influencerName", required: true }] },
    { aliases: ["influencer type", "type"], targets: [{ table: "influencers", field: "influencerType" }] },
    { aliases: ["platform", "channel"], targets: [{ table: "influencers", field: "platform" }] },
    { aliases: ["region", "state"], targets: [{ table: "regions", field: "state", required: true }] },
    { aliases: ["village"], targets: [{ table: "regions", field: "village" }] },
    { aliases: ["language", "primary language"], targets: [{ table: "languages", field: "languageName" }] },
    { aliases: ["crop expertise", "crop focus", "primary crop focus"], targets: [{ table: "influencers", field: "cropExpertise" }] },
    { aliases: ["followers", "follower count"], targets: [{ table: "influencers", field: "followerCount" }] },
    { aliases: ["farmer reach", "estimated farmer reach", "reach"], targets: [{ table: "influencers", field: "estimatedFarmerReach" }] },
    { aliases: ["trust score"], targets: [{ table: "influencers", field: "trustScore" }] },
    { aliases: ["engagement rate"], targets: [{ table: "influencers", field: "engagementRate" }] }
  ],
  "campaign history": [
    { aliases: ["campaign name", "campaign"], targets: [{ table: "campaigns", field: "campaignName", required: true }] },
    { aliases: ["product", "product name"], targets: [{ table: "products", field: "productName", required: true }] },
    { aliases: ["region", "state"], targets: [{ table: "regions", field: "state" }] },
    { aliases: ["crop", "crop name"], targets: [{ table: "crops", field: "cropName" }] },
    { aliases: ["channel"], targets: [{ table: "campaigns", field: "channel" }] },
    { aliases: ["influencer", "influencer name"], targets: [{ table: "influencers", field: "influencerName" }] },
    { aliases: ["farmers targeted", "targets"], targets: [{ table: "campaign_targets", field: "farmersTargeted" }] },
    { aliases: ["engagement rate", "engagement"], targets: [{ table: "campaign_responses", field: "engagementRate", required: true }] },
    { aliases: ["inquiry rate", "inquiries"], targets: [{ table: "campaign_responses", field: "inquiryRate", required: true }] },
    { aliases: ["purchase conversion", "conversion", "purchase rate"], targets: [{ table: "campaign_responses", field: "purchaseConversion", required: true }] },
    { aliases: ["status"], targets: [{ table: "campaigns", field: "status" }] },
    { aliases: ["date", "launch date"], targets: [{ table: "campaigns", field: "launchDate" }] }
  ],
  unknown: []
};

function normalize(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "");
}

function getMappedValue(mapped: Record<string, unknown>, table: string, field: string) {
  return mapped[`${table}.${field}`];
}

function setMappedValue(mapped: Record<string, unknown>, table: string, field: string, value: unknown) {
  mapped[`${table}.${field}`] = value;
}

function toBoolean(value: unknown) {
  const normalized = String(value ?? "").trim().toLowerCase();
  return ["yes", "true", "1", "y", "whatsapp", "smartphone"].includes(normalized);
}

function toNumber(value: unknown) {
  const cleaned = String(value ?? "").replace(/[%₹,$]/g, "").trim();
  if (!cleaned) {
    return undefined;
  }
  const numeric = Number(cleaned);
  return Number.isFinite(numeric) ? numeric : undefined;
}

function cleanText(value: unknown) {
  const text = String(value ?? "").trim();
  return text || undefined;
}

export function parseCsv(csv: string) {
  const parsed = Papa.parse<Record<string, string>>(csv, {
    header: true,
    skipEmptyLines: true,
    transformHeader: (header) => header.trim()
  });

  if (parsed.errors.length) {
    throw new Error(parsed.errors[0]?.message || "Unable to parse CSV.");
  }

  const columns = parsed.meta.fields?.filter(Boolean) ?? Object.keys(parsed.data[0] ?? {});
  return { columns, rows: parsed.data };
}

export function detectCsvType(columns: string[]): { csvType: CsvType; confidence: number } {
  const normalizedColumns = columns.map(normalize);
  const scores = CSV_TYPE_OPTIONS.filter((type) => type !== "unknown").map((type) => {
    const signals = TYPE_SIGNALS[type];
    const hits = signals.filter((signal) => normalizedColumns.some((column) => column.includes(normalize(signal)))).length;
    return { type, hits, score: hits / Math.max(signals.length, 1) };
  });

  const best = scores.sort((a, b) => b.hits - a.hits || b.score - a.score)[0];
  if (!best || best.hits < 2) {
    return { csvType: "unknown", confidence: 35 };
  }

  return {
    csvType: best.type,
    confidence: Math.min(96, 55 + best.hits * 8)
  };
}

export function mapColumnsToSchema(columns: string[], csvType: CsvType): ColumnMapping[] {
  const aliases = FIELD_ALIASES[csvType] ?? [];
  const mappings: ColumnMapping[] = [];

  for (const column of columns) {
    const normalizedColumn = normalize(column);
    const matched = aliases.find((entry) =>
      entry.aliases.some((alias) => normalizedColumn === normalize(alias) || normalizedColumn.includes(normalize(alias)))
    );

    if (!matched) {
      mappings.push({
        sourceColumn: column,
        targetTable: "unmapped",
        targetField: "ignore",
        confidence: 30,
        requiredFlag: false,
        transformNote: "No confident rule-based mapping found"
      });
      continue;
    }

    for (const target of matched.targets) {
      mappings.push({
        sourceColumn: column,
        targetTable: target.table,
        targetField: target.field,
        confidence: 88,
        requiredFlag: Boolean(target.required),
        transformNote: target.note
      });
    }
  }

  return mappings;
}

export function buildMappedRows(
  rows: Record<string, string>[],
  mappings: ColumnMapping[],
  csvType: CsvType
) {
  return rows.map((row, index) => {
    const mapped: Record<string, unknown> = {};

    for (const mapping of mappings) {
      if (mapping.targetTable === "unmapped") {
        continue;
      }

      const rawValue = row[mapping.sourceColumn];
      const target = `${mapping.targetTable}.${mapping.targetField}`;

      if (target === "farmers.smartphoneUser") {
        const text = String(rawValue ?? "").toLowerCase();
        setMappedValue(mapped, mapping.targetTable, mapping.targetField, text.includes("smart") || toBoolean(rawValue));
        continue;
      }

      if (target === "farmers.featurePhoneUser") {
        const text = String(rawValue ?? "").toLowerCase();
        setMappedValue(mapped, mapping.targetTable, mapping.targetField, text.includes("feature"));
        continue;
      }

      if (
        target.endsWith("landSizeAcres") ||
        target.endsWith("pricePerUnit") ||
        target.endsWith("retailerInfluenceScore") ||
        target.endsWith("followerCount") ||
        target.endsWith("estimatedFarmerReach") ||
        target.endsWith("trustScore") ||
        target.endsWith("engagementRate") ||
        target.endsWith("inquiryRate") ||
        target.endsWith("purchaseConversion") ||
        target.endsWith("farmersTargeted")
      ) {
        setMappedValue(mapped, mapping.targetTable, mapping.targetField, toNumber(rawValue));
        continue;
      }

      if (target.endsWith("whatsappOptIn")) {
        setMappedValue(mapped, mapping.targetTable, mapping.targetField, toBoolean(rawValue));
        continue;
      }

      setMappedValue(mapped, mapping.targetTable, mapping.targetField, cleanText(rawValue));
    }

    return {
      rowNumber: index + 1,
      raw: row,
      mapped,
      validationStatus: "valid" as const,
      errors: [],
      aiConfidence: csvType === "unknown" ? 35 : 86
    };
  });
}

export async function validateMappedRows(params: {
  prisma: PrismaClient;
  mappedRows: MappedPreviewRow[];
  csvType: CsvType;
}) {
  const { prisma, mappedRows, csvType } = params;
  const existingFarmers = await prisma.farmer.findMany({
    include: { region: true }
  });
  const existingFarmerKeys = new Set(
    existingFarmers.map((farmer) => `${farmer.name || ""}|${farmer.region.village || ""}`.toLowerCase())
  );
  const seenFarmerKeys = new Set<string>();

  return mappedRows.map((row) => {
    const errors: string[] = [];
    const mapped = row.mapped;

    if (csvType === "farmer survey") {
      const farmerName = cleanText(getMappedValue(mapped, "farmers", "farmerName"));
      const village = cleanText(getMappedValue(mapped, "regions", "village"));
      const crop = cleanText(getMappedValue(mapped, "crops", "cropName"));
      const language = cleanText(getMappedValue(mapped, "languages", "languageName"));
      const farmerKey = `${farmerName || ""}|${village || ""}`.toLowerCase();

      if (!farmerName) errors.push("missing farmer name");
      if (!village) errors.push("missing village");
      if (!crop || crop.length < 2 || /\d/.test(crop)) errors.push("invalid crop");
      if (language && /\d/.test(language)) errors.push("invalid language");
      if (farmerName && village && (existingFarmerKeys.has(farmerKey) || seenFarmerKeys.has(farmerKey))) {
        errors.push("duplicate farmer");
      }
      if (farmerName && village) {
        seenFarmerKeys.add(farmerKey);
      }
    }

    if (csvType === "product data") {
      if (!cleanText(getMappedValue(mapped, "products", "productName"))) {
        errors.push("missing product name");
      }
    }

    if (csvType === "influencer data") {
      if (!cleanText(getMappedValue(mapped, "influencers", "influencerName"))) {
        errors.push("missing influencer name");
      }
      if (!cleanText(getMappedValue(mapped, "regions", "state"))) {
        errors.push("influencer without region");
      }
    }

    if (csvType === "campaign history") {
      const hasMetrics =
        getMappedValue(mapped, "campaign_responses", "engagementRate") !== undefined ||
        getMappedValue(mapped, "campaign_responses", "inquiryRate") !== undefined ||
        getMappedValue(mapped, "campaign_responses", "purchaseConversion") !== undefined;
      if (!cleanText(getMappedValue(mapped, "campaigns", "campaignName"))) {
        errors.push("missing campaign name");
      }
      if (!hasMetrics) {
        errors.push("campaign history without metrics");
      }
    }

    if (csvType === "unknown") {
      errors.push("unknown csv type");
    }

    return {
      ...row,
      validationStatus: errors.length ? "invalid" as const : "valid" as const,
      errors,
      aiConfidence: Math.max(30, row.aiConfidence - errors.length * 12)
    };
  });
}

export async function importApprovedRows(params: {
  prisma: PrismaClient;
  csvType: CsvType;
  rows: MappedPreviewRow[];
}) {
  const { prisma, csvType, rows } = params;
  let imported = 0;

  for (const row of rows) {
    if (row.validationStatus !== "valid") {
      continue;
    }

    const mapped = row.mapped;

    if (csvType === "farmer survey") {
      const state = cleanText(getMappedValue(mapped, "regions", "state")) || "Unknown";
      const village = cleanText(getMappedValue(mapped, "regions", "village")) || "";
      const district = cleanText(getMappedValue(mapped, "regions", "district")) || "";
      const cropName = cleanText(getMappedValue(mapped, "crops", "cropName"));
      const languageName = cleanText(getMappedValue(mapped, "languages", "languageName"));

      const region = await upsertRegion(prisma, { state, district, village });
      const crop = cropName
        ? await prisma.crop.upsert({
            where: { name: cropName },
            create: { name: cropName, category: "Survey crop", season: "Kharif" },
            update: {}
          })
        : null;
      const language = languageName
        ? await prisma.language.upsert({
            where: { name: languageName },
            create: { name: languageName, scriptType: "Native script" },
            update: {}
          })
        : null;

      const farmer = await prisma.farmer.create({
        data: {
          name: cleanText(getMappedValue(mapped, "farmers", "farmerName")),
          regionId: region.id,
          primaryCropId: crop?.id,
          landSizeAcres: toNumber(getMappedValue(mapped, "farmers", "landSizeAcres")),
          annualIncomeBand: cleanText(getMappedValue(mapped, "farmers", "annualIncomeBand")),
          smartphoneUser: Boolean(getMappedValue(mapped, "farmers", "smartphoneUser")),
          featurePhoneUser: Boolean(getMappedValue(mapped, "farmers", "featurePhoneUser")),
          preferredLanguageId: language?.id,
          trustChannel: cleanText(getMappedValue(mapped, "farmers", "trustChannel"))
        }
      });

      await prisma.channelPreference.create({
        data: {
          farmerId: farmer.id,
          whatsappOptIn: Boolean(getMappedValue(mapped, "channel_preferences", "whatsappOptIn")),
          retailerInfluenceScore: toNumber(getMappedValue(mapped, "channel_preferences", "retailerInfluenceScore")),
          preferredContactTime: cleanText(getMappedValue(mapped, "channel_preferences", "preferredContactTime")),
          engagementScore: 50
        }
      });
      imported += 1;
    }

    if (csvType === "product data") {
      const productName = cleanText(getMappedValue(mapped, "products", "productName"));
      if (!productName) continue;
      const product = await prisma.product.upsert({
        where: { name: productName },
        create: {
          name: productName,
          category: cleanText(getMappedValue(mapped, "products", "productCategory")) || "Crop solution",
          productType: cleanText(getMappedValue(mapped, "products", "productType")),
          pricePerUnit: toNumber(getMappedValue(mapped, "products", "pricePerUnit")),
          unitType: cleanText(getMappedValue(mapped, "products", "unitType")),
          activeIngredient: cleanText(getMappedValue(mapped, "products", "activeIngredient")),
          targetPestType: cleanText(getMappedValue(mapped, "products", "targetPestType")),
          cropStageRelevance: cleanText(getMappedValue(mapped, "products", "cropStageRelevance")),
          positioning: cleanText(getMappedValue(mapped, "products", "description")),
          status: "active"
        },
        update: {
          category: cleanText(getMappedValue(mapped, "products", "productCategory")) || "Crop solution",
          productType: cleanText(getMappedValue(mapped, "products", "productType")),
          pricePerUnit: toNumber(getMappedValue(mapped, "products", "pricePerUnit")),
          unitType: cleanText(getMappedValue(mapped, "products", "unitType")),
          activeIngredient: cleanText(getMappedValue(mapped, "products", "activeIngredient")),
          targetPestType: cleanText(getMappedValue(mapped, "products", "targetPestType")),
          cropStageRelevance: cleanText(getMappedValue(mapped, "products", "cropStageRelevance")),
          positioning: cleanText(getMappedValue(mapped, "products", "description"))
        }
      });
      const cropName = cleanText(getMappedValue(mapped, "crops", "cropName"));
      if (cropName) {
        const crop = await prisma.crop.upsert({
          where: { name: cropName },
          create: { name: cropName, category: "Mapped crop", season: "Kharif" },
          update: {}
        });
        await prisma.productCropFit.upsert({
          where: {
            productId_cropId_outbreakType_outbreakName_recommendedStage: {
              productId: product.id,
              cropId: crop.id,
              outbreakType: cleanText(getMappedValue(mapped, "products", "targetPestType")) || "",
              outbreakName: "",
              recommendedStage: cleanText(getMappedValue(mapped, "products", "cropStageRelevance")) || ""
            }
          },
          create: {
            productId: product.id,
            cropId: crop.id,
            outbreakType: cleanText(getMappedValue(mapped, "products", "targetPestType")) || "",
            outbreakName: "",
            recommendedStage: cleanText(getMappedValue(mapped, "products", "cropStageRelevance")) || "",
            relevanceScore: 75,
            approvedFlag: true
          },
          update: {}
        });
      }
      imported += 1;
    }

    if (csvType === "influencer data") {
      const influencerName = cleanText(getMappedValue(mapped, "influencers", "influencerName"));
      if (!influencerName) continue;
      const region = await upsertRegion(prisma, {
        state: cleanText(getMappedValue(mapped, "regions", "state")) || "Unknown",
        district: "",
        village: cleanText(getMappedValue(mapped, "regions", "village")) || ""
      });
      const languageName = cleanText(getMappedValue(mapped, "languages", "languageName"));
      const language = languageName
        ? await prisma.language.upsert({
            where: { name: languageName },
            create: { name: languageName, scriptType: "Native script" },
            update: {}
          })
        : null;

      await prisma.influencer.upsert({
        where: { name: influencerName },
        create: {
          name: influencerName,
          influencerType: cleanText(getMappedValue(mapped, "influencers", "influencerType")),
          regionId: region.id,
          primaryLanguageId: language?.id,
          primaryCropFocus: cleanText(getMappedValue(mapped, "influencers", "cropExpertise")),
          channel: cleanText(getMappedValue(mapped, "influencers", "platform")) || "WhatsApp",
          followerCount: toNumber(getMappedValue(mapped, "influencers", "followerCount")),
          reachScore: toNumber(getMappedValue(mapped, "influencers", "estimatedFarmerReach")),
          trustScore: toNumber(getMappedValue(mapped, "influencers", "trustScore")),
          engagementRate: toNumber(getMappedValue(mapped, "influencers", "engagementRate")),
          contentStrength: cleanText(getMappedValue(mapped, "influencers", "cropExpertise")),
          complianceStatus: "pending",
          status: "active"
        },
        update: {
          influencerType: cleanText(getMappedValue(mapped, "influencers", "influencerType")),
          regionId: region.id,
          primaryLanguageId: language?.id,
          primaryCropFocus: cleanText(getMappedValue(mapped, "influencers", "cropExpertise")),
          channel: cleanText(getMappedValue(mapped, "influencers", "platform")) || "WhatsApp",
          followerCount: toNumber(getMappedValue(mapped, "influencers", "followerCount")),
          reachScore: toNumber(getMappedValue(mapped, "influencers", "estimatedFarmerReach")),
          trustScore: toNumber(getMappedValue(mapped, "influencers", "trustScore")),
          engagementRate: toNumber(getMappedValue(mapped, "influencers", "engagementRate")),
          contentStrength: cleanText(getMappedValue(mapped, "influencers", "cropExpertise"))
        }
      });
      imported += 1;
    }

    if (csvType === "campaign history") {
      const campaignName = cleanText(getMappedValue(mapped, "campaigns", "campaignName"));
      const productName = cleanText(getMappedValue(mapped, "products", "productName"));
      if (!campaignName || !productName) continue;
      const product = await prisma.product.upsert({
        where: { name: productName },
        create: { name: productName, category: "Imported product", status: "active" },
        update: {}
      });
      const cropName = cleanText(getMappedValue(mapped, "crops", "cropName"));
      const crop = cropName
        ? await prisma.crop.upsert({
            where: { name: cropName },
            create: { name: cropName, category: "Imported crop", season: "Kharif" },
            update: {}
          })
        : null;
      const state = cleanText(getMappedValue(mapped, "regions", "state"));
      const region = state ? await upsertRegion(prisma, { state, district: "", village: "" }) : null;

      const campaign = await prisma.campaign.create({
        data: {
          name: campaignName,
          productId: product.id,
          cropId: crop?.id,
          regionId: region?.id,
          channel: cleanText(getMappedValue(mapped, "campaigns", "channel")),
          messageType: "Imported history",
          campaignGoal: "Learning",
          launchDate: cleanText(getMappedValue(mapped, "campaigns", "launchDate"))
            ? new Date(String(getMappedValue(mapped, "campaigns", "launchDate")))
            : new Date(),
          createdBy: "CSV import",
          status: cleanText(getMappedValue(mapped, "campaigns", "status")) || "closed"
        }
      });

      const farmer = await prisma.farmer.create({
        data: {
          name: `${campaignName} aggregate target`,
          regionId: region?.id || (await upsertRegion(prisma, { state: "Imported", district: "", village: "" })).id,
          primaryCropId: crop?.id,
          farmerSegment: "Imported campaign aggregate"
        }
      });
      const target = await prisma.campaignTarget.create({
        data: {
          campaignId: campaign.id,
          farmerId: farmer.id,
          recommendedChannel: cleanText(getMappedValue(mapped, "campaigns", "channel")),
          priorityScore: toNumber(getMappedValue(mapped, "campaign_targets", "farmersTargeted")) || 50,
          status: "responded"
        }
      });
      await prisma.campaignResponse.create({
        data: {
          targetId: target.id,
          deliveryStatus: "delivered",
          openedFlag: Boolean((toNumber(getMappedValue(mapped, "campaign_responses", "engagementRate")) || 0) > 0),
          inquiryFlag: Boolean((toNumber(getMappedValue(mapped, "campaign_responses", "inquiryRate")) || 0) > 0),
          purchaseFlag: Boolean((toNumber(getMappedValue(mapped, "campaign_responses", "purchaseConversion")) || 0) > 0),
          responseDate: new Date(),
          notes: `Imported metrics: engagement ${getMappedValue(mapped, "campaign_responses", "engagementRate") ?? "N/A"}%, inquiry ${getMappedValue(mapped, "campaign_responses", "inquiryRate") ?? "N/A"}%, purchase ${getMappedValue(mapped, "campaign_responses", "purchaseConversion") ?? "N/A"}%.`
        }
      });
      imported += 1;
    }
  }

  return imported;
}

async function upsertRegion(
  prisma: PrismaClient,
  params: { state: string; district?: string; village?: string }
) {
  return prisma.region.upsert({
    where: {
      country_state_district_blockTaluk_village: {
        country: "India",
        state: params.state,
        district: params.district || "",
        blockTaluk: "",
        village: params.village || ""
      }
    },
    create: {
      country: "India",
      state: params.state,
      district: params.district || "",
      blockTaluk: "",
      village: params.village || ""
    },
    update: {}
  });
}
