import { revalidatePath } from "next/cache";
import { NextResponse } from "next/server";

import { prisma } from "@/lib/prisma";
import { influencerSchema } from "@/lib/validators";

function revalidateInfluencerViews() {
  revalidatePath("/dashboard");
  revalidatePath("/data");
  revalidatePath("/influencers");
  revalidatePath("/campaigns/create");
}

async function regionFromName(regionName?: string) {
  if (!regionName) {
    return null;
  }

  return prisma.region.upsert({
    where: {
      country_state_district_blockTaluk_village: {
        country: "India",
        state: regionName,
        district: "",
        blockTaluk: "",
        village: ""
      }
    },
    create: {
      country: "India",
      state: regionName,
      district: "",
      blockTaluk: "",
      village: ""
    },
    update: {}
  });
}

async function languageFromName(languageName?: string) {
  if (!languageName) {
    return null;
  }

  return prisma.language.upsert({
    where: { name: languageName },
    create: { name: languageName, scriptType: "Native script" },
    update: {}
  });
}

async function deleteInfluencer(influencerId: number) {
  const activations = await prisma.influencerCampaign.findMany({
    where: { influencerId },
    select: { id: true }
  });
  const activationIds = activations.map((activation) => activation.id);

  await prisma.$transaction([
    prisma.influencerPerformance.deleteMany({
      where: { influencerCampaignId: { in: activationIds } }
    }),
    prisma.influencerCampaign.deleteMany({
      where: { influencerId }
    }),
    prisma.influencer.delete({
      where: { id: influencerId }
    })
  ]);
}

export async function POST(request: Request) {
  const formData = await request.formData();
  const redirectTo = String(formData.get("redirectTo") || "/influencers");
  const action = String(formData.get("_action") || "create");
  const id = Number(formData.get("id") || 0);

  if (action === "delete") {
    if (!Number.isInteger(id) || id <= 0) {
      return NextResponse.redirect(new URL(`${redirectTo}?status=invalid-influencer`, request.url), 303);
    }

    await deleteInfluencer(id);
    revalidateInfluencerViews();
    return NextResponse.redirect(new URL(`${redirectTo}?status=influencer-deleted`, request.url), 303);
  }

  const parsed = influencerSchema.safeParse({
    name: formData.get("name"),
    channel: formData.get("channel"),
    influencerType: formData.get("influencerType"),
    region: formData.get("region"),
    primaryLanguage: formData.get("primaryLanguage"),
    primaryCropFocus: formData.get("primaryCropFocus"),
    followerCount: formData.get("followerCount"),
    reachScore: formData.get("reachScore"),
    trustScore: formData.get("trustScore"),
    engagementRate: formData.get("engagementRate"),
    contentStrength: formData.get("contentStrength"),
    costPerCampaign: formData.get("costPerCampaign"),
    contentFormat: formData.get("contentFormat"),
    contactPhone: formData.get("contactPhone"),
    contactEmail: formData.get("contactEmail"),
    commercialTerms: formData.get("commercialTerms"),
    complianceStatus: formData.get("complianceStatus"),
    status: formData.get("status")
  });

  if (!parsed.success) {
    return NextResponse.redirect(new URL(`${redirectTo}?status=validation-error`, request.url), 303);
  }

  const [region, language] = await Promise.all([
    regionFromName(parsed.data.region),
    languageFromName(parsed.data.primaryLanguage)
  ]);

  const data = {
    name: parsed.data.name,
    channel: parsed.data.channel,
    influencerType: parsed.data.influencerType,
    regionId: region?.id,
    primaryLanguageId: language?.id,
    primaryCropFocus: parsed.data.primaryCropFocus,
    followerCount: parsed.data.followerCount,
    reachScore: parsed.data.reachScore,
    trustScore: parsed.data.trustScore,
    engagementRate: parsed.data.engagementRate,
    contentStrength: parsed.data.contentStrength,
    costPerCampaign: parsed.data.costPerCampaign,
    contentFormat: parsed.data.contentFormat,
    contactPhone: parsed.data.contactPhone,
    contactEmail: parsed.data.contactEmail,
    commercialTerms: parsed.data.commercialTerms,
    complianceStatus: parsed.data.complianceStatus || "pending",
    status: parsed.data.status || "active"
  };

  if (action === "update" && Number.isInteger(id) && id > 0) {
    await prisma.influencer.update({
      where: { id },
      data
    });
  } else {
    await prisma.influencer.upsert({
      where: { name: parsed.data.name },
      create: data,
      update: data
    });
  }

  revalidateInfluencerViews();
  return NextResponse.redirect(new URL(`${redirectTo}?status=influencer-saved`, request.url), 303);
}
