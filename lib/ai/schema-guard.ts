export const CSV_DATA_TYPES = ["farmer_survey", "product_data", "influencer_data", "campaign_history", "unknown"] as const;
export const CSV_VALIDATION_STATUSES = ["valid", "warning", "error"] as const;
export const CSV_IMPORT_RECOMMENDATIONS = ["approve", "review_required", "reject"] as const;
const CSV_ERROR_TYPES = [
  "missing_value",
  "invalid_format",
  "duplicate",
  "invalid_crop",
  "invalid_language",
  "invalid_region",
  "invalid_channel",
  "unknown"
] as const;

export type AiCsvDataType = (typeof CSV_DATA_TYPES)[number];
export type AiCsvValidationStatus = (typeof CSV_VALIDATION_STATUSES)[number];
export type AiCsvImportRecommendation = (typeof CSV_IMPORT_RECOMMENDATIONS)[number];

export type LlmColumnMapping = {
  sourceColumn: string;
  targetTable: string;
  targetColumn: string;
  mappingConfidence: number;
  transformationNeeded: boolean;
  transformationNote: string;
};

export type LlmRowIssue = {
  columnName: string;
  errorType:
    | "missing_value"
    | "invalid_format"
    | "duplicate"
    | "invalid_crop"
    | "invalid_language"
    | "invalid_region"
    | "invalid_channel"
    | "unknown";
  severity: "warning" | "error";
  errorMessage: string;
  suggestedFix: string;
};

export type LlmRowValidation = {
  rowNumber: number;
  validationStatus: AiCsvValidationStatus;
  issues: LlmRowIssue[];
};

export type LlmEntityRecord = Record<string, unknown>;

export type LlmRowExtraction = {
  rowNumber: number;
  entities: Record<string, LlmEntityRecord[]>;
};

export type LlmCsvAnalysis = {
  detectedDataType: AiCsvDataType;
  detectedDataTypes: AiCsvDataType[];
  confidenceScore: number;
  reasoningSummary: string;
  columnMappings: LlmColumnMapping[];
  rowExtractions: LlmRowExtraction[];
  rowValidations: LlmRowValidation[];
  dataQualityWarnings: string[];
  suggestedFixes: string[];
  importRecommendation: AiCsvImportRecommendation;
};

export type LlmSegmentationResponse = {
  overallStrategy: string;
  segments: Array<{
    segmentName: string;
    farmerPersona: string;
    region: string;
    mainCrop: string;
    estimatedFarmers: number;
    farmerNeed: string;
    productRelevance: string;
    ecosystemContext: string;
    weatherOrOutbreakTrigger: string;
    priorityScore: number;
    dataConfidenceScore: number;
    whyThisSegment: string[];
    recommendedNextAction: string;
  }>;
  dataGaps: string[];
  assumptions: string[];
};

type AllowedSchema = Record<string, string[]>;

const ALLOWED_SCHEMA: AllowedSchema = {
  regions: ["state", "district", "village"],
  crops: ["cropName", "category", "season"],
  languages: ["languageName"],
  farmers: [
    "farmerName",
    "primaryCropId",
    "landSizeAcres",
    "annualIncomeBand",
    "literacyLevel",
    "smartphoneUser",
    "featurePhoneUser",
    "gender",
    "ageBand",
    "farmerSegment",
    "trustChannel"
  ],
  farming_practices: [
    "farmingType",
    "sowingPeriod",
    "irrigationMethod",
    "mechanizationLevel",
    "fertilizerPractice",
    "pesticidePractice",
    "laborDependency",
    "cultivationFrequency"
  ],
  farmer_assets: ["assetType", "assetName", "ownershipType", "quantity", "usableFlag"],
  channel_preferences: [
    "whatsappOptIn",
    "smsOptIn",
    "voiceCallOptIn",
    "retailerInfluenceScore",
    "fieldRepInfluenceScore",
    "preferredContactTime",
    "engagementScore"
  ],
  products: [
    "productName",
    "productCategory",
    "productType",
    "sustainableFlag",
    "organicFlag",
    "pricePerUnit",
    "unitType",
    "activeIngredient",
    "targetPestType",
    "cropStageRelevance",
    "description",
    "status"
  ],
  product_crop_fit: ["cropName", "outbreakType", "outbreakName", "recommendedStage", "relevanceScore"],
  influencers: [
    "influencerName",
    "influencerType",
    "platform",
    "primaryLanguage",
    "cropExpertise",
    "followerCount",
    "estimatedFarmerReach",
    "trustScore",
    "engagementRate",
    "contentStrength",
    "costPerCampaign",
    "contentFormat",
    "contactPhone",
    "contactEmail",
    "commercialTerms",
    "complianceStatus",
    "status"
  ],
  campaigns: ["campaignName", "productName", "cropName", "region", "channel", "status", "launchDate"],
  campaign_targets: ["farmersTargeted", "priorityScore", "recommendedChannel"],
  campaign_responses: ["engagementRate", "inquiryRate", "purchaseConversion"]
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function clampScore(value: unknown) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return 0;
  }
  return Math.max(0, Math.min(100, Math.round(numeric)));
}

