import { revalidatePath } from "next/cache";
import { NextResponse } from "next/server";

import { prisma } from "@/lib/prisma";
import { productSchema } from "@/lib/validators";

function revalidateProductViews() {
  revalidatePath("/dashboard");
  revalidatePath("/data");
  revalidatePath("/products");
  revalidatePath("/campaigns/create");
}

async function deleteProduct(productId: number) {
  const campaigns = await prisma.campaign.findMany({
    where: { productId },
    select: { id: true }
  });
  const campaignIds = campaigns.map((campaign) => campaign.id);

  const influencerCampaigns = await prisma.influencerCampaign.findMany({
    where: { campaignId: { in: campaignIds } },
    select: { id: true }
  });
  const influencerCampaignIds = influencerCampaigns.map((entry) => entry.id);

  await prisma.$transaction([
    prisma.influencerPerformance.deleteMany({
      where: { influencerCampaignId: { in: influencerCampaignIds } }
    }),
    prisma.influencerCampaign.deleteMany({
      where: { campaignId: { in: campaignIds } }
    }),
    prisma.campaignResponse.deleteMany({
      where: { target: { campaignId: { in: campaignIds } } }
    }),
    prisma.campaignTarget.deleteMany({
      where: { campaignId: { in: campaignIds } }
    }),
    prisma.campaignMessage.deleteMany({
      where: { campaignId: { in: campaignIds } }
    }),
    prisma.campaign.deleteMany({
      where: { id: { in: campaignIds } }
    }),
    prisma.productCropFit.deleteMany({
      where: { productId }
    }),
    prisma.product.delete({
      where: { id: productId }
    })
  ]);
}

export async function POST(request: Request) {
  const formData = await request.formData();
  const redirectTo = String(formData.get("redirectTo") || "/products");
  const action = String(formData.get("_action") || "create");
  const id = Number(formData.get("id") || 0);

  if (action === "delete") {
    if (!Number.isInteger(id) || id <= 0) {
      return NextResponse.redirect(new URL(`${redirectTo}?status=invalid-product`, request.url), 303);
    }

    await deleteProduct(id);
    revalidateProductViews();
    return NextResponse.redirect(new URL(`${redirectTo}?status=product-deleted`, request.url), 303);
  }

  const parsed = productSchema.safeParse({
    name: formData.get("name"),
    category: formData.get("category"),
    productType: formData.get("productType"),
    sustainableFlag: formData.has("sustainableFlag"),
    organicFlag: formData.has("organicFlag"),
    pricePerUnit: formData.get("pricePerUnit"),
    unitType: formData.get("unitType"),
    activeIngredient: formData.get("activeIngredient"),
    targetPestType: formData.get("targetPestType"),
    cropStageRelevance: formData.get("cropStageRelevance"),
    positioning: formData.get("positioning"),
    status: formData.get("status")
  });

  if (!parsed.success) {
    return NextResponse.redirect(new URL(`${redirectTo}?status=validation-error`, request.url), 303);
  }

  const data = {
    ...parsed.data,
    status: parsed.data.status || "active"
  };

  if (action === "update" && Number.isInteger(id) && id > 0) {
    await prisma.product.update({
      where: { id },
      data
    });
  } else {
    await prisma.product.upsert({
      where: { name: parsed.data.name },
      create: data,
      update: data
    });
  }

  revalidateProductViews();
  return NextResponse.redirect(new URL(`${redirectTo}?status=product-saved`, request.url), 303);
}
