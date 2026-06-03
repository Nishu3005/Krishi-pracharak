import type {
  Campaign,
  CampaignResponse,
  CampaignTarget,
  Crop,
  EcosystemCondition,
  Farmer,
  FarmerAsset,
  FarmingPractice,
  Language,
  Outbreak,
  Product,
  ProductCropFit,
  Region
} from "@prisma/client";

import type { Segment } from "@/lib/types";

// Deprecated: retained for reference only. Active farmer segment generation
// uses TokenRouter via lib/ai/tokenrouter-segmentation.ts and must not fall
// back to this local rule-based implementation.

const DEMO_CURRENT_DATE = new Date("2026-05-30T00:00:00.000Z");

type ProductWithFits = Product & {
  cropFits: Array<ProductCropFit & { crop: Crop }>;
};

type FarmerContext = Farmer & {
  primaryCrop?: Crop | null;
  region?: Region | null;
  preferredLanguage?: Language | null;
  assets: FarmerAsset[];
  farmingPractices: FarmingPractice[];
};

type CampaignContext = Campaign & {
  targets: Array<CampaignTarget & { response: CampaignResponse | null }>;
};

type SegmentContext = {
  product: ProductWithFits;
  region?: Region | null;
  regions: Region[];
  crops: Crop[];
  farmers: FarmerContext[];
  ecosystemConditions: EcosystemCondition[];
  outbreaks: Outbreak[];
  campaigns: CampaignContext[];
  additionalInfo?: string;
};

type ScoreInputs = {
  productFit: number;
  regionalRelevance: number;
  cropStageRelevance: number;
  urgency: number;
  farmerNeed: number;
  pastResponse: number;
};

type DataConfidenceBreakdown = NonNullable<Segment["dataConfidenceBreakdown"]>;

function clamp(value: number, min = 0, max = 100) {
  return Math.max(min, Math.min(max, Math.round(value)));
}