function assertString(value: unknown, label: string) {
  if (typeof value !== "string") {
    throw new Error(`${label} must be a string.`);
  }
  return value;
}

function stringArray(value: unknown, label: string) {
  if (!Array.isArray(value) || value.some((entry) => typeof entry !== "string")) {
    throw new Error(`${label} must be an array of strings.`);
  }
  return value as string[];
}

export function getAllowedSchemaForAI() {
  return ALLOWED_SCHEMA;
}

export function validateLlmColumnMappings(value: unknown): LlmColumnMapping[] {
  if (!Array.isArray(value)) {
    throw new Error("LLM columnMappings must be an array.");
  }

  return value.map((entry, index) => {
    if (!isRecord(entry)) {
      throw new Error(`LLM column mapping ${index + 1} must be an object.`);
    }

    const targetTable = assertString(entry.targetTable, `columnMappings[${index}].targetTable`);
    const targetColumn = assertString(entry.targetColumn, `columnMappings[${index}].targetColumn`);
    const allowedColumns = ALLOWED_SCHEMA[targetTable];
    if (!allowedColumns) {
      throw new Error(`LLM mapped to unknown table "${targetTable}".`);
    }
    if (!allowedColumns.includes(targetColumn)) {
      throw new Error(`LLM mapped to unknown column "${targetTable}.${targetColumn}".`);
    }

    return {
      sourceColumn: assertString(entry.sourceColumn, `columnMappings[${index}].sourceColumn`),
      targetTable,
      targetColumn,
      mappingConfidence: clampScore(entry.mappingConfidence),
      transformationNeeded: Boolean(entry.transformationNeeded),
      transformationNote: typeof entry.transformationNote === "string" ? entry.transformationNote : ""
    };
  });
}

function normalizeEntityValue(value: unknown) {
  if (value === null || value === undefined) {
    return undefined;
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed || undefined;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return value;
  }
  return value;
}

function validateEntityRecord(table: string, value: unknown, label: string): LlmEntityRecord {
  if (!isRecord(value)) {
    throw new Error(`${label} must be an object.`);
  }
  const allowedColumns = ALLOWED_SCHEMA[table];
  if (!allowedColumns) {
    throw new Error(`LLM extracted unknown table "${table}".`);
  }

  const normalized: LlmEntityRecord = {};
  for (const [key, entryValue] of Object.entries(value)) {
    if (!allowedColumns.includes(key)) {
      throw new Error(`LLM extracted unknown column "${table}.${key}".`);
    }
    const cleaned = normalizeEntityValue(entryValue);
    if (cleaned !== undefined) {
      normalized[key] = cleaned;
    }
  }
  return normalized;
}

function validateRowExtractions(value: unknown): LlmRowExtraction[] {
  if (!Array.isArray(value)) {
    throw new Error("LLM rowExtractions must be an array.");
  }

  return value.map((entry, index) => {
    if (!isRecord(entry)) {
      throw new Error(`rowExtractions[${index}] must be an object.`);
    }
    const rowNumber = Number(entry.rowNumber);
    if (!Number.isInteger(rowNumber) || rowNumber < 1) {
      throw new Error("LLM row extraction rowNumber must be a positive integer.");
    }
    if (!isRecord(entry.entities)) {
      throw new Error(`rowExtractions[${index}].entities must be an object.`);
    }

    const entities: Record<string, LlmEntityRecord[]> = {};
    for (const [table, tableRows] of Object.entries(entry.entities)) {
      if (!ALLOWED_SCHEMA[table]) {
        throw new Error(`LLM extracted unknown table "${table}".`);
      }
      if (!Array.isArray(tableRows)) {
        throw new Error(`rowExtractions[${index}].entities.${table} must be an array.`);
      }
      entities[table] = tableRows.map((row, rowIndex) =>
        validateEntityRecord(table, row, `rowExtractions[${index}].entities.${table}[${rowIndex}]`)
      );
    }

    return { rowNumber, entities };
  });
}

