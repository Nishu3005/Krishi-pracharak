import Link from "next/link";
import { CheckCircle2, Download, FileSearch, UploadCloud, XCircle } from "lucide-react";

import { InfluencerForm } from "@/components/forms/influencer-form";
import { ProductForm } from "@/components/forms/product-form";
import { SurveyUploadForm } from "@/components/forms/survey-upload-form";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { getDataManagementData, getIngestionJobReview } from "@/lib/data";
import { formatDate } from "@/lib/utils";

export const dynamic = "force-dynamic";

function statusClass(status: string) {
  const normalized = status.toLowerCase();
  if (normalized.includes("ready") || normalized.includes("imported") || normalized.includes("valid")) {
    return "bg-primary/12 text-primary";
  }
  if (normalized.includes("failed") || normalized.includes("invalid")) {
    return "bg-red-100 text-red-800";
  }
  return "bg-secondary text-secondary-foreground";
}

function parseJson<T>(value: string | null, fallback: T): T {
  if (!value) {
    return fallback;
  }
  try {
    return JSON.parse(value) as T;
  } catch {
    return fallback;
  }
}

function mappedPreview(mappedJson: string) {
  const mapped = parseJson<Record<string, unknown>>(mappedJson, {});
  return Object.entries(mapped).slice(0, 6);
}

