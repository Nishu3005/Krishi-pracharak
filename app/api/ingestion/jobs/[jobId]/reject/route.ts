import { revalidatePath } from "next/cache";
import { NextResponse } from "next/server";

import { prisma } from "@/lib/prisma";

export async function POST(request: Request, { params }: { params: { jobId: string } }) {
  const jobId = Number(params.jobId);
  if (!Number.isInteger(jobId)) {
    return NextResponse.redirect(new URL("/data?status=invalid-job", request.url), 303);
  }

  const job = await prisma.dataIngestionJob.findUnique({
    where: { id: jobId },
    include: { uploadedFile: true }
  });

  if (!job) {
    return NextResponse.redirect(new URL("/data?status=job-not-found", request.url), 303);
  }

  await prisma.dataIngestionJob.update({
    where: { id: job.id },
    data: { status: "rejected" }
  });
  await prisma.uploadedFile.update({
    where: { id: job.uploadedFileId },
    data: { status: "rejected" }
  });

  revalidatePath("/dashboard");
  revalidatePath("/data");

  return NextResponse.redirect(new URL(`/data?jobId=${job.id}&status=upload-rejected`, request.url), 303);
}
