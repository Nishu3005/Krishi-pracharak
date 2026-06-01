import type { Campaign, CampaignResponse, CampaignTarget, Influencer, Product } from "@prisma/client";

import type { GeneratedCampaign, Segment } from "@/lib/types";

type GenerationSegment = Pick<
  Segment,
  | "name"
  | "summary"
  | "farmerPersona"
  | "region"
  | "mainCrop"
  | "farmerNeed"
  | "productRelevance"
  | "ecosystemContext"
  | "outbreakWeatherTrigger"
  | "priorityScore"
  | "dataConfidenceScore"
  | "whyCreated"
  | "traits"
  | "triggers"
  | "recommendedTone"
>;

type PreviousCampaign = Campaign & {
  targets: Array<CampaignTarget & { response: CampaignResponse | null }>;
};

type GeneratorContext = {
  product: Product;
  segment: GenerationSegment;
  region?: string;
  channel?: string;
  influencer?: Influencer | null;
  additionalInfo?: string;
  previousCampaigns?: PreviousCampaign[];
};

type PromptSet = {
  campaignBrief: string;
  whatsapp: string;
  sms: string;
  voiceScript: string;
  videoScript: string;
  imagePrompt: string;
  influencerScript: string;
  fieldRepScript: string;
  retailerScript: string;
};

function clamp(value: number, min = 0, max = 100) {
  return Math.max(min, Math.min(max, Math.round(value)));
}

function ratioPercent(numerator: number, denominator: number) {
  if (!denominator) return 0;
  return Math.round((numerator / denominator) * 100);
}

function previousPerformance(campaigns: PreviousCampaign[] = []) {
  const targets = campaigns.flatMap((campaign) => campaign.targets);
  const responses = targets.map((target) => target.response).filter(Boolean);
  const engagementCount = responses.filter(
    (response) => response?.openedFlag || response?.clickedFlag || response?.repliedFlag
  ).length;
  const inquiryCount = responses.filter((response) => response?.inquiryFlag).length;
  const conversionCount = responses.filter((response) => response?.purchaseFlag).length;

  return {
    campaignCount: campaigns.length,
    targetCount: targets.length,
    engagementRate: ratioPercent(engagementCount, targets.length),
    inquiryRate: ratioPercent(inquiryCount, targets.length),
    conversionRate: ratioPercent(conversionCount, targets.length)
  };
}

function channelLabel(channel?: string) {
  return channel && channel !== "All" ? channel : "multi-channel outreach";
}

function selectedRegion(context: GeneratorContext) {
  return context.region || context.segment.region || "high-priority markets";
}

function influencerLine(influencer?: Influencer | null) {
  if (!influencer) {
    return "No named influencer selected; lean on retailer trust, field proof, and safe-use guidance.";
  }

  return `${influencer.name} can reinforce the message through ${influencer.channel} with a ${influencer.contentFormat || "short advisory"} format.`;
}

function createPromptSet(context: GeneratorContext): PromptSet {
  const { product, segment, influencer, additionalInfo } = context;
  const regionLabel = selectedRegion(context);
  const stage = product.cropStageRelevance || "the current crop stage";
  const threat = product.targetPestType || product.category || "seasonal crop risk";
  const performance = previousPerformance(context.previousCampaigns);
  const historyLine = performance.campaignCount
    ? `Previous ${product.name} campaigns show ${performance.engagementRate}% engagement and ${performance.inquiryRate}% inquiry.`
    : "No previous campaign response is available, so use conservative expected metrics.";
  const plannerLine = additionalInfo ? `Planner context: ${additionalInfo}.` : "No extra planner context supplied.";
  const sharedContext = [
    `Product: ${product.name} (${product.category}).`,
    `Segment: ${segment.name} - ${segment.farmerPersona}.`,
    `Region: ${regionLabel}. Main crop: ${segment.mainCrop}.`,
    `Need: ${segment.farmerNeed}`,
    `Ecosystem: ${segment.ecosystemContext}`,
    `Trigger: ${segment.outbreakWeatherTrigger}`,
    `Tone: ${segment.recommendedTone}. Channel: ${channelLabel(context.channel)}.`,
    historyLine,
    plannerLine,
    influencerLine(influencer)
  ].join(" ");

  return {
    campaignBrief: `${sharedContext} Create compliant, farmer-friendly campaign assets that avoid dosage, cure, guaranteed yield, competitor attack, and unsupported scientific claims.`,
    whatsapp: `${sharedContext} Write a concise WhatsApp advisory with local relevance, product fit, and retailer/field-rep CTA.`,
    sms: `${sharedContext} Write a short SMS under 160 characters with product, risk, stage, and CTA.`,
    voiceScript: `${sharedContext} Write a 25-35 second voice call script in plain advisory language.`,
    videoScript: `${sharedContext} Write a short video script with scene flow, proof point, CTA, and safe-use reminder.`,
    imagePrompt: `${sharedContext} Write an image concept prompt for a professional agricultural campaign visual.`,
    influencerScript: `${sharedContext} Write an influencer delivery script using the selected influencer if available.`,
    fieldRepScript: `${sharedContext} Write field rep talking points for in-person follow-up.`,
    retailerScript: `${sharedContext} Write retailer nudge copy for purchase inquiry conversations.`
  };
}