function avg(values: number[], fallback = 0) {
  if (!values.length) {
    return fallback;
  }
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function severityScore(value?: string | null) {
  const normalized = String(value || "").toLowerCase();
  if (normalized.includes("severe")) return 96;
  if (normalized.includes("high")) return 88;
  if (normalized.includes("medium")) return 68;
  if (normalized.includes("low")) return 42;
  return 55;
}

function regionName(region?: Region | null, fallback?: string) {
  if (region) {
    return region.district ? `${region.state} / ${region.district}` : region.state;
  }
  return fallback || "Multi-region";
}

function mainCropName(crops: Crop[], farmers: FarmerContext[]) {
  return (
    crops[0]?.name ||
    farmers.find((farmer) => farmer.primaryCrop)?.primaryCrop?.name ||
    "mixed crop"
  );
}

function averageFarmSize(farmers: FarmerContext[]) {
  return avg(
    farmers
      .map((entry) => entry.landSizeAcres)
      .filter((value): value is NonNullable<typeof value> => value !== null)
      .map(Number),
    4
  );
}

function pastCampaignScore(campaigns: CampaignContext[]) {
  const targets = campaigns.flatMap((campaign) => campaign.targets);
  if (!targets.length) {
    return 55;
  }

  const responses = targets.map((target) => target.response).filter(Boolean);
  const engagement = responses.filter(
    (response) => response?.openedFlag || response?.clickedFlag || response?.repliedFlag
  ).length;
  const inquiry = responses.filter((response) => response?.inquiryFlag).length;

  return clamp(45 + (engagement / targets.length) * 30 + (inquiry / targets.length) * 25);
}

function dataConfidenceBreakdown(params: {
  farmers: FarmerContext[];
  regions: Region[];
  ecosystemConditions: EcosystemCondition[];
  outbreaks: Outbreak[];
  campaigns: CampaignContext[];
}): DataConfidenceBreakdown {
  const { farmers, regions, ecosystemConditions, outbreaks, campaigns } = params;
  const latestWeather = ecosystemConditions[0]?.observationDate;
  const weatherFreshness = latestWeather
    ? Math.max(0, 20 - Math.min(20, Math.floor((DEMO_CURRENT_DATE.getTime() - latestWeather.getTime()) / 86_400_000)))
    : 0;

  return {
    surveyDataAvailability: farmers.length ? 25 : 8,
    regionDataAvailability: regions.length ? 20 : 8,
    weatherDataFreshness: weatherFreshness,
    outbreakDataConfidence: outbreaks.length ? 20 : 10,
    campaignHistoryAvailability: campaigns.length ? 15 : 7
  };
}

function dataConfidence(params: {
  farmers: FarmerContext[];
  regions: Region[];
  ecosystemConditions: EcosystemCondition[];
  outbreaks: Outbreak[];
  campaigns: CampaignContext[];
}) {
  const breakdown = dataConfidenceBreakdown(params);
  return clamp(
    breakdown.surveyDataAvailability +
      breakdown.regionDataAvailability +
      breakdown.weatherDataFreshness +
      breakdown.outbreakDataConfidence +
      breakdown.campaignHistoryAvailability
  );
}

function estimateFarmers(baseCount: number, multiplier: number) {
  return Math.max(1, Math.round(Math.max(baseCount, 6) * multiplier));
}

function scoreSegment(params: ScoreInputs & { offset?: number }) {
  const { productFit, regionalRelevance, cropStageRelevance, urgency, farmerNeed, pastResponse, offset = 0 } = params;
  return clamp(
    productFit * 0.25 +
      regionalRelevance * 0.2 +
      cropStageRelevance * 0.2 +
      urgency * 0.15 +
      farmerNeed * 0.1 +
      pastResponse * 0.1 +
      offset
  );
}

function scoreBreakdown(scores: ScoreInputs): NonNullable<Segment["scoreBreakdown"]> {
  return {
    productFit: clamp(scores.productFit),
    regionalRelevance: clamp(scores.regionalRelevance),
    cropStageRelevance: clamp(scores.cropStageRelevance),
    weatherOutbreakUrgency: clamp(scores.urgency),
    farmerNeed: clamp(scores.farmerNeed),
    pastCampaignResponse: clamp(scores.pastResponse)
  };
}

function withScoreAdjustments(scores: ScoreInputs, adjustments: Partial<ScoreInputs> = {}): ScoreInputs {
  return {
    productFit: clamp(scores.productFit + (adjustments.productFit || 0)),
    regionalRelevance: clamp(scores.regionalRelevance + (adjustments.regionalRelevance || 0)),
    cropStageRelevance: clamp(scores.cropStageRelevance + (adjustments.cropStageRelevance || 0)),
    urgency: clamp(scores.urgency + (adjustments.urgency || 0)),
    farmerNeed: clamp(scores.farmerNeed + (adjustments.farmerNeed || 0)),
    pastResponse: clamp(scores.pastResponse + (adjustments.pastResponse || 0))
  };
}

function baseScores(context: SegmentContext) {
  const fitScores = context.product.cropFits.map((fit) => Number(fit.relevanceScore || 72));
  const productFit = clamp(avg(fitScores, 72));
  const hasCropMatchedFarmers = context.farmers.some((farmer) =>
    context.crops.some((crop) => crop.id === farmer.primaryCropId)
  );
  const regionalRelevance = context.region
    ? context.farmers.length
      ? 86
      : 62
    : context.regions.length > 1
      ? 78
      : 65;
  const cropStageRelevance = context.product.cropStageRelevance ? 84 : 58;
  const urgency = clamp(
    Math.max(
      avg(context.ecosystemConditions.map((entry) => severityScore(entry.riskLevel)), 55),
      avg(context.outbreaks.map((entry) => severityScore(entry.severity)), 55)
    )
  );
  const farmerNeed = clamp(
    58 +
      Math.min(18, context.farmers.filter((farmer) => Number(farmer.landSizeAcres || 0) <= 4).length * 5) +
      (hasCropMatchedFarmers ? 6 : 0) +
      (context.additionalInfo ? 8 : 0)
  );

  return {
    productFit,
    regionalRelevance,
    cropStageRelevance,
    urgency,
    farmerNeed,
    pastResponse: pastCampaignScore(context.campaigns)
  };
}

function segmentTemplate(params: {
  name: string;
  farmerPersona: string;
  regionLabel: string;
  cropLabel: string;
  estimatedFarmers: number;
  farmerNeed: string;
  productRelevance: string;
  ecosystemContext: string;
  trigger: string;
  priorityScore: number;
  dataConfidenceScore: number;
  whyCreated: string;
  tone: string;
  traits: string[];
  scoreInputs: ScoreInputs;
  dataConfidenceBreakdown: DataConfidenceBreakdown;
  product: ProductWithFits;
  additionalInfo?: string;
}): Segment {
  const note = params.additionalInfo ? ` Additional market context: ${params.additionalInfo}.` : "";

  return {
    name: params.name,
    summary: `${params.farmerPersona} in ${params.regionLabel} growing ${params.cropLabel}.${note}`,
    farmerPersona: params.farmerPersona,
    region: params.regionLabel,
    mainCrop: params.cropLabel,
    estimatedFarmers: params.estimatedFarmers,
    farmerNeed: params.farmerNeed,
    productRelevance: params.productRelevance,
    ecosystemContext: params.ecosystemContext,
    outbreakWeatherTrigger: params.trigger,
    priorityScore: params.priorityScore,
    dataConfidenceScore: params.dataConfidenceScore,
    whyCreated: params.whyCreated,
    scoreBreakdown: scoreBreakdown(params.scoreInputs),
    dataConfidenceBreakdown: params.dataConfidenceBreakdown,
    traits: params.traits,
    triggers: [
      params.trigger,
      params.product.cropStageRelevance
        ? `Crop-stage relevance: ${params.product.cropStageRelevance}`
        : "Crop-stage relevance requires planner validation",
      params.product.positioning || `${params.product.name} is relevant to ${params.product.category}`
    ],
    recommendedTone: params.tone
  };
}

export function buildSegments(context: SegmentContext): Segment[] {
  const { product, farmers, crops, ecosystemConditions, outbreaks, campaigns, additionalInfo } = context;
  const regionLabel = regionName(context.region, context.regions.length > 1 ? "Multi-region" : context.regions[0]?.state);
  const cropLabel = mainCropName(crops, farmers);
  const avgFarm = averageFarmSize(farmers);
  const baseCount = farmers.length || campaigns.reduce((sum, campaign) => sum + campaign.targets.length, 0) || 10;
  const scores = baseScores(context);
  const confidenceParams = {
    farmers,
    regions: context.regions,
    ecosystemConditions,
    outbreaks,
    campaigns
  };
  const confidence = dataConfidence(confidenceParams);
  const confidenceBreakdown = dataConfidenceBreakdown(confidenceParams);
  const latestWeather = ecosystemConditions[0];
  const latestOutbreak = outbreaks[0];
  const lowMechanizationCount = farmers.filter((farmer) =>
    farmer.farmingPractices.some((practice) => String(practice.mechanizationLevel || "").toLowerCase().includes("low")) ||
    !farmer.assets.some((asset) => asset.usableFlag)
  ).length;
  const retailerTrustCount = farmers.filter((farmer) => String(farmer.trustChannel || "").toLowerCase().includes("retailer")).length;
  const ecosystemContext = latestWeather
    ? `${latestWeather.weatherSummary || "Field"} conditions, ${latestWeather.riskLevel || "medium"} risk, ${latestWeather.rainfallMm ?? "N/A"}mm rainfall, ${latestWeather.humidityPercent ?? "N/A"}% humidity`
    : "No fresh ecosystem record available; using product and survey signals";
  const trigger = latestOutbreak
    ? `${latestOutbreak.severity || "Medium"} ${latestOutbreak.outbreakType.toLowerCase()} signal: ${latestOutbreak.outbreakName}`
    : `${latestWeather?.riskLevel || "Medium"} weather-risk signal for ${cropLabel}`;
  const productRelevance = `${product.name} fits ${cropLabel} through ${product.cropStageRelevance || "general crop-stage"} and ${product.targetPestType || product.category} relevance.`;
  const seedLike =
    product.category.toLowerCase().includes("seed") ||
    product.productType?.toLowerCase().includes("seed");
  const biharMaize =
    seedLike &&
    regionLabel.toLowerCase().includes("bihar") &&
    cropLabel.toLowerCase().includes("maize");

  const common = {
    regionLabel,
    cropLabel,
    product,
    productRelevance,
    ecosystemContext,
    trigger,
    dataConfidenceScore: confidence,
    dataConfidenceBreakdown: confidenceBreakdown,
    additionalInfo
  };

  if (biharMaize) {
    const segments = [
      segmentTemplate({
        ...common,
        name: "Smallholder Maize Stability Seekers",
        farmerPersona: "Smallholder maize farmers with low-to-medium acreage",
        estimatedFarmers: estimateFarmers(baseCount, 0.34),
        farmerNeed: "Need stable germination and reliable crop establishment under variable rainfall.",
        scoreInputs: withScoreAdjustments(scores, { farmerNeed: 6 }),
        priorityScore: scoreSegment({ ...withScoreAdjustments(scores, { farmerNeed: 6 }), offset: 2 }),
        whyCreated: "Seed category, Bihar region, maize fit, and small farm-size signals point to a stability-led persona.",
        tone: "Practical, reassuring and ROI-focused",
        traits: [`Average farm size around ${avgFarm.toFixed(1)} acres`, "Sensitive to input risk", "Needs clear sowing guidance"]
      }),
      segmentTemplate({
        ...common,
        name: "Progressive Maize Yield Planners",
        farmerPersona: "Progressive maize farmers willing to invest for better yield potential",
        estimatedFarmers: estimateFarmers(baseCount, 0.22),
        farmerNeed: "Need proof that premium seed choice can improve vigor and harvest value.",
        scoreInputs: withScoreAdjustments(scores, { productFit: 4 }),
        priorityScore: scoreSegment({ ...withScoreAdjustments(scores, { productFit: 4 }), offset: 1 }),
        whyCreated: "Product positioning and crop-fit data support a performance-led maize segment.",
        tone: "Confident, evidence-led and aspirational",
        traits: ["Responds to field proof", "Tracks yield upside", "Open to better genetics when risk is clear"]
      }),
      segmentTemplate({
        ...common,
        name: "Late Sowing Recovery Farmers",
        farmerPersona: "Farmers likely to face delayed sowing or uneven early crop establishment",
        estimatedFarmers: estimateFarmers(baseCount, 0.18),
        farmerNeed: "Need stronger early vigor and simple timing advice after delayed field preparation.",
        scoreInputs: withScoreAdjustments(scores, { cropStageRelevance: 6, urgency: 4 }),
        priorityScore: scoreSegment(withScoreAdjustments(scores, { cropStageRelevance: 6, urgency: 4 })),
        whyCreated: "Weather context and seed-stage relevance indicate a time-sensitive sowing persona.",
        tone: "Urgent, clear and action-oriented",
        traits: ["Late sowing risk", "Needs simple crop-stage guidance", "Benefits from quick retailer confirmation"]
      }),
      segmentTemplate({
        ...common,
        name: "Low Mechanization Maize Growers",
        farmerPersona: "Farmers with limited equipment access and higher dependency on manual operations",
        estimatedFarmers: estimateFarmers(baseCount, 0.16),
        farmerNeed: "Need seed choices and guidance that reduce operational complexity.",
        scoreInputs: withScoreAdjustments(scores, { farmerNeed: lowMechanizationCount ? 6 : 4 }),
        priorityScore: scoreSegment(withScoreAdjustments(scores, { farmerNeed: lowMechanizationCount ? 6 : 4 })),
        whyCreated: "Farming practice and asset availability signals support a low-mechanization segment without using selected channel or influencer inputs.",
        tone: "Simple, grounded and support-led",
        traits: ["Limited equipment access", "Needs low-complexity recommendations", "Values field support"]
      }),
      segmentTemplate({
        ...common,
        name: "Retailer-Dependent Maize Buyers",
        farmerPersona: "Farmers who rely on local retailer advice before purchasing seed",
        estimatedFarmers: estimateFarmers(baseCount, 0.2),
        farmerNeed: "Need local retailer validation and simple proof before buying.",
        scoreInputs: withScoreAdjustments(scores, { regionalRelevance: retailerTrustCount ? 6 : 4 }),
        priorityScore: scoreSegment(withScoreAdjustments(scores, { regionalRelevance: retailerTrustCount ? 6 : 4 })),
        whyCreated: "Survey trust-channel and campaign learning signals indicate retailer confirmation will matter after segmentation.",
        tone: "Trust-building, local and proof-led",
        traits: ["Acts after local recommendation", "Needs retailer confirmation", "Prefers practical examples over broad claims"]
      })
    ];

    return segments.sort((a, b) => b.priorityScore - a.priorityScore || a.name.localeCompare(b.name));
  }

  const segments = [
    segmentTemplate({
      ...common,
      name: "High-Urgency Crop Protection Farmers",
      farmerPersona: "Farmers facing visible pest, disease, weed, or stress risk",
      estimatedFarmers: estimateFarmers(baseCount, 0.3),
      farmerNeed: "Need fast, context-aware guidance before crop damage spreads.",
      scoreInputs: withScoreAdjustments(scores, { urgency: 6 }),
      priorityScore: scoreSegment({ ...withScoreAdjustments(scores, { urgency: 6 }), offset: 2 }),
      whyCreated: "Product threat fit, outbreak/weather context, and crop-stage relevance indicate urgent activation potential.",
      tone: "Urgent, agronomic and direct",
      traits: [`Average farm size around ${avgFarm.toFixed(1)} acres`, "Responds to visible field risk", "Needs timely intervention"]
    }),
    segmentTemplate({
      ...common,
      name: "Progressive Yield Maximizers",
      farmerPersona: "Growers looking to improve output and justify input spend",
      estimatedFarmers: estimateFarmers(baseCount, 0.24),
      farmerNeed: "Need proof that the product improves field outcomes and protects ROI.",
      scoreInputs: withScoreAdjustments(scores, { productFit: 5 }),
      priorityScore: scoreSegment(withScoreAdjustments(scores, { productFit: 5 })),
      whyCreated: "Product fit scores and past response signals support a performance-led persona.",
      tone: "Confident, data-led and commercially practical",
      traits: ["Responds to performance proof", "Tracks input cost vs. harvest value", "Open to demo-led adoption"]
    }),
    segmentTemplate({
      ...common,
      name: "Risk-Averse Retailer-Led Farmers",
      farmerPersona: "Farmers who adopt only after trusted local confirmation",
      estimatedFarmers: estimateFarmers(baseCount, 0.22),
      farmerNeed: "Need low-risk messaging, retailer validation, and clear usage guidance.",
      scoreInputs: withScoreAdjustments(scores, { farmerNeed: 4 }),
      priorityScore: scoreSegment(withScoreAdjustments(scores, { farmerNeed: 4 })),
      whyCreated: "Survey trust signals and campaign history indicate local validation is likely a purchase gate.",
      tone: "Assuring, plain-spoken and locally grounded",
      traits: ["Prefers familiar advice channels", "Cautious about new input choices", "Values clear instructions"]
    }),
    segmentTemplate({
      ...common,
      name: "Weather-Risk Smallholders",
      farmerPersona: "Smaller-acreage farmers exposed to weather-driven yield risk",
      estimatedFarmers: estimateFarmers(baseCount, 0.18),
      farmerNeed: "Need resilient, affordable recommendations tied to current ecosystem risk.",
      scoreInputs: withScoreAdjustments(scores, { urgency: 3, farmerNeed: 5 }),
      priorityScore: scoreSegment(withScoreAdjustments(scores, { urgency: 3, farmerNeed: 5 })),
      whyCreated: "Weather freshness, regional conditions, and smaller farm-size signals point to a resilience persona.",
      tone: "Practical, empathetic and risk-aware",
      traits: ["Smaller acreage", "Sensitive to weather risk", "Needs affordable next steps"]
    }),
    segmentTemplate({
      ...common,
      name: "Demo-Ready Community Influencers",
      farmerPersona: "Early movers who can influence nearby growers through visible field results",
      estimatedFarmers: estimateFarmers(baseCount, 0.12),
      farmerNeed: "Need strong proof points and shareable field success stories.",
      scoreInputs: withScoreAdjustments(scores, { pastResponse: 5 }),
      priorityScore: scoreSegment(withScoreAdjustments(scores, { pastResponse: 5 })),
      whyCreated: "Past response, product positioning, and regional crop fit support a smaller amplification segment.",
      tone: "Aspirational, field-first and proof-led",
      traits: ["Influences peer conversations", "Open to demonstration", "Amplifies local success stories"]
    })
  ];

  return segments.sort((a, b) => b.priorityScore - a.priorityScore || a.name.localeCompare(b.name));
}
