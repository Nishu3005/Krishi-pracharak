import { prisma } from "@/lib/prisma";
import { ensureSeedData } from "@/lib/seed";

function regionLabel(region?: { state: string; district: string | null } | null) {
  if (!region) {
    return "Unassigned";
  }
  return region.district ? `${region.state} / ${region.district}` : region.state;
}

function ratioPercent(numerator: number, denominator: number) {
  if (!denominator) {
    return 0;
  }
  return Math.round((numerator / denominator) * 100);
}

function average(values: number[]) {
  if (!values.length) {
    return 0;
  }
  return Math.round(values.reduce((sum, value) => sum + value, 0) / values.length);
}

export async function getDashboardData() {
  await ensureSeedData();

  const [
    farmerCount,
    productCount,
    influencerCount,
    regionCount,
    campaigns,
    uploads,
    dataHealthIssues
  ] = await Promise.all([
    prisma.farmer.count(),
    prisma.product.count(),
    prisma.influencer.count(),
    prisma.region.count(),
    prisma.campaign.findMany({
      orderBy: { id: "desc" },
      include: {
        product: true,
        crop: true,
        region: true,
        targets: {
          include: { response: true }
        },
        influencerCampaigns: {
          include: { influencer: true }
        }
      }
    }),
    prisma.uploadRecord.findMany({
      orderBy: { uploadedAt: "desc" },
      take: 6
    }),
    prisma.dataHealthIssue.findMany({
      orderBy: [{ severity: "desc" }, { issueCount: "desc" }]
    })
  ]);

  const campaignRows = campaigns.map((campaign) => {
    const targetCount = campaign.targets.length;
    const responses = campaign.targets.map((target) => target.response).filter(Boolean);
    const engagementCount = responses.filter(
      (response) => response?.openedFlag || response?.clickedFlag || response?.repliedFlag
    ).length;
    const inquiryCount = responses.filter((response) => response?.inquiryFlag).length;
    const purchaseCount = responses.filter((response) => response?.purchaseFlag).length;

    return {
      ...campaign,
      farmersTargeted: targetCount,
      engagementRate: ratioPercent(engagementCount, targetCount),
      inquiryRate: ratioPercent(inquiryCount, targetCount),
      purchaseConversion: ratioPercent(purchaseCount, targetCount)
    };
  });

  const avgEngagementRate = average(campaignRows.map((campaign) => campaign.engagementRate));
  const avgInquiryRate = average(campaignRows.map((campaign) => campaign.inquiryRate));
  const totalIssueCount = dataHealthIssues.reduce((sum, issue) => sum + issue.issueCount, 0);
  const dataQualityScore = Math.max(0, Math.min(100, 100 - totalIssueCount));

  const campaignsByRegion = campaignRows.reduce<Record<string, number>>((acc, campaign) => {
    const key = regionLabel(campaign.region);
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

  const campaignsByChannel = campaignRows.reduce<Record<string, number>>((acc, campaign) => {
    const key = campaign.channel || "Unassigned";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

  const healthByCategory = dataHealthIssues.map((issue) => ({
    name: issue.category,
    total: issue.issueCount
  }));

  const performanceChartData = campaignRows.map((campaign) => ({
    name: campaign.name.length > 18 ? `${campaign.name.slice(0, 18)}...` : campaign.name,
    engagement: campaign.engagementRate,
    inquiry: campaign.inquiryRate,
    purchase: campaign.purchaseConversion
  }));

  return {
    metrics: {
      farmerCount,
      productCount,
      influencerCount,
      regionCount,
      campaignCount: campaignRows.length,
      avgEngagementRate,
      avgInquiryRate,
      dataQualityScore
    },
    campaigns: campaignRows,
    uploads,
    dataHealthIssues,
    regionChartData: Object.entries(campaignsByRegion).map(([name, total]) => ({
      name,
      total
    })),
    channelChartData: Object.entries(campaignsByChannel).map(([name, total]) => ({
      name,
      total
    })),
    healthByCategory,
    performanceChartData
  };
}

export async function getDataManagementData() {
  await ensureSeedData();

  const [products, influencers, farmers, campaigns, ingestionJobs] = await Promise.all([
    prisma.product.findMany({
      orderBy: { id: "desc" },
      include: {
        cropFits: {
          include: { crop: true },
          orderBy: { relevanceScore: "desc" }
        }
      }
    }),
    prisma.influencer.findMany({
      orderBy: { id: "desc" },
      include: { region: true, language: true }
    }),
    prisma.farmer.findMany({
      orderBy: { createdAt: "desc" },
      include: { region: true, primaryCrop: true, preferredLanguage: true },
      take: 8
    }),
    prisma.campaign.findMany({
      orderBy: { id: "desc" },
      include: {
        product: true,
        region: true,
        messages: true,
        influencerCampaigns: {
          include: { influencer: true }
        }
      },
      take: 8
    }),
    prisma.dataIngestionJob.findMany({
      orderBy: { createdAt: "desc" },
      include: { uploadedFile: true },
      take: 6
    })
  ]);

  return { products, influencers, farmers, campaigns, ingestionJobs };
}

export async function getIngestionJobReview(jobId?: string) {
  const id = Number(jobId);
  if (!Number.isInteger(id)) {
    return null;
  }

  return prisma.dataIngestionJob.findUnique({
    where: { id },
    include: {
      uploadedFile: true,
      schemaMappings: {
        orderBy: { id: "asc" }
      },
      stagingRecords: {
        orderBy: { rowNumber: "asc" },
        take: 20
      },
      validationErrors: {
        orderBy: [{ rowNumber: "asc" }, { severity: "asc" }]
      }
    }
  });
}

export async function getCampaignBuilderData() {
  await ensureSeedData();

  const [products, influencers] = await Promise.all([
    prisma.product.findMany({
      orderBy: { name: "asc" },
      select: {
        id: true,
        name: true,
        category: true,
        positioning: true
      }
    }),
    prisma.influencer.findMany({
      orderBy: { name: "asc" },
      select: {
        id: true,
        name: true,
        channel: true
      }
    })
  ]);

  return { products, influencers };
}
