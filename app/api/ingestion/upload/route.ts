import { revalidatePath } from "next/cache";
import { NextResponse } from "next/server";

import {
  buildMappedRows,
  detectCsvType,
  mapColumnsToSchema,
  parseCsv,
  validateMappedRows,
  type CsvType
} from "@/lib/ai/csv-ingestion";
import { prisma } from "@/lib/prisma";

function normalizeRequestedType(value: FormDataEntryValue | null): CsvType | "auto-detect" {
  const type = String(value || "auto-detect");
  if (
    type === "farmer survey" ||
    type === "product data" ||
    type === "influencer data" ||
    type === "campaign history" ||
    type === "unknown" ||
    type === "auto-detect"
  ) {
    return type;
  }
  return "auto-detect";
}

export async function POST(request: Request) {
  const formData = await request.formData();
  const file = formData.get("file");
  const requestedCsvType = normalizeRequestedType(formData.get("csvType"));

  if (!(file instanceof File)) {
    return NextResponse.redirect(new URL("/data?status=missing-file", request.url), 303);
  }

  try {
    const csv = await file.text();
    const { columns, rows } = parseCsv(csv);
    const detected = detectCsvType(columns);
    const processingCsvType = requestedCsvType === "auto-detect" ? detected.csvType : requestedCsvType;
    const mappings = mapColumnsToSchema(columns, processingCsvType);
    const mappedRows = buildMappedRows(rows, mappings, processingCsvType);
    const validatedRows = await validateMappedRows({
      prisma,
      mappedRows,
      csvType: processingCsvType
    });
    const validRows = validatedRows.filter((row) => row.validationStatus === "valid").length;
    const invalidRows = validatedRows.length - validRows;
    const avgConfidence = Math.round(
      validatedRows.reduce((sum, row) => sum + row.aiConfidence, 0) / Math.max(validatedRows.length, 1)
    );

    const uploadedFile = await prisma.uploadedFile.create({
      data: {
        originalFileName: file.name,
        uploadPurpose: processingCsvType,
        requestedCsvType,
        detectedCsvType: detected.csvType,
        rowCount: rows.length,
        status: "staged"
      }
    });

    const job = await prisma.dataIngestionJob.create({
      data: {
        uploadedFileId: uploadedFile.id,
        requestedCsvType,
        detectedCsvType: detected.csvType,
        status: invalidRows ? "validation_failed" : "ready_for_approval",
        totalRows: rows.length,
        validRows,
        invalidRows,
        aiConfidence: avgConfidence,
        errorReportJson: JSON.stringify(
          validatedRows
            .filter((row) => row.errors.length)
            .map((row) => ({
              rowNumber: row.rowNumber,
              errors: row.errors,
              raw: row.raw
            }))
        )
      }
    });

    await prisma.schemaMapping.createMany({
      data: mappings.map((mapping) => ({
        jobId: job.id,
        sourceColumn: mapping.sourceColumn,
        targetTable: mapping.targetTable,
        targetField: mapping.targetField,
        confidence: mapping.confidence,
        requiredFlag: mapping.requiredFlag,
        transformNote: mapping.transformNote
      }))
    });

    await prisma.stagingRecord.createMany({
      data: validatedRows.map((row) => ({
        jobId: job.id,
        rowNumber: row.rowNumber,
        rawJson: JSON.stringify(row.raw),
        mappedJson: JSON.stringify(row.mapped),
        validationStatus: row.validationStatus,
        errorsJson: row.errors.length ? JSON.stringify(row.errors) : null,
        aiConfidence: row.aiConfidence
      }))
    });

    await prisma.uploadRecord.create({
      data: {
        fileName: file.name,
        purpose: processingCsvType,
        rows: rows.length,
        status: invalidRows ? "Staged with warnings" : "Ready for approval",
        aiConfidence: avgConfidence,
        importedRows: 0
      }
    });

    if (invalidRows) {
      await prisma.dataHealthIssue.create({
        data: {
          category: "Validation errors",
          label: `${file.name} has ${invalidRows} invalid staged rows`,
          issueCount: invalidRows,
          severity: "high",
          recommendedFix: "Review the validation report, correct source data, and re-upload before approval.",
          status: "open"
        }
      });
    }

    revalidatePath("/dashboard");
    revalidatePath("/data");

    return NextResponse.redirect(
      new URL(`/data?jobId=${job.id}&status=csv-staged`, request.url),
      303
    );
  } catch {
    return NextResponse.redirect(new URL("/data?status=csv-parse-error", request.url), 303);
  }
}
