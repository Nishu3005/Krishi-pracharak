import { revalidatePath } from "next/cache";
import { NextResponse } from "next/server";

import { generateCampaignContent } from "@/lib/ai/campaign-generator";
import { prisma } from "@/lib/prisma";
import { generationSchema } from "@/lib/validators";

export async function POST(request: Request) {
  const json = await request.json();
  const parsed = generationSchema.safeParse(json);

  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid request." }, { status: 400 });
  }

  const [product, influencer] = await Promise.all([
    prisma.product.findUnique({
      where: { id: parsed.data.productId },
      include: { cropFits: true }
    }),
    typeof parsed.data.influencerId === "number"
      ? prisma.influencer.findUnique({ where: { id: parsed.data.influencerId } })
      : Promise.resolve(null)
  ]);

  if (!product) {
    return NextResponse.json({ error: "Product not found." }, { status: 404 });
  }

  const region = parsed.data.region
    ? await prisma.region.findFirst({ where: { state: parsed.data.region } })
    : null;
  const cropId = product.cropFits[0]?.cropId;
  const previousCampaigns = await prisma.campaign.findMany({
    where: {
      productId: product.id,
      regionId: region?.id
    },
    include: {
      targets: {
        include: { response: true }
      }
    },
    orderBy: { id: "desc" },
    take: 8
  });

  const generated = generateCampaignContent({
    product,
    segment: {
      farmerPersona: parsed.data.segment.farmerPersona || parsed.data.segment.summary,
      region: parsed.data.segment.region || parsed.data.region || "Selected market",
      mainCrop: parsed.data.segment.mainCrop || "selected crop",
      farmerNeed: parsed.data.segment.farmerNeed || parsed.data.segment.summary,
      productRelevance: parsed.data.segment.productRelevance || `${product.name} is relevant to this segment.`,
      ecosystemContext: parsed.data.segment.ecosystemContext || "Use the latest ecosystem context from segmentation.",
      outbreakWeatherTrigger: parsed.data.segment.outbreakWeatherTrigger || parsed.data.segment.triggers[0] || "Current field trigger",
      priorityScore: parsed.data.segment.priorityScore || 65,
      dataConfidenceScore: parsed.data.segment.dataConfidenceScore || 65,
      whyCreated: parsed.data.segment.whyCreated || parsed.data.segment.summary,
      ...parsed.data.segment
    },
    region: parsed.data.region,
    channel: parsed.data.channel,
    influencer,
    additionalInfo: parsed.data.additionalInfo,
    previousCampaigns
  });

  const saved = await prisma.campaign.create({
    data: {
      name: `${product.name} • ${parsed.data.segment.name}`,
      productId: product.id,
      cropId,
      regionId: region?.id,
      channel: parsed.data.channel,
      messageType: parsed.data.segment.name,
      campaignGoal: "inquiry",
      launchDate: new Date(),
      createdBy: "Krishi Pracharak",
      status: "draft",
      messages: {
        create: {
          messageVariant: "A",
          campaignBrief: generated.campaignBrief,
          whatsappText: generated.content.whatsapp,
          smsText: generated.content.sms,
          voiceScript: generated.content.voiceScript,
          videoScript: generated.content.videoScript,
          influencerScript: generated.content.influencerScript,
          fieldRepScript: generated.content.fieldRepScript,
          retailerScript: generated.content.retailerScript,
          visualPrompt: generated.content.imagePrompt,
          complianceStatus: generated.compliance.status,
          complianceNotes: generated.compliance.notes.join("\n"),
          expectedMetrics: JSON.stringify(generated.expectedPerformance),
          complianceApproved: generated.compliance.status === "Passed"
        }
      },
      influencerCampaigns: influencer
        ? {
            create: {
              influencerId: influencer.id,
              activationRole: "testimonial",
              contentFormat: parsed.data.channel || influencer.channel,
              expectedReach: influencer.reachScore,
              approvalStatus: "draft",
              notes: parsed.data.additionalInfo
            }
          }
        : undefined
    }
  });

  revalidatePath("/dashboard");
  revalidatePath("/data");

  return NextResponse.json({
    generated,
    savedCampaignId: saved.id
  });
}
