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

  const issues = await prisma.validationError.findMany({
    where: { jobId },
    orderBy: [{ rowNumber: "asc" }, { severity: "asc" }]
  });

  const records = await prisma.stagingRecord.findMany({
    where: { jobId },
    orderBy: { rowNumber: "asc" }
  });
  const recordByRow = new Map(records.map((record) => [record.rowNumber, record]));

  const reportRows = issues.map((issue) => ({
    rowNumber: issue.rowNumber,
    columnName: issue.columnName || "",
    severity: issue.severity,
    errorType: issue.errorType,
    errorMessage: issue.errorMessage,
    suggestedFix: issue.suggestedFix || "",
    rawJson: recordByRow.get(issue.rowNumber)?.rawJson || "",
    mappedJson: recordByRow.get(issue.rowNumber)?.mappedJson || ""
  }));

  const csv = Papa.unparse(reportRows);

  return new Response(csv, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="ingestion-job-${jobId}-errors.csv"`
    }
  });
}
