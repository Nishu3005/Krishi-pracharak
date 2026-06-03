import { revalidatePath } from "next/cache";
import { NextResponse } from "next/server";
import Papa from "papaparse";

import { getAllowedSchemaForAI, type AiCsvDataType, type LlmCsvAnalysis } from "@/lib/ai/schema-guard";
import { analyzeCsvWithTokenRouter } from "@/lib/ai/tokenrouter-csv-ingestion";
import { prisma } from "@/lib/prisma";

const DEFAULT_MAX_CSV_BYTES = 500_000;
const DEFAULT_MAX_CSV_ROWS = 1000;

function maxCsvBytes() {
  const value = Number(process.env.AI_MAX_CSV_BYTES || DEFAULT_MAX_CSV_BYTES);
  return Number.isFinite(value) && value > 0 ? value : DEFAULT_MAX_CSV_BYTES;
}

function maxCsvRows() {
  const value = Number(process.env.AI_MAX_CSV_ROWS || DEFAULT_MAX_CSV_ROWS);
  return Number.isFinite(value) && value > 0 ? value : DEFAULT_MAX_CSV_ROWS;
}

function normalizeRequestedType(value: FormDataEntryValue | null): AiCsvDataType | "auto-detect" {
  const type = String(value || "auto-detect");
  const aliases: Record<string, AiCsvDataType | "auto-detect"> = {
    "auto-detect": "auto-detect",
    "farmer survey": "farmer_survey",
    farmer_survey: "farmer_survey",
    "product data": "product_data",
    product_data: "product_data",
    "influencer data": "influencer_data",
    influencer_data: "influencer_data",
    "campaign history": "campaign_history",
    campaign_history: "campaign_history",
    unknown: "unknown"
  };
  return aliases[type] || "auto-detect";
}

