import { revalidatePath } from "next/cache";
import { NextResponse } from "next/server";

import { prisma } from "@/lib/prisma";

type EntityRow = Record<string, unknown>;
type EntityGroups = Record<string, EntityRow[]>;
type ImportableRow = {
  rowNumber: number;
  mapped: Record<string, unknown>;
  validationStatus: string;
};

function cleanText(value: unknown) {
  const text = String(value ?? "").trim();
  return text || undefined;
}

function toNumber(value: unknown) {
  const cleaned = String(value ?? "").replace(/[%₹,$]/g, "").trim();
  if (!cleaned) return undefined;
  const numeric = Number(cleaned);
  return Number.isFinite(numeric) ? numeric : undefined;
}

function toInt(value: unknown) {
  const numeric = toNumber(value);
  return numeric === undefined ? undefined : Math.round(numeric);
}

function toBoolean(value: unknown) {
  if (typeof value === "boolean") return value;
  const normalized = String(value ?? "").trim().toLowerCase();
  return ["yes", "true", "1", "y", "whatsapp", "smartphone"].includes(normalized);
}

function dateOrNow(value: unknown) {
  const text = cleanText(value);
  if (!text) return new Date();
  const date = new Date(text);
  return Number.isNaN(date.getTime()) ? new Date() : date;
}

function groupsForRow(row: ImportableRow): EntityGroups {
  const entities = row.mapped.entities;
  if (entities && typeof entities === "object" && !Array.isArray(entities)) {
    return entities as EntityGroups;
  }

  // Compatibility for older staged rows that used flat "table.column" keys.
  const groups: EntityGroups = {};
  for (const [key, value] of Object.entries(row.mapped)) {
    const [table, field] = key.split(".");
    if (!table || !field) continue;
    groups[table] ??= [{}];
    groups[table][0][field] = value;
  }
  return groups;
}

function first(groups: EntityGroups, table: string) {
  return groups[table]?.[0];
}

async function upsertRegion(row?: EntityRow | null) {
  const state = cleanText(row?.state) || "Unknown";
  const district = cleanText(row?.district) || "";
  const village = cleanText(row?.village) || "";
  return prisma.region.upsert({
    where: {
      country_state_district_blockTaluk_village: {
        country: "India",
        state,
        district,
        blockTaluk: "",
        village
      }
    },
    create: {
      country: "India",
      state,
      district,
      blockTaluk: "",
      village
    },
    update: {}
  });
}

async function upsertLanguage(row?: EntityRow | null) {
  const name = cleanText(row?.languageName);
  if (!name) return null;
  return prisma.language.upsert({
    where: { name },
    create: { name, scriptType: "Native script" },
    update: {}
  });
}

async function upsertCrop(row?: EntityRow | null) {
  const name = cleanText(row?.cropName);
  if (!name) return null;
  return prisma.crop.upsert({
    where: { name },
    create: {
      name,
      category: cleanText(row?.category) || "Imported crop",
      season: cleanText(row?.season) || "Kharif"
    },
    update: {
      category: cleanText(row?.category),
      season: cleanText(row?.season)
    }
  });
}

async function upsertProduct(row?: EntityRow | null) {
  const name = cleanText(row?.productName);
  if (!name) return null;
  return prisma.product.upsert({
    where: { name },
    create: {
      name,
      category: cleanText(row?.productCategory) || "Crop solution",
      productType: cleanText(row?.productType),
      sustainableFlag: toBoolean(row?.sustainableFlag),
      organicFlag: toBoolean(row?.organicFlag),
      pricePerUnit: toNumber(row?.pricePerUnit),
      unitType: cleanText(row?.unitType),
      activeIngredient: cleanText(row?.activeIngredient),
      targetPestType: cleanText(row?.targetPestType),
      cropStageRelevance: cleanText(row?.cropStageRelevance),
      positioning: cleanText(row?.description),
      status: cleanText(row?.status) || "active"
    },
    update: {
      category: cleanText(row?.productCategory) || "Crop solution",
      productType: cleanText(row?.productType),
      sustainableFlag: toBoolean(row?.sustainableFlag),
      organicFlag: toBoolean(row?.organicFlag),
      pricePerUnit: toNumber(row?.pricePerUnit),
      unitType: cleanText(row?.unitType),
      activeIngredient: cleanText(row?.activeIngredient),
      targetPestType: cleanText(row?.targetPestType),
      cropStageRelevance: cleanText(row?.cropStageRelevance),
      positioning: cleanText(row?.description),
      status: cleanText(row?.status) || "active"
    }
  });
}

