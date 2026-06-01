import { revalidatePath } from "next/cache";
import { NextResponse } from "next/server";

import { importApprovedRows, type CsvType, type MappedPreviewRow } from "@/lib/ai/csv-ingestion";
import { prisma } from "@/lib/prisma";

function parseStagedRecord(record: {
  rowNumber: number;
  rawJson: string;
  mappedJson: string;
  validationStatus: string;
  errorsJson: string | null;
  aiConfidence: unknown;
}): MappedPreviewRow {
  return {
    rowNumber: record.rowNumber,
    raw: JSON.parse(record.rawJson),
    mapped: JSON.parse(record.mappedJson),
    validationStatus: record.validationStatus === "valid" ? "valid" : "invalid",
    errors: record.errorsJson ? JSON.parse(record.errorsJson) : [],
    aiConfidence: Number(record.aiConfidence || 0)
  };
}

export async function POST(
  request: Request,
  { params }: { params: { jobId: string } }
) {
  const jobId = Number(params.jobId);

  if (!Number.isInteger(jobId)) {
    return NextResponse.redirect(new URL("/data?status=invalid-job", request.url), 303);
  }

  const job = await prisma.dataIngestionJob.findUnique({
    where: { id: jobId },
    include: {
      uploadedFile: true,
      stagingRecords: {
        orderBy: { rowNumber: "asc" }
      }
    }
  });

  if (!job) {
    return NextResponse.redirect(new URL("/data?status=job-not-found", request.url), 303);
  }

  if (job.status === "imported") {
    return NextResponse.redirect(new URL(`/data?jobId=${job.id}&status=already-imported`, request.url), 303);
  }

  const rows = job.stagingRecords.map(parseStagedRecord);
  const importedRows = await importApprovedRows({
    prisma,
    csvType: job.requestedCsvType === "auto-detect" ? (job.detectedCsvType as CsvType) : (job.requestedCsvType as CsvType),
    rows
  });

  await prisma.stagingRecord.updateMany({
    where: {
      jobId: job.id,
      validationStatus: "valid"
    },
    data: { importedFlag: true }
  });

  await prisma.dataIngestionJob.update({
    where: { id: job.id },
    data: {
      status: "imported",
      approvedAt: new Date(),
      validRows: importedRows
    }
  });

  await prisma.uploadedFile.update({
    where: { id: job.uploadedFileId },
    data: { status: "imported" }
  });

  await prisma.uploadRecord.create({
    data: {
      fileName: job.uploadedFile.originalFileName,
      purpose: job.uploadedFile.uploadPurpose,
      rows: job.totalRows,
      status: "Imported",
      aiConfidence: job.aiConfidence,
      importedRows
    }
  });

  revalidatePath("/dashboard");
  revalidatePath("/data");
  revalidatePath("/products");
  revalidatePath("/influencers");
  revalidatePath("/campaigns/create");

  return NextResponse.redirect(
    new URL(`/data?jobId=${job.id}&status=import-approved&count=${importedRows}`, request.url),
    303
  );
}