function safeUseLine(product: Product) {
  const stage = product.cropStageRelevance || "the current crop stage";
  return `Confirm fit for ${stage} and follow the approved label or field-rep guidance.`;
}

function generateWhatsAppContent(context: GeneratorContext, prompt: string) {
  const { product, segment, additionalInfo } = context;
  const regionLabel = selectedRegion(context);
  const plannerNote = additionalInfo ? `\nPlanner note: ${additionalInfo}` : "";

  return `Namaste. ${product.name} update for ${regionLabel}: ${segment.name} are seeing ${segment.outbreakWeatherTrigger.toLowerCase()}. ${segment.productRelevance} ${safeUseLine(product)} Ask your retailer or field rep for the right next step this week.${plannerNote}`;
}

function generateSmsContent(context: GeneratorContext, prompt: string) {
  const { product, segment } = context;
  const stage = product.cropStageRelevance || "current stage";
  const risk = product.targetPestType || segment.mainCrop;

  return `${product.name}: relevant for ${risk} at ${stage}. Ask retailer/field rep if it fits your field this week.`;
}

function generateVoiceScript(context: GeneratorContext, prompt: string) {
  const { product, segment } = context;
  const regionLabel = selectedRegion(context);

  return `Namaskar. This is a crop advisory for ${regionLabel}. For ${segment.name.toLowerCase()}, current field signals show ${segment.outbreakWeatherTrigger.toLowerCase()}. ${product.name} may be relevant where the crop stage and field condition match. Please speak with your retailer or field representative before taking action.`;
}

function generateVideoScript(context: GeneratorContext, prompt: string) {
  const { product, segment } = context;

  return `Scene 1: Show a ${segment.mainCrop} field in ${selectedRegion(context)}.\nScene 2: Farmer explains the need: ${segment.farmerNeed}\nScene 3: Field rep connects the risk to ${product.name}: ${segment.productRelevance}\nScene 4: Show retailer/field-rep discussion and safe-use reminder.\nClose: Book a field check or retailer conversation this week.`;
}

function generateImagePrompt(context: GeneratorContext, prompt: string) {
  const { product, segment } = context;

  return `Professional agricultural campaign visual for ${product.name}; ${segment.mainCrop} farmers in ${selectedRegion(context)}; show field context, retailer guidance, product-fit cue, ${segment.recommendedTone.toLowerCase()} tone, clean Syngenta-style green and white layout, no dosage or guaranteed yield claim.`;
}

function generateInfluencerScript(context: GeneratorContext, prompt: string) {
  const { product, segment, influencer } = context;
  const speaker = influencer ? influencer.name : "Local trusted agronomy voice";
  const format = influencer?.contentFormat || influencer?.channel || "short advisory";

  return `${speaker} ${format}: "Farmers in the ${segment.name.toLowerCase()} group are dealing with ${segment.outbreakWeatherTrigger.toLowerCase()}. ${product.name} is worth discussing where your crop stage and field condition match. I recommend checking with your retailer or field rep for approved guidance before purchase or use."`;
}

function generateFieldRepScript(context: GeneratorContext, prompt: string) {
  const { product, segment } = context;

  return [
    `Prioritize ${segment.name.toLowerCase()} in ${selectedRegion(context)}.`,
    `Ask about crop stage, recent weather stress, and visible field symptoms.`,
    `Explain product fit: ${segment.productRelevance}`,
    `Avoid yield guarantees; use field suitability and approved guidance only.`,
    `Record inquiry intent and retailer follow-up requirement.`
  ].join("\n");
}

function generateRetailerScript(context: GeneratorContext, prompt: string) {
  const { product, segment } = context;

  return `When ${segment.mainCrop} farmers ask about ${segment.outbreakWeatherTrigger.toLowerCase()}, connect the concern to their crop stage and explain where ${product.name} fits. Offer a simple next step: field-rep callback, demo request, or approved product guidance.`;
}