async function upsertFarmer(row: EntityRow, params: { regionId: number; cropId?: number; languageId?: number }) {
  const name = cleanText(row.farmerName);
  if (!name) return null;
  const existing = await prisma.farmer.findFirst({
    where: {
      name,
      regionId: params.regionId
    }
  });
  const data = {
    name,
    regionId: params.regionId,
    primaryCropId: params.cropId,
    landSizeAcres: toNumber(row.landSizeAcres),
    annualIncomeBand: cleanText(row.annualIncomeBand),
    literacyLevel: cleanText(row.literacyLevel),
    smartphoneUser: toBoolean(row.smartphoneUser),
    featurePhoneUser: toBoolean(row.featurePhoneUser),
    preferredLanguageId: params.languageId,
    gender: cleanText(row.gender),
    ageBand: cleanText(row.ageBand),
    farmerSegment: cleanText(row.farmerSegment),
    trustChannel: cleanText(row.trustChannel)
  };
  if (existing) {
    return prisma.farmer.update({
      where: { id: existing.id },
      data
    });
  }
  return prisma.farmer.create({ data });
}

async function upsertInfluencer(row: EntityRow, params: { regionId?: number; languageId?: number }) {
  const name = cleanText(row.influencerName);
  if (!name) return null;
  return prisma.influencer.upsert({
    where: { name },
    create: {
      name,
      influencerType: cleanText(row.influencerType),
      regionId: params.regionId,
      primaryLanguageId: params.languageId,
      primaryCropFocus: cleanText(row.cropExpertise),
      channel: cleanText(row.platform) || "WhatsApp",
      followerCount: toInt(row.followerCount),
      reachScore: toInt(row.estimatedFarmerReach),
      trustScore: toNumber(row.trustScore),
      engagementRate: toNumber(row.engagementRate),
      contentStrength: cleanText(row.contentStrength),
      costPerCampaign: toNumber(row.costPerCampaign),
      contentFormat: cleanText(row.contentFormat),
      contactPhone: cleanText(row.contactPhone),
      contactEmail: cleanText(row.contactEmail),
      commercialTerms: cleanText(row.commercialTerms),
      complianceStatus: cleanText(row.complianceStatus) || "pending",
      status: cleanText(row.status) || "active"
    },
    update: {
      influencerType: cleanText(row.influencerType),
      regionId: params.regionId,
      primaryLanguageId: params.languageId,
      primaryCropFocus: cleanText(row.cropExpertise),
      channel: cleanText(row.platform) || "WhatsApp",
      followerCount: toInt(row.followerCount),
      reachScore: toInt(row.estimatedFarmerReach),
      trustScore: toNumber(row.trustScore),
      engagementRate: toNumber(row.engagementRate),
      contentStrength: cleanText(row.contentStrength),
      costPerCampaign: toNumber(row.costPerCampaign),
      contentFormat: cleanText(row.contentFormat),
      contactPhone: cleanText(row.contactPhone),
      contactEmail: cleanText(row.contactEmail),
      commercialTerms: cleanText(row.commercialTerms),
      complianceStatus: cleanText(row.complianceStatus) || "pending",
      status: cleanText(row.status) || "active"
    }
  });
}

async function upsertProductCropFit(row: EntityRow, params: { productId?: number; cropId?: number; productRow?: EntityRow | null }) {
  if (!params.productId || !params.cropId) return;
  const outbreakType = cleanText(row.outbreakType) || cleanText(params.productRow?.targetPestType) || "";
  const outbreakName = cleanText(row.outbreakName) || "";
  const recommendedStage = cleanText(row.recommendedStage) || cleanText(params.productRow?.cropStageRelevance) || "";
  await prisma.productCropFit.upsert({
    where: {
      productId_cropId_outbreakType_outbreakName_recommendedStage: {
        productId: params.productId,
        cropId: params.cropId,
        outbreakType,
        outbreakName,
        recommendedStage
      }
    },
    create: {
      productId: params.productId,
      cropId: params.cropId,
      outbreakType,
      outbreakName,
      recommendedStage,
      relevanceScore: toNumber(row.relevanceScore) || 75,
      approvedFlag: true
    },
    update: {
      relevanceScore: toNumber(row.relevanceScore) || 75,
      approvedFlag: true
    }
  });
}

