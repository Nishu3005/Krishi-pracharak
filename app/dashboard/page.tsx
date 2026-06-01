import Link from "next/link";
import {
  Bot,
  BrainCircuit,
  FileClock,
  Megaphone,
  PackagePlus,
  UploadCloud,
  UsersRound
} from "lucide-react";

import { DashboardCharts } from "@/components/dashboard/dashboard-charts";
import { MetricCard } from "@/components/dashboard/metric-card";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { getDashboardData } from "@/lib/data";
import { formatDate } from "@/lib/utils";

export const dynamic = "force-dynamic";

function percent(value: number) {
  return `${value}%`;
}

function statusClass(status: string) {
  const normalized = status.toLowerCase();
  if (normalized.includes("import") || normalized.includes("live") || normalized.includes("validated")) {
    return "bg-primary/12 text-primary";
  }
  if (normalized.includes("review") || normalized.includes("draft")) {
    return "bg-secondary text-secondary-foreground";
  }
  return "bg-muted text-foreground/70";
}

const quickActions = [
  {
    title: "Upload Survey CSV",
    description: "Parse farmer survey rows into regions, crops, channel preferences, products, and influencers.",
    action: "/api/ingestion/upload",
    purpose: "Survey CSV",
    accept: ".csv,text/csv",
    icon: UploadCloud,
    button: "Upload CSV"
  },
  {
    title: "Add Product",
    description: "Add crop-stage fit, product type, threat relevance, and positioning data.",
    href: "/products",
    icon: PackagePlus
  },
  {
    title: "Add Influencer",
    description: "Register trusted local voices and digital creators for post-segmentation activation.",
    href: "/influencers",
    icon: UsersRound
  },
  {
    title: "Upload Campaign History",
    description: "Bring past campaign rows into the learning loop for response and conversion benchmarks.",
    action: "/api/uploads/generic",
    purpose: "Campaign History",
    accept: ".csv,text/csv",
    icon: FileClock,
    button: "Upload History"
  },
  {
    title: "Upload Model",
    description: "Stage a rule model or scoring config for future channel and priority recommendations.",
    action: "/api/uploads/generic",
    purpose: "Model Upload",
    accept: ".json,.csv,application/json,text/csv",
    icon: BrainCircuit,
    button: "Upload Model"
  }
];

