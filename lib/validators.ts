import { z } from "zod";

const optionalText = z.preprocess(
  (value) => (typeof value === "string" && value.trim() === "" ? undefined : value),
  z.string().optional()
);

export const productSchema = z.object({
  name: z.string().min(2),
  category: z.string().min(2),
  productType: optionalText,
  sustainableFlag: z.coerce.boolean().optional(),
  organicFlag: z.coerce.boolean().optional(),
  pricePerUnit: optionalText,
  unitType: optionalText,
  activeIngredient: optionalText,
  targetPestType: optionalText,
  cropStageRelevance: optionalText,
  positioning: optionalText,
  status: optionalText
});

export const influencerSchema = z.object({
  name: z.string().min(2),
  channel: z.string().min(2),
  influencerType: optionalText,
  region: optionalText,
  primaryLanguage: optionalText,
  primaryCropFocus: optionalText,
  followerCount: z.coerce.number().int().nonnegative().optional(),
  reachScore: z.coerce.number().int().nonnegative().optional(),
  trustScore: z.coerce.number().min(0).max(100).optional(),
  engagementRate: z.coerce.number().min(0).max(100).optional(),
  contentStrength: optionalText,
  costPerCampaign: z.coerce.number().nonnegative().optional(),
  contentFormat: optionalText,
  contactPhone: optionalText,
  contactEmail: optionalText,
  commercialTerms: optionalText,
  complianceStatus: optionalText,
  status: optionalText
});

export const segmentationSchema = z.object({
  productId: z.coerce.number().int().positive(),
  region: z.string().optional(),
  channel: z.string().optional(),
  influencerId: z.coerce.number().int().positive().optional().or(z.literal("")),
  additionalInfo: z.string().optional()
});

export const generationSchema = segmentationSchema.extend({
  segment: z.object({
    name: z.string(),
    summary: z.string(),
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
    whyThisSegment: z.array(z.string()).optional(),
    recommendedNextAction: z.string().optional(),
    traits: z.array(z.string()),
    triggers: z.array(z.string()),
    recommendedTone: z.string()
  })
});
