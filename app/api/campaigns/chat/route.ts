import { NextResponse } from "next/server";
import { z } from "zod";

import { prisma } from "@/lib/prisma";

const chatSchema = z.object({
  productId: z.coerce.number().int().positive().optional(),
  region: z.string().optional(),
  channel: z.string().optional(),
  influencerId: z.coerce.number().int().positive().optional().or(z.literal("")),
  additionalInfo: z.string().optional(),
  segment: z
    .object({
      name: z.string(),
      farmerPersona: z.string().optional(),
      region: z.string().optional(),
      mainCrop: z.string().optional(),
      farmerNeed: z.string().optional(),
      productRelevance: z.string().optional(),
      ecosystemContext: z.string().optional(),
      outbreakWeatherTrigger: z.string().optional(),
      priorityScore: z.number().optional(),
      dataConfidenceScore: z.number().optional(),
      whyCreated: z.string().optional(),
      scoreBreakdown: z
        .object({
          productFit: z.number(),
          regionalRelevance: z.number(),
          cropStageRelevance: z.number(),
          weatherOutbreakUrgency: z.number(),
          farmerNeed: z.number(),
          pastCampaignResponse: z.number()
        })
        .optional()
    })
    .optional(),
  expectedPerformance: z
    .object({
      predictedReach: z.number(),
      expectedEngagement: z.number(),
      expectedInquiryRate: z.number(),
      expectedConversion: z.number(),
      expectedUpliftOverGeneric: z.number()
    })
    .optional(),
  compliance: z
    .object({
      status: z.enum(["Passed", "Warning", "Blocked"]),
      notes: z.array(z.string())
    })
    .optional(),
  question: z.string().min(2)
});

function pct(value: number, total: number) {
  if (!total) {
    return 0;
  }
  return Math.round((value / total) * 100);
}

function regionLabel(region?: { state: string; district: string | null } | null) {
  if (!region) {
    return "all selected regions";
  }
  return region.district ? `${region.state}/${region.district}` : region.state;
}

function bestChannel(params: {
  selectedChannel?: string;
  whatsappOptIn: number;
  smartphoneFarmers: number;
  farmers: number;
  retailerTrust: number;
}) {
  if (params.selectedChannel && params.selectedChannel !== "All") {
    return params.selectedChannel;
  }
  if (params.whatsappOptIn >= Math.max(1, params.farmers / 2) || params.smartphoneFarmers >= Math.max(1, params.farmers / 2)) {
    return "WhatsApp";
  }
  if (params.retailerTrust > 0) {
    return "Retailer + field rep follow-up";
  }
  return "SMS + voice";
}