function parseCsv(csv: string) {
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

function toBoolean(value: unknown) {
  const normalized = String(value ?? "").trim().toLowerCase();
  return ["yes", "true", "1", "y", "whatsapp", "smartphone"].includes(normalized);
}

function toNumber(value: unknown) {
  const cleaned = String(value ?? "").replace(/[%₹,$]/g, "").trim();
  if (!cleaned) return undefined;
  const numeric = Number(cleaned);
  return Number.isFinite(numeric) ? numeric : undefined;
}

function cleanText(value: unknown) {
  const text = String(value ?? "").trim();
  return text || undefined;
}

function mappedValue(targetTable: string, targetColumn: string, rawValue: unknown) {
  const target = `${targetTable}.${targetColumn}`;
  if (
    target.endsWith("landSizeAcres") ||
    target.endsWith("pricePerUnit") ||
    target.endsWith("retailerInfluenceScore") ||
    target.endsWith("fieldRepInfluenceScore") ||
    target.endsWith("engagementScore") ||
    target.endsWith("followerCount") ||
    target.endsWith("estimatedFarmerReach") ||
    target.endsWith("trustScore") ||
    target.endsWith("engagementRate") ||
    target.endsWith("inquiryRate") ||
    target.endsWith("purchaseConversion") ||
    target.endsWith("farmersTargeted") ||
    target.endsWith("priorityScore") ||
    target.endsWith("quantity") ||
    target.endsWith("relevanceScore") ||
    target.endsWith("costPerCampaign")
  ) {
    return toNumber(rawValue);
  }
  if (
    target.endsWith("smartphoneUser") ||
    target.endsWith("featurePhoneUser") ||
    target.endsWith("whatsappOptIn") ||
    target.endsWith("smsOptIn") ||
    target.endsWith("voiceCallOptIn") ||
    target.endsWith("sustainableFlag") ||
    target.endsWith("organicFlag") ||
    target.endsWith("usableFlag")
  ) {
    const text = String(rawValue ?? "").toLowerCase();
    if (target.endsWith("featurePhoneUser")) return text.includes("feature");
    if (target.endsWith("smartphoneUser")) return text.includes("smart") || toBoolean(rawValue);
    return toBoolean(rawValue);
  }
  return cleanText(rawValue);
}

function buildMappedRows(rows: Record<string, string>[], analysis: LlmCsvAnalysis) {
  const validationByRow = new Map(analysis.rowValidations.map((validation) => [validation.rowNumber, validation]));
  const extractionByRow = new Map(analysis.rowExtractions.map((extraction) => [extraction.rowNumber, extraction.entities]));

  return rows.map((row, index) => {
    const rowNumber = index + 1;
    const extractedEntities = extractionByRow.get(rowNumber);
    const mapped: Record<string, unknown> = extractedEntities ? { entities: extractedEntities } : { entities: {} };

    if (!extractedEntities) {
      for (const mapping of analysis.columnMappings) {
        mapped[`${mapping.targetTable}.${mapping.targetColumn}`] = mappedValue(
          mapping.targetTable,
          mapping.targetColumn,
          row[mapping.sourceColumn]
        );
      }
    }

    const validation = validationByRow.get(rowNumber);
    const issueSeverities = validation?.issues.map((issue) => issue.severity) ?? [];
    const validationStatus = issueSeverities.includes("error")
      ? "error"
      : issueSeverities.includes("warning")
        ? "warning"
        : validation?.validationStatus || "valid";

    return {
      rowNumber,
      raw: row,
      mapped,
      validationStatus,
      errors: validation?.issues.map((issue) => issue.errorMessage) ?? []
    };
  });
}

async function markFailed(params: {
  jobId: number;
  uploadedFileId: number;
  fileName: string;
  requestedCsvType: string;
  rows: number;
  error: string;
}) {
  await prisma.dataIngestionJob.update({
    where: { id: params.jobId },
    data: {
      status: "failed",
      errorReportJson: JSON.stringify([{ error: params.error }])
    }
  });
  await prisma.uploadedFile.update({
    where: { id: params.uploadedFileId },
    data: { status: "failed" }
  });
  await prisma.uploadRecord.create({
    data: {
      fileName: params.fileName,
      purpose: params.requestedCsvType,
      rows: params.rows,
      status: "AI failed",
      aiConfidence: 0,
      importedRows: 0
    }
  });
}

export async function POST(request: Request) {
  const formData = await request.formData();
  const file = formData.get("file");
  const requestedCsvType = normalizeRequestedType(formData.get("csvType"));

  if (!(file instanceof File)) {
    return NextResponse.redirect(new URL("/data?status=missing-file", request.url), 303);
  }

  if (file.size > maxCsvBytes()) {
    return NextResponse.redirect(new URL("/data?status=csv-too-large", request.url), 303);
  }

  let csv = "";
  let columns: string[] = [];
  let rows: Record<string, string>[] = [];

  try {
    csv = await file.text();
    const parsed = parseCsv(csv);
    columns = parsed.columns;
    rows = parsed.rows;
  } catch {
    return NextResponse.redirect(new URL("/data?status=csv-parse-error", request.url), 303);
  }

  if (rows.length > maxCsvRows()) {
    return NextResponse.redirect(new URL("/data?status=csv-too-large", request.url), 303);
  }

  const uploadedFile = await prisma.uploadedFile.create({
    data: {
      originalFileName: file.name,
      uploadPurpose: requestedCsvType,
      requestedCsvType,
      detectedCsvType: "unknown",
      rowCount: rows.length,
      status: "processing"
    }
  });

  const job = await prisma.dataIngestionJob.create({
    data: {
      uploadedFileId: uploadedFile.id,
      requestedCsvType,
      detectedCsvType: "unknown",
      status: "processing",
      totalRows: rows.length,
      validRows: 0,
      invalidRows: 0,
      aiProvider: "tokenrouter",
      aiModel: process.env.OPENAI_MODEL || "auto:balance"
    }
  });

  try {
    const { analysis, metadata } = await analyzeCsvWithTokenRouter({
      fileName: file.name,
      csvText: csv,
      columns,
      rowCount: rows.length,
      allowedSchema: getAllowedSchemaForAI()
    });
    const mappedRows = buildMappedRows(rows, analysis);
    const validRows = mappedRows.filter((row) => row.validationStatus === "valid").length;
    const warningRows = mappedRows.filter((row) => row.validationStatus === "warning").length;
    const errorRows = mappedRows.filter((row) => row.validationStatus === "error").length;
    const status = warningRows || errorRows ? "needs_review" : "ready_for_approval";

    await prisma.uploadedFile.update({
      where: { id: uploadedFile.id },
      data: {
        uploadPurpose: analysis.detectedDataTypes.join(","),
        detectedCsvType: analysis.detectedDataType,
        status: "staged"
      }
    });

    await prisma.dataIngestionJob.update({
      where: { id: job.id },
      data: {
        detectedCsvType: analysis.detectedDataType,
        status,
        validRows,
        invalidRows: errorRows,
        aiConfidence: analysis.confidenceScore,
        aiProvider: metadata.provider,
        aiModel: metadata.model,
        reasoningSummary: analysis.reasoningSummary,
        dataQualityWarningsJson: JSON.stringify(analysis.dataQualityWarnings),
        suggestedFixesJson: JSON.stringify(analysis.suggestedFixes),
        importRecommendation: analysis.importRecommendation,
        errorReportJson: JSON.stringify(analysis.rowValidations.filter((validation) => validation.issues.length))
      }
    });

    await prisma.schemaMapping.createMany({
      data: analysis.columnMappings.map((mapping) => ({
        jobId: job.id,
        sourceColumn: mapping.sourceColumn,
        targetTable: mapping.targetTable,
        targetField: mapping.targetColumn,
        confidence: mapping.mappingConfidence,
        requiredFlag: false,
        transformNote: mapping.transformationNote
      }))
    });

    await prisma.stagingRecord.createMany({
      data: mappedRows.map((row) => ({
        jobId: job.id,
        rowNumber: row.rowNumber,
        rawJson: JSON.stringify(row.raw),
        mappedJson: JSON.stringify(row.mapped),
        validationStatus: row.validationStatus,
        errorsJson: row.errors.length ? JSON.stringify(row.errors) : null,
        aiConfidence: analysis.confidenceScore
      }))
    });

    const validationIssues = analysis.rowValidations.flatMap((validation) =>
      validation.issues.map((issue) => ({
        jobId: job.id,
        rowNumber: validation.rowNumber,
        columnName: issue.columnName,
        errorType: issue.errorType,
        severity: issue.severity,
        errorMessage: issue.errorMessage,
        suggestedFix: issue.suggestedFix
      }))
    );
    if (validationIssues.length) {
      await prisma.validationError.createMany({ data: validationIssues });
    }

    await prisma.uploadRecord.create({
      data: {
        fileName: file.name,
        purpose: analysis.detectedDataTypes.join(","),
        rows: rows.length,
        status: status === "ready_for_approval" ? "Ready for approval" : "Needs review",
        aiConfidence: analysis.confidenceScore,
        importedRows: 0
      }
    });

    if (warningRows || errorRows) {
      await prisma.dataHealthIssue.create({
        data: {
          category: "AI validation",
          label: `${file.name} has ${warningRows} warning row(s) and ${errorRows} error row(s)`,
          issueCount: warningRows + errorRows,
          severity: errorRows ? "high" : "medium",
          recommendedFix: "Review TokenRouter validation issues before approving import.",
          status: "open"
        }
      });
    }

    revalidatePath("/dashboard");
    revalidatePath("/data");
    return NextResponse.redirect(new URL(`/data?jobId=${job.id}&status=csv-staged`, request.url), 303);
  } catch (error) {
    await markFailed({
      jobId: job.id,
      uploadedFileId: uploadedFile.id,
      fileName: file.name,
      requestedCsvType,
      rows: rows.length,
      error: error instanceof Error ? error.message : "TokenRouter CSV analysis failed."
    });
    revalidatePath("/dashboard");
    revalidatePath("/data");
    return NextResponse.redirect(new URL(`/data?jobId=${job.id}&status=ai-error`, request.url), 303);
  }
}
