import { NextResponse } from "next/server";
import Papa from "papaparse";

import { prisma } from "@/lib/prisma";

export async function GET(
  _request: Request,
  { params }: { params: { jobId: string } }
) {
  const jobId = Number(params.jobId);

  if (!Number.isInteger(jobId)) {
    return NextResponse.json({ error: "Invalid job." }, { status: 400 });
  }

  const records = await prisma.stagingRecord.findMany({
    where: {
      jobId,
      validationStatus: "invalid"
    },
    orderBy: { rowNumber: "asc" }
  });

  const reportRows = records.map((record) => ({
    rowNumber: record.rowNumber,
    errors: record.errorsJson ? JSON.parse(record.errorsJson).join("; ") : "",
    rawJson: record.rawJson,
    mappedJson: record.mappedJson
  }));

  const csv = Papa.unparse(reportRows);

  return new Response(csv, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="ingestion-job-${jobId}-errors.csv"`
    }
  });
}
