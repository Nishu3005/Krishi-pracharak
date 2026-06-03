import { validateLlmSegmentationResponse } from "@/lib/ai/schema-guard";
import { callTokenRouterJson } from "@/lib/ai/tokenrouter-client";
import type { Segment } from "@/lib/types";

type GenerateSegmentsInput = {
  selectedProduct: unknown;
  selectedRegion?: unknown;
  additionalInfo?: string;
  databaseContext: unknown;
};

const SEGMENTATION_JSON_SCHEMA_DESCRIPTION = `{
  "overallStrategy": "string",
  "segments": [
    {
      "segmentName": "string",
      "farmerPersona": "string",
      "region": "string",
      "mainCrop": "string",
      "estimatedFarmers": 0,
      "farmerNeed": "string",
      "productRelevance": "string",
      "ecosystemContext": "string",
      "weatherOrOutbreakTrigger": "string",
      "priorityScore": 0,
      "dataConfidenceScore": 0,
      "whyThisSegment": ["string"],
      "recommendedNextAction": "string"
    }
  ],
  "dataGaps": ["string"],
  "assumptions": ["string"]
}`;

const SYSTEM_PROMPT = `You are a farmer segmentation AI for an agricultural marketing intelligence platform.
Create 3 to 6 farmer persona segments using only product, crop, farmer, ecosystem, outbreak, language, campaign history, and planner context provided.
Do not use selected channel for segmentation.
Do not use selected influencer for segmentation.
Channel and influencer are used later for content generation, not segment creation.
priorityScore must be 0-100.
dataConfidenceScore must be 0-100.
If data is weak, mention it in dataGaps.
Do not invent exact farmer counts; estimate based on available database context.
Return JSON only.
No markdown.
No explanation outside JSON.`;

function compactInputSummary(input: GenerateSegmentsInput) {
  const product = input.selectedProduct as { name?: string; id?: number } | null;
  const region = input.selectedRegion as { state?: string; district?: string } | null | undefined;
  return JSON.stringify({
    feature: "segmentation",
    product: product?.name || product?.id || "unknown",
    region: region?.state || "all",
    additionalInfo: input.additionalInfo ? "provided" : "not provided"
  });
}

function segmentToAppShape(segment: ReturnType<typeof validateLlmSegmentationResponse>["segments"][number]): Segment {
  return {
    name: segment.segmentName,
    summary: `${segment.farmerPersona} in ${segment.region} growing ${segment.mainCrop}.`,
    farmerPersona: segment.farmerPersona,
    region: segment.region,
    mainCrop: segment.mainCrop,
    estimatedFarmers: segment.estimatedFarmers,
    farmerNeed: segment.farmerNeed,
    productRelevance: segment.productRelevance,
    ecosystemContext: segment.ecosystemContext,
    outbreakWeatherTrigger: segment.weatherOrOutbreakTrigger,
    priorityScore: segment.priorityScore,
    dataConfidenceScore: segment.dataConfidenceScore,
    whyCreated: segment.whyThisSegment.join(" "),
    whyThisSegment: segment.whyThisSegment,
    recommendedNextAction: segment.recommendedNextAction,
    traits: segment.whyThisSegment.slice(0, 4),
    triggers: [segment.weatherOrOutbreakTrigger],
    recommendedTone: segment.priorityScore >= 80 ? "Urgent advisory" : "Consultative"
  };
}

export async function generateSegmentsWithTokenRouter(input: GenerateSegmentsInput) {
  const userPrompt = `Generate farmer segments for this campaign planning context.

Selected product:
${JSON.stringify(input.selectedProduct, null, 2)}

Selected region:
${JSON.stringify(input.selectedRegion ?? null, null, 2)}

Additional planner information:
${input.additionalInfo || "None"}

Database context:
${JSON.stringify(input.databaseContext, null, 2)}`;

  const result = await callTokenRouterJson<ReturnType<typeof validateLlmSegmentationResponse>>({
    systemPrompt: SYSTEM_PROMPT,
    userPrompt,
    jsonSchemaDescription: SEGMENTATION_JSON_SCHEMA_DESCRIPTION,
    featureName: "segmentation",
    inputSummary: compactInputSummary(input)
  });

  const response = validateLlmSegmentationResponse(result.parsed);
  return {
    overallStrategy: response.overallStrategy,
    dataGaps: response.dataGaps,
    assumptions: response.assumptions,
    segments: response.segments.map(segmentToAppShape),
    rawText: result.rawText,
    metadata: result.metadata
  };
}