export async function POST(request: Request) {
  const json = await request.json();
  const parsed = chatSchema.safeParse(json);

  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid request." }, { status: 400 });
  }

  const selectedRegion = parsed.data.region
    ? await prisma.region.findFirst({ where: { state: parsed.data.region } })
    : null;

  const [product, farmers, campaigns, retailers, influencer] = await Promise.all([
    parsed.data.productId
      ? prisma.product.findUnique({
          where: { id: parsed.data.productId },
          include: { cropFits: { include: { crop: true } } }
        })
      : Promise.resolve(null),
    prisma.farmer.findMany({
      where: { regionId: selectedRegion?.id },
      include: {
        primaryCrop: true,
        preferredLanguage: true,
        channelPreferences: true
      },
      take: 100
    }),
    prisma.campaign.findMany({
      where: {
        productId: parsed.data.productId,
        regionId: selectedRegion?.id
      },
      include: {
        product: true,
        crop: true,
        region: true,
        targets: { include: { response: true } },
        influencerCampaigns: { include: { influencer: true } }
      },
      orderBy: { id: "desc" },
      take: 5
    }),
    prisma.retailer.findMany({
      where: { regionId: selectedRegion?.id },
      orderBy: { influenceScore: "desc" },
      take: 5
    }),
    typeof parsed.data.influencerId === "number"
      ? prisma.influencer.findUnique({ where: { id: parsed.data.influencerId } })
      : Promise.resolve(null)
  ]);

  const question = parsed.data.question.toLowerCase();
  const segment = parsed.data.segment;
  const expected = parsed.data.expectedPerformance;
  const targetCount = campaigns.reduce((sum, campaign) => sum + campaign.targets.length, 0);
  const responses = campaigns.flatMap((campaign) => campaign.targets.map((target) => target.response).filter(Boolean));
  const engagement = responses.filter((response) => response?.openedFlag || response?.clickedFlag || response?.repliedFlag).length;
  const inquiries = responses.filter((response) => response?.inquiryFlag).length;
  const cropNames = product?.cropFits.map((fit) => fit.crop.name).filter(Boolean) ?? [];
  const smartphoneFarmers = farmers.filter((farmer) => farmer.smartphoneUser).length;
  const retailerTrust = farmers.filter((farmer) => farmer.trustChannel?.toLowerCase().includes("retailer")).length;
  const whatsappOptIn = farmers.filter((farmer) => farmer.channelPreferences.some((pref) => pref.whatsappOptIn)).length;
  const place = regionLabel(selectedRegion);
  const productName = product?.name ?? "the selected product";
  const selectedChannel = parsed.data.channel || "the best-fit channel";
  const recommendedChannel = bestChannel({
    selectedChannel: parsed.data.channel,
    whatsappOptIn,
    smartphoneFarmers,
    farmers: farmers.length,
    retailerTrust
  });

  let answer = "";

  if (question.includes("why") && question.includes("segment")) {
    answer = segment
      ? `${segment.name} was selected because ${segment.whyCreated || "the product, region, crop, farmer need, and risk signals aligned"}. For ${productName} in ${segment.region || place}, the main need is: ${segment.farmerNeed || "localized campaign relevance"}. Priority is ${segment.priorityScore ?? "not scored"} and data confidence is ${segment.dataConfidenceScore ?? "not scored"}.`
      : "Create segments first so I can explain the selected persona using product fit, regional relevance, crop-stage relevance, urgency, farmer need, and past response.";
  } else if (question.includes("priority") || question.includes("score calculated")) {
    const breakdown = segment?.scoreBreakdown;
    answer = breakdown
      ? `Priority score uses Product Fit 25%, Regional Relevance 20%, Crop Stage Relevance 20%, Weather/Outbreak Urgency 15%, Farmer Need 10%, and Past Campaign Response 10%. For ${segment?.name}, inputs are product fit ${breakdown.productFit}, region ${breakdown.regionalRelevance}, crop stage ${breakdown.cropStageRelevance}, urgency ${breakdown.weatherOutbreakUrgency}, need ${breakdown.farmerNeed}, and past response ${breakdown.pastCampaignResponse}.`
      : "Priority score uses Product Fit 25%, Regional Relevance 20%, Crop Stage Relevance 20%, Weather/Outbreak Urgency 15%, Farmer Need 10%, and Past Campaign Response 10%. Create segments to see the exact score inputs.";
  } else if (question.includes("channel")) {
    answer = segment
      ? `Best channel for ${segment.name} is ${recommendedChannel}. In ${place}, ${smartphoneFarmers}/${farmers.length} farmer profiles are smartphone users, ${whatsappOptIn} have WhatsApp opt-in, and ${retailerTrust} show retailer trust. Use channel only for activation; the segment itself was created without channel influence.`
      : `Best-fit channel is ${recommendedChannel}. This is based on available farmer device, WhatsApp opt-in, and retailer-trust signals for ${place}.`;
  } else if (question.includes("expected") || question.includes("inquiry") || question.includes("performance")) {
    answer = expected
      ? `Expected performance: predicted reach ${expected.predictedReach.toLocaleString("en-IN")}, engagement ${expected.expectedEngagement}%, inquiry rate ${expected.expectedInquiryRate}%, conversion ${expected.expectedConversion}%, and uplift over a generic campaign ${expected.expectedUpliftOverGeneric}%.`
      : campaigns.length
        ? `No generated prediction is active yet. Historical benchmark for this context is ${pct(engagement, targetCount)}% engagement and ${pct(inquiries, targetCount)}% inquiry across ${targetCount} target(s).`
        : "Generate content for a segment to calculate predicted reach, engagement, inquiry, conversion, and uplift.";
  } else if (question.includes("risk")) {
    const compliance = parsed.data.compliance;
    answer = [
      segment?.outbreakWeatherTrigger ? `Field risk: ${segment.outbreakWeatherTrigger}.` : `Field risk should be validated for ${place}.`,
      segment?.ecosystemContext ? `Ecosystem context: ${segment.ecosystemContext}.` : null,
      compliance ? `Compliance status is ${compliance.status}: ${compliance.notes.join(" ")}` : "Compliance will be checked after generation.",
      "Messaging risk: avoid dosage, guaranteed yield, disease cure, competitor attack, and unsupported scientific claims."
    ]
      .filter(Boolean)
      .join(" ");
  } else if (question.includes("product")) {
    answer = product
      ? `${product.name} is a ${product.category}${product.productType ? ` (${product.productType})` : ""}. It is strongest for ${cropNames.join(", ") || "mapped crop contexts"} and is positioned around ${product.positioning || product.targetPestType || "field relevance"}. For ${place}, use crop-stage fit (${product.cropStageRelevance || "not specified"}) and threat fit (${product.targetPestType || "not specified"}) before scaling the campaign.`
      : "Select a product first so I can ground the strategy in product category, crop fit, crop stage, and threat relevance.";
  } else if (question.includes("previous") || question.includes("campaign") || question.includes("history")) {
    answer = campaigns.length
      ? `I found ${campaigns.length} recent campaign record(s) for this context. Across ${targetCount} targets, simulated engagement is ${pct(engagement, targetCount)}% and inquiry is ${pct(inquiries, targetCount)}%. The latest campaign is "${campaigns[0].name}" with status "${campaigns[0].status}". Use this as a benchmark, not as a final prediction.`
      : `No previous campaign history is available for ${productName} in ${place}. Start with a conservative pilot, capture responses, then use the learning loop to improve the next campaign.`;
  } else if (question.includes("retailer")) {
    answer = retailers.length
      ? `Top retailer signal in ${place}: ${retailers.map((retailer) => `${retailer.name}${retailer.influenceScore ? ` (${retailer.influenceScore}/100 influence)` : ""}`).join(", ")}. Since ${retailerTrust} farmer(s) in the current data trust retailers, retailer scripts and callback tracking should be included.`
      : `No retailer records are available for ${place}. If retailer influence is important, upload or add retailer data before depending on retailer-led conversion.`;
  } else if (question.includes("farmer") || question.includes("segment")) {
    answer = `The selected context has ${farmers.length} farmer profile(s). ${smartphoneFarmers} use smartphones, ${whatsappOptIn} have WhatsApp opt-in, and ${retailerTrust} show retailer trust. Segment strategy should separate progressive digital growers from risk-averse retailer-led farmers.`;
  } else if (question.includes("influencer")) {
    const regionalInfluencers = await prisma.influencer.findMany({
      where: { regionId: selectedRegion?.id },
      orderBy: [{ trustScore: "desc" }, { reachScore: "desc" }],
      take: 3
    });
    answer = influencer
      ? `${influencer.name} can support ${productName} through ${influencer.channel}. Use them after segmentation for testimonial, demo, or reminder content. Their trust score is ${influencer.trustScore ?? "not scored"} and estimated reach is ${influencer.reachScore ?? "not available"}.`
      : regionalInfluencers.length
        ? `Best influencer options for ${place}: ${regionalInfluencers.map((entry) => `${entry.name} (${entry.channel}, trust ${entry.trustScore ?? "N/A"}, reach ${entry.reachScore ?? "N/A"})`).join("; ")}. Select one before Generate if you want influencer-specific scripts.`
        : `No influencer is selected and no regional influencer records are available for ${place}. Add influencer data or run product-led content through retailer and field rep channels.`;
  } else if (question.includes("field rep") || question.includes("field") || question.includes("suggestion")) {
    answer = segment
      ? `Field reps should prioritize ${segment.name}, ask about ${segment.mainCrop || "crop"} stage and visible risk, explain ${segment.productRelevance || `${productName} fit`}, then capture inquiry intent and retailer callback needs.`
      : `Field reps should validate crop stage, field symptoms, farmer trust channel, and retailer follow-up before scaling ${productName}.`;
  } else {
    answer = `Recommended strategy: use ${productName} for the strongest crop-fit audience in ${place}, keep ${selectedChannel} as the activation layer, and validate the message against farmer trust channels. ${segment ? `Current segment: ${segment.name}. ` : ""}${parsed.data.additionalInfo ? `Planner context considered: ${parsed.data.additionalInfo}` : "Add market or outbreak context if you want a sharper recommendation."}`;
  }

  return NextResponse.json({
    answer,
    context: {
      farmers: farmers.length,
      campaigns: campaigns.length,
      retailers: retailers.length,
      product: product?.name ?? null
    }
  });
}
