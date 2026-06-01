export type Segment = {
  name: string;
  summary: string;
  farmerPersona: string;
  region: string;
  mainCrop: string;
  estimatedFarmers: number;
  farmerNeed: string;
  productRelevance: string;
  ecosystemContext: string;
  outbreakWeatherTrigger: string;
  priorityScore: number;
  dataConfidenceScore: number;
  whyCreated: string;
  traits: string[];
  triggers: string[];
  recommendedTone: string;
  scoreBreakdown?: {
    productFit: number;
    regionalRelevance: number;
    cropStageRelevance: number;
    weatherOutbreakUrgency: number;
    farmerNeed: number;
    pastCampaignResponse: number;
  };
  dataConfidenceBreakdown?: {
    surveyDataAvailability: number;
    regionDataAvailability: number;
    weatherDataFreshness: number;
    outbreakDataConfidence: number;
    campaignHistoryAvailability: number;
  };
};

export type GeneratedCampaign = {
  campaignBrief: string;
  hook: string;
  headline: string;
  body: string;
  callToAction: string;
  content: {
    whatsapp: string;
    sms: string;
    voiceScript: string;
    videoScript: string;
    imagePrompt: string;
    influencerScript: string;
    fieldRepScript: string;
    retailerScript: string;
  };
  compliance: {
    status: "Passed" | "Warning" | "Blocked";
    notes: string[];
  };
  expectedPerformance: {
    predictedReach: number;
    expectedEngagement: number;
    expectedInquiryRate: number;
    expectedConversion: number;
    expectedUpliftOverGeneric: number;
  };
  chat: string[];
};