async function upsertFarmerChildren(groups: EntityGroups, farmerId: number, cropId?: number) {
  for (const row of groups.channel_preferences || []) {
    const existing = await prisma.channelPreference.findFirst({ where: { farmerId } });
    const data = {
      farmerId,
      whatsappOptIn: toBoolean(row.whatsappOptIn),
      smsOptIn: toBoolean(row.smsOptIn),
      voiceCallOptIn: toBoolean(row.voiceCallOptIn),
      retailerInfluenceScore: toNumber(row.retailerInfluenceScore),
      fieldRepInfluenceScore: toNumber(row.fieldRepInfluenceScore),
      preferredContactTime: cleanText(row.preferredContactTime),
      engagementScore: toNumber(row.engagementScore) || 50
    };
    if (existing) {
      await prisma.channelPreference.update({ where: { id: existing.id }, data });
    } else {
      await prisma.channelPreference.create({ data });
    }
  }

  if (cropId) {
    for (const row of groups.farming_practices || []) {
      await prisma.farmingPractice.create({
        data: {
          farmerId,
          cropId,
          farmingType: cleanText(row.farmingType),
          sowingPeriod: cleanText(row.sowingPeriod),
          irrigationMethod: cleanText(row.irrigationMethod),
          mechanizationLevel: cleanText(row.mechanizationLevel),
          fertilizerPractice: cleanText(row.fertilizerPractice),
          pesticidePractice: cleanText(row.pesticidePractice),
          laborDependency: cleanText(row.laborDependency),
          cultivationFrequency: cleanText(row.cultivationFrequency)
        }
      });
    }
  }

  for (const row of groups.farmer_assets || []) {
    const assetType = cleanText(row.assetType);
    if (!assetType) continue;
    await prisma.farmerAsset.create({
      data: {
        farmerId,
        assetType,
        assetName: cleanText(row.assetName),
        ownershipType: cleanText(row.ownershipType),
        quantity: toInt(row.quantity) || 1,
        usableFlag: row.usableFlag === undefined ? true : toBoolean(row.usableFlag)
      }
    });
  }
}

async function importCampaign(groups: EntityGroups, params: { productId?: number; cropId?: number; regionId?: number; farmerId?: number }) {
  const campaignRow = first(groups, "campaigns");
  const campaignName = cleanText(campaignRow?.campaignName);
  if (!campaignName || !params.productId) return;
  const campaign = await prisma.campaign.create({
    data: {
      name: campaignName,
      productId: params.productId,
      cropId: params.cropId,
      regionId: params.regionId,
      channel: cleanText(campaignRow?.channel),
      messageType: "Imported history",
      campaignGoal: "Learning",
      launchDate: dateOrNow(campaignRow?.launchDate),
      createdBy: "CSV import",
      status: cleanText(campaignRow?.status) || "closed"
    }
  });

  const aggregateFarmerId =
    params.farmerId ||
    (
      await prisma.farmer.create({
        data: {
          name: `${campaignName} aggregate target`,
          regionId: params.regionId || (await upsertRegion({ state: "Imported" })).id,
          primaryCropId: params.cropId,
          farmerSegment: "Imported campaign aggregate"
        }
      })
    ).id;
  const targetRow = first(groups, "campaign_targets");
  const target = await prisma.campaignTarget.create({
    data: {
      campaignId: campaign.id,
      farmerId: aggregateFarmerId,
      recommendedChannel: cleanText(targetRow?.recommendedChannel) || cleanText(campaignRow?.channel),
      priorityScore: toNumber(targetRow?.priorityScore) || toNumber(targetRow?.farmersTargeted) || 50,
      status: "responded"
    }
  });
  const responseRow = first(groups, "campaign_responses");
  await prisma.campaignResponse.create({
    data: {
      targetId: target.id,
      deliveryStatus: "delivered",
      openedFlag: Boolean((toNumber(responseRow?.engagementRate) || 0) > 0),
      inquiryFlag: Boolean((toNumber(responseRow?.inquiryRate) || 0) > 0),
      purchaseFlag: Boolean((toNumber(responseRow?.purchaseConversion) || 0) > 0),
      responseDate: new Date(),
      notes: `Imported metrics: engagement ${responseRow?.engagementRate ?? "N/A"}%, inquiry ${responseRow?.inquiryRate ?? "N/A"}%, purchase ${responseRow?.purchaseConversion ?? "N/A"}%.`
    }
  });
}

