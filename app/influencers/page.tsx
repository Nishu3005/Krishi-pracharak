import { Edit3, Trash2, TrendingUp } from "lucide-react";

import { InfluencerForm } from "@/components/forms/influencer-form";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { getDataManagementData } from "@/lib/data";

export const dynamic = "force-dynamic";

function num(value: unknown) {
  if (value === null || value === undefined || value === "") {
    return 0;
  }
  return Number(value);
}

function money(value: unknown) {
  if (!value) {
    return "N/A";
  }
  return `₹${Number(value).toLocaleString("en-IN")}`;
}

function fitScore(influencer: {
  trustScore: unknown;
  engagementRate: unknown;
  reachScore: number | null;
  costPerCampaign: unknown;
}) {
  const trust = num(influencer.trustScore);
  const engagement = Math.min(100, num(influencer.engagementRate) * 8);
  const reach = Math.min(100, (influencer.reachScore || 0) / 200);
  const cost = num(influencer.costPerCampaign);
  const affordability = cost ? Math.max(15, 100 - cost / 1000) : 65;

  return Math.round(trust * 0.35 + engagement * 0.25 + reach * 0.25 + affordability * 0.15);
}

function scoreBadge(score: number) {
  if (score >= 75) return "bg-primary/12 text-primary";
  if (score >= 55) return "bg-secondary text-secondary-foreground";
  return "bg-red-100 text-red-800";
}

export default async function InfluencersPage({
  searchParams
}: {
  searchParams: { status?: string };
}) {
  const { influencers } = await getDataManagementData();

  return (
    <div>
      <PageHeader
        eyebrow="Network"
        title="Influencers"
        description="Maintain trusted agri voices and preview fit for campaign amplification."
        badge={`${influencers.length} influencers`}
      />

      {searchParams.status ? (
        <div className="mb-6 rounded-2xl border border-border bg-white/82 px-4 py-3 text-sm text-foreground/72 shadow-soft">
          Latest action: <span className="font-semibold">{searchParams.status.replaceAll("-", " ")}</span>
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[0.78fr_1.22fr]">
        <Card className="bg-white/88">
          <CardTitle>Add Influencer</CardTitle>
          <CardDescription className="mt-1">Create a profile for an agri creator, local champion, advisor, or community leader.</CardDescription>
          <div className="mt-6">
            <InfluencerForm redirectTo="/influencers" />
          </div>
        </Card>

        <Card className="bg-white/88">
          <CardTitle>Influencer List</CardTitle>
          <CardDescription className="mt-1">Audience, engagement, trust, cost, and fit overview.</CardDescription>
          <div className="mt-6 overflow-x-auto">
            <table className="w-full min-w-[1180px] border-separate border-spacing-0 text-left text-sm">
              <thead>
                <tr className="text-xs uppercase text-foreground/48">
                  <th className="border-b border-border pb-3 font-semibold">Influencer</th>
                  <th className="border-b border-border pb-3 font-semibold">Type</th>
                  <th className="border-b border-border pb-3 font-semibold">Region</th>
                  <th className="border-b border-border pb-3 font-semibold">Language</th>
                  <th className="border-b border-border pb-3 font-semibold">Crop Expertise</th>
                  <th className="border-b border-border pb-3 font-semibold">Audience</th>
                  <th className="border-b border-border pb-3 font-semibold">Engagement</th>
                  <th className="border-b border-border pb-3 font-semibold">Trust</th>
                  <th className="border-b border-border pb-3 font-semibold">Cost</th>
                  <th className="border-b border-border pb-3 font-semibold">Format</th>
                  <th className="border-b border-border pb-3 font-semibold">Fit Score</th>
                </tr>
              </thead>
              <tbody>
                {influencers.map((influencer) => {
                  const score = fitScore(influencer);
                  return (
                    <tr key={influencer.id} className="align-top">
                      <td className="border-b border-border/65 py-4 pr-4">
                        <p className="font-semibold">{influencer.name}</p>
                        <p className="mt-1 text-xs text-foreground/55">{influencer.channel}</p>
                      </td>
                      <td className="border-b border-border/65 py-4 pr-4 text-foreground/68">{influencer.influencerType || "N/A"}</td>
                      <td className="border-b border-border/65 py-4 pr-4 text-foreground/68">{influencer.region?.state || "Multi-region"}</td>
                      <td className="border-b border-border/65 py-4 pr-4 text-foreground/68">{influencer.language?.name || "N/A"}</td>
                      <td className="border-b border-border/65 py-4 pr-4 text-foreground/68">{influencer.primaryCropFocus || "General"}</td>
                      <td className="border-b border-border/65 py-4 pr-4">{(influencer.reachScore || 0).toLocaleString("en-IN")}</td>
                      <td className="border-b border-border/65 py-4 pr-4">{influencer.engagementRate ? `${influencer.engagementRate}%` : "N/A"}</td>
                      <td className="border-b border-border/65 py-4 pr-4">{influencer.trustScore ? `${influencer.trustScore}%` : "N/A"}</td>
                      <td className="border-b border-border/65 py-4 pr-4">{money(influencer.costPerCampaign)}</td>
                      <td className="border-b border-border/65 py-4 pr-4 text-foreground/68">{influencer.contentFormat || influencer.contentStrength || "N/A"}</td>
                      <td className="border-b border-border/65 py-4">
                        <Badge className={scoreBadge(score)}>{score}/100</Badge>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-2">
        {influencers.map((influencer) => {
          const score = fitScore(influencer);
          return (
            <Card key={influencer.id} className="bg-white/88">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <Edit3 className="h-5 w-5 text-primary" />
                    <CardTitle>Edit {influencer.name}</CardTitle>
                  </div>
                  <CardDescription className="mt-1">Update profile details or remove this influencer.</CardDescription>
                </div>
                <form action="/api/influencers" method="post">
                  <input type="hidden" name="redirectTo" value="/influencers" />
                  <input type="hidden" name="id" value={influencer.id} />
                  <input type="hidden" name="_action" value="delete" />
                  <button
                    type="submit"
                    className="inline-flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-800"
                  >
                    <Trash2 className="h-4 w-4" />
                    Delete
                  </button>
                </form>
              </div>

              <div className="mt-5 rounded-2xl border border-border bg-muted/35 p-4">
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-primary" />
                  <p className="font-semibold">Influencer Fit Score Preview</p>
                  <Badge className={scoreBadge(score)}>{score}/100</Badge>
                </div>
                <p className="mt-2 text-sm leading-6 text-foreground/62">
                  Fit combines trust score, engagement rate, audience size, and affordability. It is a rule-based preview for campaign planning.
                </p>
              </div>

              <div className="mt-6">
                <InfluencerForm redirectTo="/influencers" influencer={influencer} compact />
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