function runComplianceGuardrail(text: string, additionalInfo?: string): GeneratedCampaign["compliance"] {
  const normalized = `${text} ${additionalInfo || ""}`
    .toLowerCase()
    .replace(/avoid yield guarantees?/g, "")
    .replace(/avoid dosage, cure, guaranteed yield, competitor attack, and unsupported scientific claims/g, "")
    .replace(/no dosage or guaranteed yield claim/g, "")
    .replace(/without guaranteed yield claims?/g, "");
  const blockedRules = [
    { pattern: /\bguarantee[ds]?\b.*\byield\b|\byield\b.*\bguarantee[ds]?\b/, note: "Guaranteed yield claims are not allowed." },
    { pattern: /\bcure[sd]?\b.*\bdisease\b|\bdisease\b.*\bcure[sd]?\b/, note: "False disease cure claims are not allowed." },
    { pattern: /\bunsafe\b.*\bpesticide\b|\bno safety\b|\bno protective\b/, note: "Unsafe pesticide claims are not allowed." },
    { pattern: /\bcompetitor\b.*\b(bad|fake|useless|harmful|inferior)\b/, note: "Competitor attacks are not allowed." }
  ];
  const warningRules = [
    { pattern: /\b\d+\s?(ml|g|kg|litre|liter|l|gm)\b/, note: "Potential unapproved dosage language detected." },
    { pattern: /\bscientifically proven\b|\b100%\b|\bbest in market\b/, note: "Unsupported scientific or superiority claim detected." },
    { pattern: /\bhighest yield\b|\bdouble yield\b/, note: "Yield uplift language needs substantiation." }
  ];
  const blocked = blockedRules.filter((rule) => rule.pattern.test(normalized)).map((rule) => rule.note);
  const warnings = warningRules.filter((rule) => rule.pattern.test(normalized)).map((rule) => rule.note);

  if (blocked.length) {
    return {
      status: "Blocked",
      notes: blocked
    };
  }

  if (warnings.length) {
    return {
      status: "Warning",
      notes: warnings
    };
  }

  return {
    status: "Passed",
    notes: [
      "No dosage, guaranteed yield, unsafe pesticide, disease cure, competitor attack, or unsupported scientific claim detected.",
      "Content keeps CTA to retailer or field-rep guidance."
    ]
  };
}

function expectedPerformance(context: GeneratorContext): GeneratedCampaign["expectedPerformance"] {
  const performance = previousPerformance(context.previousCampaigns);
  const priority = context.segment.priorityScore || 65;
  const confidence = context.segment.dataConfidenceScore || 65;
  const influencerReach = context.influencer?.reachScore || context.influencer?.followerCount || 0;
  const segmentReach = Math.max(context.segment.priorityScore * 18, context.influencer ? influencerReach : 0, 500);
  const engagementBase = performance.engagementRate || 18;
  const inquiryBase = performance.inquiryRate || 6;
  const conversionBase = performance.conversionRate || 2;

  return {
    predictedReach: Math.round(segmentReach),
    expectedEngagement: clamp(engagementBase + priority * 0.18 + confidence * 0.05, 5, 75),
    expectedInquiryRate: clamp(inquiryBase + priority * 0.08, 2, 45),
    expectedConversion: clamp(conversionBase + priority * 0.035, 1, 25),
    expectedUpliftOverGeneric: clamp(8 + priority * 0.18 + (context.additionalInfo ? 4 : 0), 8, 42)
  };
}

function orchestrateGeneration(context: GeneratorContext, prompts: PromptSet): GeneratedCampaign["content"] {
  return {
    whatsapp: generateWhatsAppContent(context, prompts.whatsapp),
    sms: generateSmsContent(context, prompts.sms),
    voiceScript: generateVoiceScript(context, prompts.voiceScript),
    videoScript: generateVideoScript(context, prompts.videoScript),
    imagePrompt: generateImagePrompt(context, prompts.imagePrompt),
    influencerScript: generateInfluencerScript(context, prompts.influencerScript),
    fieldRepScript: generateFieldRepScript(context, prompts.fieldRepScript),
    retailerScript: generateRetailerScript(context, prompts.retailerScript)
  };
}

export function generateCampaignContent(params: GeneratorContext): GeneratedCampaign {
  const { product, segment, influencer } = params;
  const regionLabel = selectedRegion(params);
  const prompts = createPromptSet(params);
  const content = orchestrateGeneration(params, prompts);
  const allGeneratedText = Object.values(content).join("\n\n");
  const compliance = runComplianceGuardrail(allGeneratedText, params.additionalInfo);
  const performance = expectedPerformance(params);
  const selectedChannel = channelLabel(params.channel);

  return {
    campaignBrief: prompts.campaignBrief,
    hook: `${segment.name} in ${regionLabel}: move from field need to inquiry with ${product.name}.`,
    headline: `${product.name} for ${segment.name.toLowerCase()}`,
    body: [
      `${product.name} is positioned for ${segment.mainCrop} growers where ${segment.outbreakWeatherTrigger.toLowerCase()} is shaping urgency.`,
      `The selected segment needs: ${segment.farmerNeed}`,
      `Use ${selectedChannel} with a ${segment.recommendedTone.toLowerCase()} tone.`,
      influencerLine(influencer)
    ].join(" "),
    callToAction: `Prompt farmers to request a retailer conversation or field demo for ${product.name} this week.`,
    content,
    compliance,
    expectedPerformance: performance,
    chat: [
      `Prompt Generator: Created prompts for WhatsApp, SMS, voice, video, image, influencer, field rep, and retailer assets.`,
      `Agentic AI Orchestrator: Delegated prompts to eight rule-based generator functions.`,
      `Generative AI Simulation: Built content from product, region, segment, channel, influencer, additional info, ecosystem trigger, and campaign history.`,
      `Compliance Guardrail: ${compliance.status}. ${compliance.notes.join(" ")}`
    ]
  };
}