async function importExtractedRow(row: ImportableRow) {
  const groups = groupsForRow(row);
  const region = first(groups, "regions") ? await upsertRegion(first(groups, "regions")) : null;
  const language = first(groups, "languages") ? await upsertLanguage(first(groups, "languages")) : null;
  const cropSource = first(groups, "crops") || first(groups, "product_crop_fit") || first(groups, "campaigns");
  const crop = cropSource ? await upsertCrop({ cropName: cropSource.cropName, category: cropSource.category, season: cropSource.season }) : null;
  const productRow = first(groups, "products") || first(groups, "campaigns");
  const product = productRow ? await upsertProduct({ ...productRow, productName: productRow.productName }) : null;

  if (product && crop) {
    const fitRows = groups.product_crop_fit?.length ? groups.product_crop_fit : [{}];
    for (const fitRow of fitRows) {
      await upsertProductCropFit(fitRow, { productId: product.id, cropId: crop.id, productRow: first(groups, "products") });
    }
  }

  let farmerId: number | undefined;
  for (const farmerRow of groups.farmers || []) {
    const resolvedRegion = region || (await upsertRegion(first(groups, "regions")));
    const farmer = await upsertFarmer(farmerRow, {
      regionId: resolvedRegion.id,
      cropId: crop?.id,
      languageId: language?.id
    });
    if (farmer) {
      farmerId = farmer.id;
      await upsertFarmerChildren(groups, farmer.id, crop?.id);
    }
  }

  for (const influencerRow of groups.influencers || []) {
    const resolvedRegion = region || (first(groups, "regions") ? await upsertRegion(first(groups, "regions")) : null);
    await upsertInfluencer(influencerRow, {
      regionId: resolvedRegion?.id,
      languageId: language?.id
    });
  }

  if (first(groups, "campaigns")) {
    await importCampaign(groups, {
      productId: product?.id,
      cropId: crop?.id,
      regionId: region?.id,
      farmerId
    });
  }
}

export async function POST(request: Request, { params }: { params: { jobId: string } }) {
  const jobId = Number(params.jobId);
  if (!Number.isInteger(jobId)) {
    return NextResponse.redirect(new URL("/data?status=invalid-job", request.url), 303);
  }

  const formData = await request.formData();
  const confirmWarnings = formData.get("confirmWarnings") === "on";
  const job = await prisma.dataIngestionJob.findUnique({
    where: { id: jobId },
    include: {
      uploadedFile: true,
      stagingRecords: {
        orderBy: { rowNumber: "asc" }
      }
    }
  });

  if (!job) {
    return NextResponse.redirect(new URL("/data?status=job-not-found", request.url), 303);
  }
  if (job.status === "imported") {
    return NextResponse.redirect(new URL(`/data?jobId=${job.id}&status=already-imported`, request.url), 303);
  }
  if (job.status === "failed" || job.status === "rejected") {
    return NextResponse.redirect(new URL(`/data?jobId=${job.id}&status=not-importable`, request.url), 303);
  }

  const warningRows = job.stagingRecords.filter((record) => record.validationStatus === "warning");
  if (warningRows.length && !confirmWarnings) {
    return NextResponse.redirect(new URL(`/data?jobId=${job.id}&status=confirm-warnings-required`, request.url), 303);
  }

  const rows = job.stagingRecords
    .filter((record) => record.validationStatus === "valid" || (confirmWarnings && record.validationStatus === "warning"))
    .map((record) => ({
      rowNumber: record.rowNumber,
      validationStatus: record.validationStatus,
      mapped: JSON.parse(record.mappedJson) as Record<string, unknown>
    }));

  let importedRows = 0;
  for (const row of rows) {
    await importExtractedRow(row);
    importedRows += 1;
  }

  await prisma.stagingRecord.updateMany({
    where: {
      jobId: job.id,
      validationStatus: confirmWarnings ? { in: ["valid", "warning"] } : "valid"
    },
    data: { importedFlag: true }
  });

  await prisma.dataIngestionJob.update({
    where: { id: job.id },
    data: {
      status: "imported",
      approvedAt: new Date(),
      validRows: importedRows
    }
  });

  await prisma.uploadedFile.update({
    where: { id: job.uploadedFileId },
    data: { status: "imported" }
  });

  await prisma.uploadRecord.create({
    data: {
      fileName: job.uploadedFile.originalFileName,
      purpose: job.uploadedFile.uploadPurpose,
      rows: job.totalRows,
      status: "Imported",
      aiConfidence: job.aiConfidence,
      importedRows
    }
  });

  revalidatePath("/dashboard");
  revalidatePath("/data");
  revalidatePath("/products");
  revalidatePath("/influencers");
  revalidatePath("/campaigns/create");

  return NextResponse.redirect(
    new URL(`/data?jobId=${job.id}&status=import-approved&count=${importedRows}`, request.url),
    303
  );
}