export function validateLlmCsvResponse(value: unknown): LlmCsvAnalysis {
  if (!isRecord(value)) {
    throw new Error("LLM CSV response must be a JSON object.");
  }

  const detectedDataType = assertString(value.detectedDataType ?? "unknown", "detectedDataType") as AiCsvDataType;
  if (!CSV_DATA_TYPES.includes(detectedDataType)) {
    throw new Error(`LLM returned invalid detectedDataType "${detectedDataType}".`);
  }
  const detectedDataTypes = Array.isArray(value.detectedDataTypes)
    ? value.detectedDataTypes.map((type) => assertString(type, "detectedDataTypes entry") as AiCsvDataType)
    : [detectedDataType];
  for (const type of detectedDataTypes) {
    if (!CSV_DATA_TYPES.includes(type)) {
      throw new Error(`LLM returned invalid detectedDataTypes entry "${type}".`);
    }
  }

  const importRecommendation = assertString(value.importRecommendation, "importRecommendation") as AiCsvImportRecommendation;
  if (!CSV_IMPORT_RECOMMENDATIONS.includes(importRecommendation)) {
    throw new Error(`LLM returned invalid importRecommendation "${importRecommendation}".`);
  }

  if (!Array.isArray(value.rowValidations)) {
    throw new Error("LLM rowValidations must be an array.");
  }

  const rowValidations = value.rowValidations.map((entry, index) => {
    if (!isRecord(entry)) {
      throw new Error(`rowValidations[${index}] must be an object.`);
    }
    const validationStatus = assertString(entry.validationStatus, `rowValidations[${index}].validationStatus`) as AiCsvValidationStatus;
    if (!CSV_VALIDATION_STATUSES.includes(validationStatus)) {
      throw new Error(`LLM returned invalid validationStatus "${validationStatus}".`);
    }
    const issues = Array.isArray(entry.issues) ? entry.issues : [];
    return {
      rowNumber: Number(entry.rowNumber),
      validationStatus,
      issues: issues.map((issue, issueIndex) => {
        if (!isRecord(issue)) {
          throw new Error(`rowValidations[${index}].issues[${issueIndex}] must be an object.`);
        }
        const severity = assertString(issue.severity, `rowValidations[${index}].issues[${issueIndex}].severity`);
        if (severity !== "warning" && severity !== "error") {
          throw new Error(`LLM returned invalid issue severity "${severity}".`);
        }
        const errorType = typeof issue.errorType === "string" ? issue.errorType : "unknown";
        if (!CSV_ERROR_TYPES.includes(errorType as (typeof CSV_ERROR_TYPES)[number])) {
          throw new Error(`LLM returned invalid issue errorType "${errorType}".`);
        }
        return {
          columnName: typeof issue.columnName === "string" ? issue.columnName : "",
          errorType: errorType as LlmRowIssue["errorType"],
          severity: severity as LlmRowIssue["severity"],
          errorMessage: assertString(issue.errorMessage, `rowValidations[${index}].issues[${issueIndex}].errorMessage`),
          suggestedFix: typeof issue.suggestedFix === "string" ? issue.suggestedFix : ""
        };
      })
    };
  });

  for (const validation of rowValidations) {
    if (!Number.isInteger(validation.rowNumber) || validation.rowNumber < 1) {
      throw new Error("LLM row validation rowNumber must be a positive integer.");
    }
  }

  return {
    detectedDataType,
    detectedDataTypes: detectedDataTypes.length ? detectedDataTypes : [detectedDataType],
    confidenceScore: clampScore(value.confidenceScore),
    reasoningSummary: assertString(value.reasoningSummary, "reasoningSummary"),
    columnMappings: validateLlmColumnMappings(value.columnMappings),
    rowExtractions: validateRowExtractions(value.rowExtractions),
    rowValidations,
    dataQualityWarnings: stringArray(value.dataQualityWarnings ?? [], "dataQualityWarnings"),
    suggestedFixes: stringArray(value.suggestedFixes ?? [], "suggestedFixes"),
    importRecommendation
  };
}

export function validateLlmSegmentationResponse(value: unknown): LlmSegmentationResponse {
  if (!isRecord(value)) {
    throw new Error("LLM segmentation response must be a JSON object.");
  }
  if (!Array.isArray(value.segments)) {
    throw new Error("LLM segmentation response must include segments.");
  }
  if (value.segments.length < 3 || value.segments.length > 6) {
    throw new Error("LLM segmentation response must include 3 to 6 segments.");
  }

  return {
    overallStrategy: assertString(value.overallStrategy, "overallStrategy"),
    dataGaps: stringArray(value.dataGaps ?? [], "dataGaps"),
    assumptions: stringArray(value.assumptions ?? [], "assumptions"),
    segments: value.segments.map((segment, index) => {
      if (!isRecord(segment)) {
        throw new Error(`segments[${index}] must be an object.`);
      }
      return {
        segmentName: assertString(segment.segmentName, `segments[${index}].segmentName`),
        farmerPersona: assertString(segment.farmerPersona, `segments[${index}].farmerPersona`),
        region: assertString(segment.region, `segments[${index}].region`),
        mainCrop: assertString(segment.mainCrop, `segments[${index}].mainCrop`),
        estimatedFarmers: Math.max(1, Math.round(Number(segment.estimatedFarmers) || 1)),
        farmerNeed: assertString(segment.farmerNeed, `segments[${index}].farmerNeed`),
        productRelevance: assertString(segment.productRelevance, `segments[${index}].productRelevance`),
        ecosystemContext: assertString(segment.ecosystemContext, `segments[${index}].ecosystemContext`),
        weatherOrOutbreakTrigger: assertString(segment.weatherOrOutbreakTrigger, `segments[${index}].weatherOrOutbreakTrigger`),
        priorityScore: clampScore(segment.priorityScore),
        dataConfidenceScore: clampScore(segment.dataConfidenceScore),
        whyThisSegment: stringArray(segment.whyThisSegment, `segments[${index}].whyThisSegment`),
        recommendedNextAction: assertString(segment.recommendedNextAction, `segments[${index}].recommendedNextAction`)
      };
    })
  };
}
