import {
  getAllowedSchemaForAI,
  validateLlmCsvResponse,
  type LlmCsvAnalysis
} from "@/lib/ai/schema-guard";
import { callTokenRouterJson } from "@/lib/ai/tokenrouter-client";
import { prisma } from "@/lib/prisma";

type AnalyzeCsvInput = {
  fileName: string;
  csvText: string;
  columns: string[];
  rowCount: number;
  allowedSchema?: object;
};

const CSV_JSON_SCHEMA_DESCRIPTION = `{
  "detectedDataType": "farmer_survey | product_data | influencer_data | campaign_history | unknown",
  "detectedDataTypes": ["farmer_survey | product_data | influencer_data | campaign_history | unknown"],
  "confidenceScore": 0,
  "reasoningSummary": "string",
  "columnMappings": [
    {
      "sourceColumn": "string",
      "targetTable": "string",
      "targetColumn": "string",
      "mappingConfidence": 0,
      "transformationNeeded": false,
      "transformationNote": "string"
    }
  ],
  "rowExtractions": [
    {
      "rowNumber": 1,
      "entities": {
        "regions": [{ "state": "string", "district": "string", "village": "string" }],
        "languages": [{ "languageName": "string" }],
        "crops": [{ "cropName": "string" }],
        "farmers": [{ "farmerName": "string", "landSizeAcres": 0, "trustChannel": "string" }],
        "channel_preferences": [{ "whatsappOptIn": true }],
        "farming_practices": [{ "farmingType": "string" }],
        "farmer_assets": [{ "assetType": "string" }],
        "products": [{ "productName": "string", "productCategory": "string" }],
        "product_crop_fit": [{ "cropName": "string" }],
        "influencers": [{ "influencerName": "string" }],
        "campaigns": [{ "campaignName": "string" }],
        "campaign_targets": [{ "farmersTargeted": 0 }],
        "campaign_responses": [{ "engagementRate": 0 }]
      }
    }
  ],
  "rowValidations": [
    {
      "rowNumber": 1,
      "validationStatus": "valid | warning | error",
      "issues": [
        {
          "columnName": "string",
          "errorType": "missing_value | invalid_format | duplicate | invalid_crop | invalid_language | invalid_region | invalid_channel | unknown",
          "severity": "warning | error",
          "errorMessage": "string",
          "suggestedFix": "string"
        }
      ]
    }
  ],
  "dataQualityWarnings": ["string"],
  "suggestedFixes": ["string"],
  "importRecommendation": "approve | review_required | reject"
}`;

const SYSTEM_PROMPT = `You are a data ingestion AI for an agricultural marketing intelligence platform.
Classify the uploaded CSV.
Map columns to the existing database schema only.
Extract normalized entities for every row.
One row may contain multiple entity types at the same time.
For example, if a row has farmer, village, crop, and language data, extract entities for farmers, regions, crops, and languages in that row.
Validate rows for missing values, invalid values, duplicates, and inconsistent agricultural fields.
Do not invent table names.
Do not invent columns.
Only use tables and fields from the allowed database schema.
Return JSON only.
No markdown.
No explanation outside JSON.`;

function inputSummary(input: AnalyzeCsvInput) {
  return JSON.stringify({
    feature: "csv_ingestion",
    fileName: input.fileName,
    rowCount: input.rowCount,
    columnCount: input.columns.length
  });
}

async function logValidationFeature(input: AnalyzeCsvInput, analysis: LlmCsvAnalysis, status: string, errorMessage?: string) {
  try {
    await prisma.aiGenerationLog.create({
      data: {
        feature: "csv_validation",
        provider: "tokenrouter",
        model: process.env.OPENAI_MODEL || "auto:balance",
        inputSummary: inputSummary(input),
        outputSummary: status === "success" ? `${analysis.rowValidations.length} row validation result(s)` : undefined,
        status,
        errorMessage
      }
    });
  } catch {
    // Non-critical audit logging.
  }
}

export async function analyzeCsvWithTokenRouter(input: AnalyzeCsvInput) {
  const allowedSchema = input.allowedSchema ?? getAllowedSchemaForAI();
  const userPrompt = `Analyze this CSV upload.

File name: ${input.fileName}
Row count: ${input.rowCount}
Columns: ${JSON.stringify(input.columns)}

Allowed database schema:
${JSON.stringify(allowedSchema, null, 2)}

Full CSV content:
${input.csvText}`;

  try {
    const result = await callTokenRouterJson<LlmCsvAnalysis>({
      systemPrompt: SYSTEM_PROMPT,
      userPrompt,
      jsonSchemaDescription: CSV_JSON_SCHEMA_DESCRIPTION,
      featureName: "csv_ingestion",
      inputSummary: inputSummary(input)
    });

    const analysis = validateLlmCsvResponse(result.parsed);
    await logValidationFeature(input, analysis, "success");
    return {
      analysis,
      rawText: result.rawText,
      metadata: result.metadata
    };
  } catch (error) {
    await logValidationFeature(
      input,
      {
        detectedDataType: "unknown",
        detectedDataTypes: ["unknown"],
        confidenceScore: 0,
        reasoningSummary: "",
        columnMappings: [],
        rowExtractions: [],
        rowValidations: [],
        dataQualityWarnings: [],
        suggestedFixes: [],
        importRecommendation: "reject"
      },
      "failed",
      error instanceof Error ? error.message : "CSV validation failed."
    );
    throw error;
  }
}