export default async function DashboardPage() {
  const {
    metrics,
    campaigns,
    uploads,
    dataHealthIssues,
    regionChartData,
    channelChartData,
    healthByCategory,
    performanceChartData
  } = await getDashboardData();

  return (
    <div>
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <PageHeader
          eyebrow="Stage 1"
          title="Dashboard and Data Onboarding"
          description="Monitor farmer intelligence, onboarding quality, campaign history, and AI-readiness for the Krishi Pracharak planning engine."
          badge="MVP intelligence console"
        />
        <Link
          href="/campaigns/create"
          className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground shadow-soft transition hover:opacity-95"
        >
          <Megaphone className="h-4 w-4" />
          Create Campaign
        </Link>
      </div>

      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="Total Farmers" value={metrics.farmerCount} description="Farmer profiles available for targeting." accent="green" />
        <MetricCard title="Total Products" value={metrics.productCount} description="Product records mapped to crop and threat context." />
        <MetricCard title="Total Influencers" value={metrics.influencerCount} description="Trusted voices available for activation." />
        <MetricCard title="Total Regions" value={metrics.regionCount} description="Hyperlocal geographies in the knowledge base." accent="blue" />
        <MetricCard title="Previous Campaigns" value={metrics.campaignCount} description="Campaign records available for learning." />
        <MetricCard title="Average Engagement Rate" value={percent(metrics.avgEngagementRate)} description="Opened, clicked, or replied target share." accent="amber" />
        <MetricCard title="Average Inquiry Rate" value={percent(metrics.avgInquiryRate)} description="Targets that converted into product inquiries." accent="green" />
        <MetricCard title="Data Quality Score" value={percent(metrics.dataQualityScore)} description="Current readiness score after open data issues." accent="blue" />
      </div>

      <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {quickActions.map((action) => {
          const Icon = action.icon;
          const content = (
            <Card className="h-full bg-white/86 transition hover:-translate-y-0.5 hover:border-primary/35 hover:shadow-lg">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Icon className="h-5 w-5" />
              </div>
              <CardTitle className="mt-5 text-lg">{action.title}</CardTitle>
              <CardDescription className="mt-2 leading-6">{action.description}</CardDescription>
              {"action" in action ? (
                <form action={action.action} method="post" encType="multipart/form-data" className="mt-5 space-y-3">
                  <input type="hidden" name="purpose" value={action.purpose} />
                  <input
                    type="hidden"
                    name="csvType"
                    value={action.purpose === "Survey CSV" ? "farmer survey" : "auto-detect"}
                  />
                  <input
                    name="file"
                    type="file"
                    accept={action.accept}
                    required
                    className="block w-full rounded-xl border border-border bg-white/90 px-3 py-2 text-xs text-foreground file:mr-3 file:rounded-lg file:border-0 file:bg-primary file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-primary-foreground"
                  />
                  <button
                    type="submit"
                    className="inline-flex w-full items-center justify-center rounded-xl bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground"
                  >
                    {action.button}
                  </button>
                </form>
              ) : null}
            </Card>
          );

          if ("href" in action) {
            return (
              <Link key={action.title} href={action.href || "/data"} className="block">
                {content}
              </Link>
            );
          }

          return <div key={action.title}>{content}</div>;
        })}
      </div>

      <div className="mt-8">
        <DashboardCharts
          regionChartData={regionChartData}
          channelChartData={channelChartData}
          healthByCategory={healthByCategory}
          performanceChartData={performanceChartData}
        />
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <Card className="bg-white/88">
          <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
            <div>
              <CardTitle>Recent Uploads</CardTitle>
              <CardDescription className="mt-1">Latest onboarding files and AI mapping confidence.</CardDescription>
            </div>
            <Badge>{uploads.length} files</Badge>
          </div>
          <div className="mt-6 overflow-x-auto">
            <table className="w-full min-w-[720px] border-separate border-spacing-0 text-left text-sm">
              <thead>
                <tr className="text-xs uppercase text-foreground/48">
                  <th className="border-b border-border pb-3 font-semibold">File Name</th>
                  <th className="border-b border-border pb-3 font-semibold">Purpose</th>
                  <th className="border-b border-border pb-3 font-semibold">Rows</th>
                  <th className="border-b border-border pb-3 font-semibold">Status</th>
                  <th className="border-b border-border pb-3 font-semibold">AI Confidence</th>
                  <th className="border-b border-border pb-3 font-semibold">Imported</th>
                </tr>
              </thead>
              <tbody>
                {uploads.map((upload) => (
                  <tr key={upload.id} className="align-top">
                    <td className="border-b border-border/65 py-4 pr-4 font-medium">{upload.fileName}</td>
                    <td className="border-b border-border/65 py-4 pr-4 text-foreground/68">{upload.purpose}</td>
                    <td className="border-b border-border/65 py-4 pr-4">{upload.rows}</td>
                    <td className="border-b border-border/65 py-4 pr-4">
                      <Badge className={statusClass(upload.status)}>{upload.status}</Badge>
                    </td>
                    <td className="border-b border-border/65 py-4 pr-4">{upload.aiConfidence ? `${upload.aiConfidence}%` : "N/A"}</td>
                    <td className="border-b border-border/65 py-4">{upload.importedRows}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <Card className="bg-white/88">
          <CardTitle>Data Health</CardTitle>
          <CardDescription className="mt-1">Open quality issues and recommended fixes before campaign creation.</CardDescription>
          <div className="mt-6 grid gap-3">
            {dataHealthIssues.map((issue) => (
              <div key={issue.id} className="rounded-2xl border border-border bg-muted/35 p-4">
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-semibold text-foreground">{issue.category}</p>
                      <Badge className={issue.severity === "high" ? "bg-red-100 text-red-800" : statusClass(issue.status)}>
                        {issue.issueCount} records
                      </Badge>
                    </div>
                    <p className="mt-2 text-sm text-foreground/70">{issue.label}</p>
                    <p className="mt-2 text-sm leading-6 text-foreground/58">{issue.recommendedFix}</p>
                  </div>
                  <Badge className={statusClass(issue.status)}>{issue.status}</Badge>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card className="mt-8 bg-white/88">
        <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <CardTitle>Campaign History</CardTitle>
            <CardDescription className="mt-1">
              Past campaign performance used to benchmark future segmentation and channel recommendations.
            </CardDescription>
          </div>
          <Badge>{campaigns.length} campaigns</Badge>
        </div>
        <div className="mt-6 overflow-x-auto">
          <table className="w-full min-w-[1120px] border-separate border-spacing-0 text-left text-sm">
            <thead>
              <tr className="text-xs uppercase text-foreground/48">
                <th className="border-b border-border pb-3 font-semibold">Campaign Name</th>
                <th className="border-b border-border pb-3 font-semibold">Product</th>
                <th className="border-b border-border pb-3 font-semibold">Region</th>
                <th className="border-b border-border pb-3 font-semibold">Crop</th>
                <th className="border-b border-border pb-3 font-semibold">Channel</th>
                <th className="border-b border-border pb-3 font-semibold">Influencer</th>
                <th className="border-b border-border pb-3 font-semibold">Farmers</th>
                <th className="border-b border-border pb-3 font-semibold">Engagement</th>
                <th className="border-b border-border pb-3 font-semibold">Inquiry</th>
                <th className="border-b border-border pb-3 font-semibold">Purchase</th>
                <th className="border-b border-border pb-3 font-semibold">Status</th>
                <th className="border-b border-border pb-3 font-semibold">Date</th>
              </tr>
            </thead>
            <tbody>
              {campaigns.map((campaign) => (
                <tr key={campaign.id} className="align-top">
                  <td className="border-b border-border/65 py-4 pr-4 font-medium">{campaign.name}</td>
                  <td className="border-b border-border/65 py-4 pr-4 text-foreground/68">{campaign.product.name}</td>
                  <td className="border-b border-border/65 py-4 pr-4 text-foreground/68">
                    {campaign.region ? `${campaign.region.state}${campaign.region.district ? ` / ${campaign.region.district}` : ""}` : "All"}
                  </td>
                  <td className="border-b border-border/65 py-4 pr-4 text-foreground/68">{campaign.crop?.name || "Mixed"}</td>
                  <td className="border-b border-border/65 py-4 pr-4 text-foreground/68">{campaign.channel || "Multi-channel"}</td>
                  <td className="border-b border-border/65 py-4 pr-4 text-foreground/68">
                    {campaign.influencerCampaigns[0]?.influencer.name || "None"}
                  </td>
                  <td className="border-b border-border/65 py-4 pr-4">{campaign.farmersTargeted}</td>
                  <td className="border-b border-border/65 py-4 pr-4">{percent(campaign.engagementRate)}</td>
                  <td className="border-b border-border/65 py-4 pr-4">{percent(campaign.inquiryRate)}</td>
                  <td className="border-b border-border/65 py-4 pr-4">{percent(campaign.purchaseConversion)}</td>
                  <td className="border-b border-border/65 py-4 pr-4">
                    <Badge className={statusClass(campaign.status)}>{campaign.status}</Badge>
                  </td>
                  <td className="border-b border-border/65 py-4">
                    {campaign.launchDate ? formatDate(campaign.launchDate) : "Not scheduled"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
