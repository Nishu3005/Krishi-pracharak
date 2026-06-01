import Papa from "papaparse";

type CsvRecord = Record<string, string>;

const COLUMN_ALIASES: Record<string, string[]> = {
  farmerName: ["farmer", "farmer_name", "name"],
  region: ["region", "state", "location"],
  district: ["district", "taluka"],
  cropType: ["crop", "crop_type"],
  farmSizeAcres: ["farm_size", "acreage", "acres"],
  productInterest: ["product_interest", "interested_product", "brand_interest"],
  channelPreference: ["channel", "preferred_channel", "channel_preference"],
  influencerAffinity: ["influencer", "influencer_affinity", "trusted_voice"],
  budgetBand: ["budget", "budget_band"],
  notes: ["notes", "remarks", "pain_point"],
  productName: ["product_name", "brand_name"],
  influencerName: ["influencer_name", "creator_name"],
  influencerChannel: ["influencer_channel", "creator_channel"],
  language: ["language", "preferred_language"],
  literacyLevel: ["literacy", "literacy_level"],
  smartphoneUser: ["smartphone", "smartphone_user"],
  featurePhoneUser: ["feature_phone", "feature_phone_user"],
  ageBand: ["age_band", "age"],
  farmerSegment: ["segment", "farmer_segment"]
};

function lookup(record: CsvRecord, keys: string[]) {
  const match = Object.entries(record).find(([key]) =>
    keys.some((candidate) => key.trim().toLowerCase() === candidate)
  );
  return match?.[1]?.trim() ?? "";
}

export function parseSurveyCsv(csv: string) {
  const parsed = Papa.parse<CsvRecord>(csv, {
    header: true,
    skipEmptyLines: true,
    transformHeader: (header) => header.trim().toLowerCase()
  });

  if (parsed.errors.length) {
    throw new Error(parsed.errors[0]?.message ?? "Unable to parse CSV.");
  }

  return parsed.data.map((row) => {
    const farmerName = lookup(row, COLUMN_ALIASES.farmerName) || undefined;
    const region = lookup(row, COLUMN_ALIASES.region) || "Unknown Region";
    const district = lookup(row, COLUMN_ALIASES.district) || undefined;
    const cropType = lookup(row, COLUMN_ALIASES.cropType) || undefined;
    const farmSizeAcresValue = lookup(row, COLUMN_ALIASES.farmSizeAcres);
    const farmSizeAcres = farmSizeAcresValue ? Number(farmSizeAcresValue) : undefined;
    const productInterest = lookup(row, COLUMN_ALIASES.productInterest) || undefined;
    const channelPreference = lookup(row, COLUMN_ALIASES.channelPreference) || undefined;
    const influencerAffinity = lookup(row, COLUMN_ALIASES.influencerAffinity) || undefined;
    const budgetBand = lookup(row, COLUMN_ALIASES.budgetBand) || undefined;
    const notes = lookup(row, COLUMN_ALIASES.notes) || undefined;
    const productName = lookup(row, COLUMN_ALIASES.productName) || productInterest || undefined;
    const influencerName = lookup(row, COLUMN_ALIASES.influencerName) || influencerAffinity || undefined;
    const influencerChannel = lookup(row, COLUMN_ALIASES.influencerChannel) || channelPreference || undefined;

    const language = lookup(row, COLUMN_ALIASES.language) || undefined;
    const literacyLevel = lookup(row, COLUMN_ALIASES.literacyLevel) || undefined;
    const smartphoneUser = ["yes", "true", "1", "smartphone"].includes(
      lookup(row, COLUMN_ALIASES.smartphoneUser).toLowerCase()
    );
    const featurePhoneUser = ["yes", "true", "1", "feature phone"].includes(
      lookup(row, COLUMN_ALIASES.featurePhoneUser).toLowerCase()
    );
    const ageBand = lookup(row, COLUMN_ALIASES.ageBand) || undefined;
    const farmerSegment = lookup(row, COLUMN_ALIASES.farmerSegment) || undefined;

    return {
      farmer: {
        farmerName,
        region,
        district,
        cropType,
        landSizeAcres: farmSizeAcres,
        channelPreference,
        annualIncomeBand: budgetBand,
        literacyLevel,
        smartphoneUser,
        featurePhoneUser,
        language,
        ageBand,
        farmerSegment,
        trustChannel: influencerAffinity || channelPreference || undefined,
        notes
      },
      extractedProduct:
        productName && productName !== "Unknown"
          ? {
              name: productName,
              category: cropType ? `${cropType} solution` : "Crop solution",
              productType: "Survey signal",
              targetPestType: notes,
              cropStageRelevance: undefined,
              positioning: notes ? `Built around ${notes}` : "Field-ready performance",
              status: "active"
            }
          : null,
      extractedInfluencer:
        influencerName && influencerName !== "Unknown"
          ? {
              name: influencerName,
              channel: influencerChannel || "YouTube",
              influencerType: "Trusted local voice",
              region,
              primaryLanguage: language,
              primaryCropFocus: cropType ? `${cropType} growers` : "Mixed growers",
              contentStrength: cropType ? `${cropType} advisory` : "Agri advisory",
              reachScore: 5000,
              trustScore: 60
            }
          : null
    };
  });
}