export default async function DataPage({
  searchParams
}: {
  searchParams: { status?: string; count?: string; jobId?: string };
}) {
  const [{ products, influencers, farmers, campaigns, ingestionJobs }, activeJob] = await Promise.all([
    getDataManagementData(),
    getIngestionJobReview(searchParams.jobId)
  ]);

  const invalidRecords = activeJob?.stagingRecords.filter((record) => record.validationStatus !== "valid") ?? [];
  const validRecords = activeJob?.stagingRecords.filter((record) => record.validationStatus === "valid") ?? [];

  return (
    <div>
      <PageHeader
        eyebrow="Stage 1"
        title="CSV Upload Workflow"
        description="Upload CSV files into staging, review AI-like type detection and mappings, validate rows, preview mapped data, then approve the final import."
        badge="Staged import pipeline"
      />

      {searchParams.status ? (
        <div className="mb-6 rounded-2xl border border-border bg-white/82 px-4 py-3 text-sm text-foreground/72 shadow-soft">
          Latest action: <span className="font-semibold">{searchParams.status.replaceAll("-", " ")}</span>
          {searchParams.count ? ` • ${searchParams.count} rows imported` : ""}
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
        <Card className="bg-white/88">
          <div className="flex items-start gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <UploadCloud className="h-5 w-5" />
            </div>
            <div>
              <CardTitle>Upload CSV</CardTitle>
              <CardDescription className="mt-1">
                Choose a known file type or let the rule engine auto-detect from column names.
              </CardDescription>
            </div>
          </div>
          <div className="mt-6">
            <SurveyUploadForm />
          </div>
        </Card>

        <Card className="bg-white/88">
          <div className="flex items-start gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <FileSearch className="h-5 w-5" />
            </div>
            <div>
              <CardTitle>Recent Ingestion Jobs</CardTitle>
              <CardDescription className="mt-1">Files are staged first. Final tables are changed only after approval.</CardDescription>
            </div>
          </div>
          <div className="mt-6 overflow-x-auto">
            <table className="w-full min-w-[720px] border-separate border-spacing-0 text-left text-sm">
              <thead>
                <tr className="text-xs uppercase text-foreground/48">
                  <th className="border-b border-border pb-3 font-semibold">File</th>
                  <th className="border-b border-border pb-3 font-semibold">Requested</th>
                  <th className="border-b border-border pb-3 font-semibold">Detected</th>
                  <th className="border-b border-border pb-3 font-semibold">Rows</th>
                  <th className="border-b border-border pb-3 font-semibold">Status</th>
                  <th className="border-b border-border pb-3 font-semibold">Review</th>
                </tr>
              </thead>
              <tbody>
                {ingestionJobs.map((job) => (
                  <tr key={job.id}>
                    <td className="border-b border-border/65 py-4 pr-4 font-medium">{job.uploadedFile.originalFileName}</td>
                    <td className="border-b border-border/65 py-4 pr-4 text-foreground/68">{job.requestedCsvType}</td>
                    <td className="border-b border-border/65 py-4 pr-4 text-foreground/68">{job.detectedCsvType}</td>
                    <td className="border-b border-border/65 py-4 pr-4">{job.totalRows}</td>
                    <td className="border-b border-border/65 py-4 pr-4">
                      <Badge className={statusClass(job.status)}>{job.status.replaceAll("_", " ")}</Badge>
                    </td>
                    <td className="border-b border-border/65 py-4">
                      <Link href={`/data?jobId=${job.id}`} className="font-semibold text-primary">
                        Open
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {activeJob ? (
        <div className="mt-8 space-y-6">
          <div className="grid gap-6 xl:grid-cols-[0.75fr_1.25fr]">
            <Card className="bg-primary text-primary-foreground">
              <CardTitle className="text-primary-foreground">Detected Data Type</CardTitle>
              <CardDescription className="mt-1 text-primary-foreground/78">
                The selected parser is based on requested type unless auto-detect was chosen.
              </CardDescription>
              <div className="mt-6 grid gap-4 text-sm">
                <div className="rounded-2xl bg-white/10 p-4">
                  <p className="text-primary-foreground/64">File</p>
                  <p className="mt-1 font-semibold">{activeJob.uploadedFile.originalFileName}</p>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-2xl bg-white/10 p-4">
                    <p className="text-primary-foreground/64">Requested</p>
                    <p className="mt-1 font-semibold">{activeJob.requestedCsvType}</p>
                  </div>
                  <div className="rounded-2xl bg-white/10 p-4">
                    <p className="text-primary-foreground/64">Detected</p>
                    <p className="mt-1 font-semibold">{activeJob.detectedCsvType}</p>
                  </div>
                </div>
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="rounded-2xl bg-white/10 p-4">
                    <p className="text-primary-foreground/64">AI Confidence</p>
                    <p className="mt-1 font-semibold">{activeJob.aiConfidence ? `${activeJob.aiConfidence}%` : "N/A"}</p>
                  </div>
                  <div className="rounded-2xl bg-white/10 p-4">
                    <p className="text-primary-foreground/64">Valid</p>
                    <p className="mt-1 font-semibold">{activeJob.validRows}</p>
                  </div>
                  <div className="rounded-2xl bg-white/10 p-4">
                    <p className="text-primary-foreground/64">Invalid</p>
                    <p className="mt-1 font-semibold">{activeJob.invalidRows}</p>
                  </div>
                </div>
              </div>
            </Card>

            <Card className="bg-white/88">
              <CardTitle>Column Mapping Table</CardTitle>
              <CardDescription className="mt-1">Source columns are mapped into staging targets before any final insert.</CardDescription>
              <div className="mt-6 overflow-x-auto">
                <table className="w-full min-w-[760px] border-separate border-spacing-0 text-left text-sm">
                  <thead>
                    <tr className="text-xs uppercase text-foreground/48">
                      <th className="border-b border-border pb-3 font-semibold">Source Column</th>
                      <th className="border-b border-border pb-3 font-semibold">Target Table</th>
                      <th className="border-b border-border pb-3 font-semibold">Target Field</th>
                      <th className="border-b border-border pb-3 font-semibold">Required</th>
                      <th className="border-b border-border pb-3 font-semibold">Confidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activeJob.schemaMappings.map((mapping) => (
                      <tr key={mapping.id}>
                        <td className="border-b border-border/65 py-4 pr-4 font-medium">{mapping.sourceColumn}</td>
                        <td className="border-b border-border/65 py-4 pr-4 text-foreground/68">{mapping.targetTable}</td>
                        <td className="border-b border-border/65 py-4 pr-4 text-foreground/68">{mapping.targetField}</td>
                        <td className="border-b border-border/65 py-4 pr-4">{mapping.requiredFlag ? "Yes" : "No"}</td>
                        <td className="border-b border-border/65 py-4">{mapping.confidence ? `${mapping.confidence}%` : "N/A"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>

          <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
            <Card className="bg-white/88">
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div>
                  <CardTitle>Validation Report</CardTitle>
                  <CardDescription className="mt-1">
                    Checks include missing farmer names, missing villages, invalid crop or language, duplicate farmers, products without names, influencer region gaps, and campaign history missing metrics.
                  </CardDescription>
                </div>
                <Badge className={statusClass(activeJob.status)}>{activeJob.status.replaceAll("_", " ")}</Badge>
              </div>

              <div className="mt-6 grid gap-4 md:grid-cols-3">
                <div className="rounded-2xl border border-border bg-muted/35 p-4">
                  <CheckCircle2 className="h-5 w-5 text-primary" />
                  <p className="mt-3 text-3xl font-semibold">{validRecords.length}</p>
                  <p className="text-sm text-foreground/58">Valid staged rows</p>
                </div>
                <div className="rounded-2xl border border-border bg-muted/35 p-4">
                  <XCircle className="h-5 w-5 text-red-700" />
                  <p className="mt-3 text-3xl font-semibold">{invalidRecords.length}</p>
                  <p className="text-sm text-foreground/58">Rows needing correction</p>
                </div>
                <div className="rounded-2xl border border-border bg-muted/35 p-4">
                  <FileSearch className="h-5 w-5 text-foreground/65" />
                  <p className="mt-3 text-3xl font-semibold">{activeJob.totalRows}</p>
                  <p className="text-sm text-foreground/58">Total rows parsed</p>
                </div>
              </div>

              <div className="mt-5 space-y-3">
                {invalidRecords.slice(0, 5).map((record) => {
                  const errors = parseJson<string[]>(record.errorsJson, []);
                  return (
                    <div key={record.id} className="rounded-2xl border border-red-100 bg-red-50/70 p-4 text-sm">
                      <p className="font-semibold text-red-900">Row {record.rowNumber}</p>
                      <p className="mt-1 text-red-800">{errors.join(", ")}</p>
                    </div>
                  );
                })}
                {!invalidRecords.length ? (
                  <div className="rounded-2xl border border-primary/15 bg-primary/5 p-4 text-sm text-primary">
                    No validation blockers found. Valid rows can be approved for import.
                  </div>
                ) : null}
              </div>

              <div className="mt-6 flex flex-col gap-3 sm:flex-row">
                <form action={`/api/ingestion/jobs/${activeJob.id}/approve`} method="post" className="sm:flex-1">
                  <button
                    type="submit"
                    disabled={activeJob.status === "imported" || validRecords.length === 0}
                    className="inline-flex w-full items-center justify-center rounded-xl bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground disabled:pointer-events-none disabled:opacity-45"
                  >
                    Approve Import
                  </button>
                </form>
                <a
                  href={`/api/ingestion/jobs/${activeJob.id}/errors`}
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-border bg-white px-4 py-3 text-sm font-semibold text-foreground"
                >
                  <Download className="h-4 w-4" />
                  Download Error Report
                </a>
              </div>
            </Card>

            <Card className="bg-white/88">
              <CardTitle>Preview Mapped Rows</CardTitle>
              <CardDescription className="mt-1">Showing staged rows exactly as they will be interpreted on approval.</CardDescription>
              <div className="mt-6 space-y-3">
                {activeJob.stagingRecords.slice(0, 8).map((record) => (
                  <div key={record.id} className="rounded-2xl border border-border bg-muted/35 p-4">
                    <div className="flex items-center justify-between gap-4">
                      <p className="font-semibold">Row {record.rowNumber}</p>
                      <Badge className={statusClass(record.validationStatus)}>{record.validationStatus}</Badge>
                    </div>
                    <div className="mt-3 grid gap-2 text-sm md:grid-cols-2">
                      {mappedPreview(record.mappedJson).map(([key, value]) => (
                        <div key={key} className="rounded-xl bg-white/75 px-3 py-2">
                          <p className="text-xs text-foreground/48">{key}</p>
                          <p className="mt-1 font-medium text-foreground/78">{String(value ?? "N/A")}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </div>
      ) : null}

      <div className="mt-8 grid gap-6 xl:grid-cols-3">
        <Card className="bg-white/84">
          <CardTitle>Add Product</CardTitle>
          <CardDescription className="mt-1">Manual entry remains available for quick demo edits.</CardDescription>
          <div className="mt-6">
            <ProductForm redirectTo="/data" />
          </div>
        </Card>

        <Card className="bg-white/84">
          <CardTitle>Add Influencer</CardTitle>
          <CardDescription className="mt-1">Add trusted voices outside the CSV import flow.</CardDescription>
          <div className="mt-6">
            <InfluencerForm redirectTo="/data" />
          </div>
        </Card>

        <Card className="bg-white/84">
          <CardTitle>Imported Database Snapshot</CardTitle>
          <CardDescription className="mt-1">Current final-table counts after approved imports.</CardDescription>
          <div className="mt-6 grid grid-cols-2 gap-3 text-sm">
            <div className="rounded-2xl bg-muted/45 p-4">
              <p className="text-foreground/58">Farmers</p>
              <p className="mt-1 text-3xl font-semibold">{farmers.length}</p>
            </div>
            <div className="rounded-2xl bg-muted/45 p-4">
              <p className="text-foreground/58">Products</p>
              <p className="mt-1 text-3xl font-semibold">{products.length}</p>
            </div>
            <div className="rounded-2xl bg-muted/45 p-4">
              <p className="text-foreground/58">Influencers</p>
              <p className="mt-1 text-3xl font-semibold">{influencers.length}</p>
            </div>
            <div className="rounded-2xl bg-muted/45 p-4">
              <p className="text-foreground/58">Campaigns</p>
              <p className="mt-1 text-3xl font-semibold">{campaigns.length}</p>
            </div>
          </div>
        </Card>
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="bg-white/84">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Recent Farmer Records</CardTitle>
              <CardDescription className="mt-1">Latest final-table farmer profiles after approval.</CardDescription>
            </div>
            <Badge>{farmers.length} shown</Badge>
          </div>
          <div className="mt-6 space-y-3">
            {farmers.map((farmer) => (
              <div key={farmer.id} className="rounded-2xl border border-border bg-muted/45 p-4">
                <div className="flex flex-col gap-2 md:flex-row md:justify-between">
                  <div>
                    <p className="font-semibold text-foreground">{farmer.name || "Unnamed farmer"}</p>
                    <p className="text-sm text-foreground/66">
                      {farmer.region.state} • {farmer.primaryCrop?.name || "Crop not specified"} • {farmer.trustChannel || "No trust-channel signal"}
                    </p>
                  </div>
                  <p className="text-sm text-foreground/52">{formatDate(farmer.createdAt)}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <div className="space-y-6">
          <Card className="bg-white/84">
            <CardTitle>Available Products</CardTitle>
            <CardDescription className="mt-1">Ready for campaign selection.</CardDescription>
            <div className="mt-5 flex flex-wrap gap-2">
              {products.map((product) => (
                <Badge key={product.id}>{product.name}</Badge>
              ))}
            </div>
          </Card>

          <Card className="bg-white/84">
            <CardTitle>Available Influencers</CardTitle>
            <CardDescription className="mt-1">Mapped by channel for the generation step.</CardDescription>
            <div className="mt-5 flex flex-wrap gap-2">
              {influencers.map((influencer) => (
                <Badge key={influencer.id}>{influencer.name}</Badge>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
