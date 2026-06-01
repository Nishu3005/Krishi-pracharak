import { revalidatePath } from "next/cache";
import { NextResponse } from "next/server";
import Papa from "papaparse";

import { prisma } from "@/lib/prisma";

function countRows(fileName: string, text: string) {
  if (!fileName.toLowerCase().endsWith(".csv")) {
    return 1;
  }

  const parsed = Papa.parse<Record<string, string>>(text, {
    header: true,
    skipEmptyLines: true
  });

  return parsed.data.length;
}

export async function POST(request: Request) {
  const formData = await request.formData();
  const file = formData.get("file");
  const purpose = String(formData.get("purpose") || "Data Upload");

  if (!(file instanceof File)) {
    return NextResponse.redirect(new URL("/dashboard?status=missing-file", request.url), 303);
  }

  const text = await file.text();
  const rows = countRows(file.name, text);
  const isModel = purpose.toLowerCase().includes("model");

  await prisma.uploadRecord.create({
    data: {
      fileName: file.name,
      purpose,
      rows,
      status: isModel ? "Validated" : "Needs Review",
      aiConfidence: isModel ? 93 : 78,
      importedRows: isModel ? rows : Math.max(0, rows - 2)
    }
  });

  if (!isModel) {
    await prisma.dataHealthIssue.create({
      data: {
        category: "Validation errors",
        label: `${purpose} upload requires business review`,
        issueCount: Math.min(3, Math.max(1, rows)),
        severity: "medium",
        recommendedFix: "Review required columns, map missing campaign fields, and approve imported history.",
        status: "open"
      }
    });
  }

  revalidatePath("/dashboard");

  return NextResponse.redirect(new URL("/dashboard?status=upload-recorded", request.url), 303);
}
