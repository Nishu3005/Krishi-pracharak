const { PrismaClient } = require("@prisma/client");

const prisma = new PrismaClient();

async function main() {
  await prisma.influencerPerformance.deleteMany();
  await prisma.stagingRecord.deleteMany();
  await prisma.schemaMapping.deleteMany();
  await prisma.dataIngestionJob.deleteMany();
  await prisma.uploadedFile.deleteMany();
  await prisma.dataHealthIssue.deleteMany();
  await prisma.uploadRecord.deleteMany();
  await prisma.influencerCampaign.deleteMany();
  await prisma.campaignResponse.deleteMany();
  await prisma.campaignTarget.deleteMany();
  await prisma.campaignMessage.deleteMany();
  await prisma.campaign.deleteMany();
  await prisma.retailer.deleteMany();
  await prisma.channelPreference.deleteMany();
  await prisma.farmerAsset.deleteMany();
  await prisma.farmingPractice.deleteMany();
  await prisma.farmer.deleteMany();
  await prisma.outbreak.deleteMany();
  await prisma.ecosystemCondition.deleteMany();
  await prisma.productCropFit.deleteMany();
  await prisma.influencer.deleteMany();
  await prisma.product.deleteMany();
  await prisma.crop.deleteMany();
  await prisma.language.deleteMany();
  await prisma.region.deleteMany();

  const marathi = await prisma.language.create({
    data: { name: "Marathi", scriptType: "Native script" }
  });
  const hindi = await prisma.language.create({
    data: { name: "Hindi", scriptType: "Native script" }
  });

  const maharashtra = await prisma.region.create({
    data: {
      country: "India",
      state: "Maharashtra",
      district: "Akola",
      blockTaluk: "",
      village: "",
      agroClimaticZone: "Central Plateau"
    }
  });
  const bihar = await prisma.region.create({
    data: {
      country: "India",
      state: "Bihar",
      district: "Begusarai",
      blockTaluk: "",
      village: "",
      agroClimaticZone: "Middle Gangetic Plains"
    }
  });

  const cotton = await prisma.crop.create({
    data: {
      name: "Cotton",
      category: "Cash crop",
      season: "Kharif",
      averageDurationDays: 165,
      typicalGrowthStages: "Sowing, vegetative, flowering, boll formation, harvest"
    }
  });
  const maize = await prisma.crop.create({
    data: {
      name: "Maize",
      category: "Cereal",
      season: "Kharif",
      averageDurationDays: 110,
      typicalGrowthStages: "Sowing, vegetative, tasseling, grain filling, harvest"
    }
  });

  const cropShield = await prisma.product.create({
    data: {
      name: "CropShield Pro",
      category: "Insecticide",
      productType: "Chemical",
      pricePerUnit: 850,
      unitType: "litre",
      activeIngredient: "Lambda-cyhalothrin",
      targetPestType: "Insect",
      cropStageRelevance: "Vegetative to flowering",
      positioning: "High-efficacy pest control with low spray complexity",
      status: "active"
    }
  });
  const rootRise = await prisma.product.create({
    data: {
      name: "RootRise Max",
      category: "Seed",
      productType: "Hybrid seed",
      sustainableFlag: true,
      pricePerUnit: 1350,
      unitType: "packet",
      activeIngredient: "Hybrid maize genetics",
      targetPestType: "Stress tolerance",
      cropStageRelevance: "Sowing",
      positioning: "Higher vigor for erratic rainfall conditions",
      status: "active"
    }
  });

  await prisma.productCropFit.createMany({
    data: [
      {
        productId: cropShield.id,
        cropId: cotton.id,
        outbreakType: "Pest",
        outbreakName: "Pink bollworm",
        recommendedStage: "Flowering",
        relevanceScore: 92,
        approvedFlag: true
      },
      {
        productId: rootRise.id,
        cropId: maize.id,
        outbreakType: "Nutrient issue",
        outbreakName: "Early vigor stress",
        recommendedStage: "Sowing",
        relevanceScore: 88,
        approvedFlag: true
      }
    ]
  });

  const ramesh = await prisma.farmer.create({
    data: {
      name: "Ramesh Patil",
      regionId: maharashtra.id,
      primaryCropId: cotton.id,
      landSizeAcres: 6,
      annualIncomeBand: "Medium",
      literacyLevel: "Moderate",
      smartphoneUser: true,
      preferredLanguageId: marathi.id,
      ageBand: "31-45",
      farmerSegment: "Progressive smallholder",
      trustChannel: "WhatsApp"
    }
  });
  const anita = await prisma.farmer.create({
    data: {
      name: "Anita Devi",
      regionId: bihar.id,
      primaryCropId: maize.id,
      landSizeAcres: 3,
      annualIncomeBand: "Low",
      literacyLevel: "Low",
      featurePhoneUser: true,
      preferredLanguageId: hindi.id,
      ageBand: "31-45",
      farmerSegment: "Price-sensitive smallholder",
      trustChannel: "Voice call"
    }
  });

  await prisma.channelPreference.createMany({
    data: [
      {
        farmerId: ramesh.id,
        whatsappOptIn: true,
        smsOptIn: true,
        retailerInfluenceScore: 62,
        fieldRepInfluenceScore: 70,
        preferredContactTime: "Morning",
        engagementScore: 78
      },
      {
        farmerId: anita.id,
        smsOptIn: true,
        voiceCallOptIn: true,
        retailerInfluenceScore: 58,
        fieldRepInfluenceScore: 61,
        preferredContactTime: "Afternoon",
        engagementScore: 45
      }
    ]
  });

  await prisma.farmingPractice.create({
    data: {
      farmerId: ramesh.id,
      cropId: cotton.id,
      farmingType: "Mixed",
      sowingPeriod: "Normal",
      irrigationMethod: "Borewell",
      mechanizationLevel: "Medium",
      fertilizerPractice: "Mixed",
      pesticidePractice: "Need-based",
      laborDependency: "Mixed",
      cultivationFrequency: "Seasonal"
    }
  });
  await prisma.farmerAsset.create({
    data: {
      farmerId: ramesh.id,
      assetType: "Sprayer",
      assetName: "Battery sprayer",
      ownershipType: "Owned",
      quantity: 1,
      usableFlag: true
    }
  });

  await prisma.ecosystemCondition.create({
    data: {
      regionId: maharashtra.id,
      observationDate: new Date("2026-05-01"),
      temperatureAvg: 32,
      rainfallMm: 18,
      humidityPercent: 74,
      soilType: "Black soil",
      soilPh: 7.2,
      soilMoisture: 62,
      irrigationType: "Borewell",
      weatherSummary: "Humid",
      riskLevel: "High"
    }
  });
  const outbreak = await prisma.outbreak.create({
    data: {
      regionId: maharashtra.id,
      cropId: cotton.id,
      outbreakType: "Pest",
      outbreakName: "Pink bollworm",
      severity: "High",
      detectedDate: new Date("2026-05-05"),
      source: "Field survey",
      symptoms: "Boll damage and larvae sightings reported in demo plots.",
      recommendationWindowDays: 10,
      activeFlag: true
    }
  });

  await prisma.retailer.create({
    data: {
      name: "Akola Agri Inputs",
      regionId: maharashtra.id,
      contactPerson: "Mahesh Kulkarni",
      phone: "+91 90000 00000",
      majorCropsServed: "Cotton, soybean",
      keyProductsStocked: "CropShield Pro",
      influenceScore: 78
    }
  });

  const influencer = await prisma.influencer.create({
    data: {
      name: "Dr. Kavya Fields",
      influencerType: "Agronomist creator",
      regionId: maharashtra.id,
      primaryLanguageId: marathi.id,
      primaryCropFocus: "Cotton",
      channel: "YouTube",
      followerCount: 42000,
      reachScore: 15000,
      trustScore: 82,
      engagementRate: 9.5,
      contentStrength: "Field demo videos and WhatsApp voice notes",
      costPerCampaign: 25000,
      contentFormat: "Short video",
      commercialTerms: "Field demo honorarium",
      complianceStatus: "approved",
      status: "active"
    }
  });

  const campaign = await prisma.campaign.create({
    data: {
      name: "Cotton Pest Control Sprint",
      productId: cropShield.id,
      cropId: cotton.id,
      regionId: maharashtra.id,
      outbreakId: outbreak.id,
      languageId: marathi.id,
      channel: "WhatsApp",
      messageType: "Advisory",
      campaignGoal: "Inquiry",
      launchDate: new Date("2026-05-12"),
      endDate: new Date("2026-05-24"),
      createdBy: "Krishi Pracharak",
      status: "draft"
    }
  });

  await prisma.campaignMessage.create({
    data: {
      campaignId: campaign.id,
      messageVariant: "A",
      whatsappText: "Pink bollworm pressure is rising in Akola. Ask your retailer about CropShield Pro before flowering damage spreads.",
      smsText: "CropShield Pro: act early against cotton pest pressure. Visit your nearest retailer this week.",
      voiceScript: "Namaskar. Pest pressure is high in nearby cotton fields. Ask for CropShield Pro guidance today.",
      fieldRepScript: "Show local pest pressure, explain dose simplicity, and book demo visits for high-acreage growers.",
      retailerScript: "Use local proof and demo booking to convert growers asking about bollworm control.",
      visualPrompt: "Cotton field close-up with pest-risk warning and retailer call-to-action.",
      complianceApproved: false
    }
  });
  const target = await prisma.campaignTarget.create({
    data: {
      campaignId: campaign.id,
      farmerId: ramesh.id,
      recommendedChannel: "WhatsApp",
      priorityScore: 84,
      predictedEngagementProbability: 72,
      predictedInquiryProbability: 41,
      recommendedSendTime: "Morning",
      status: "pending"
    }
  });
  await prisma.campaignResponse.create({
    data: {
      targetId: target.id,
      deliveryStatus: "pending",
      openedFlag: true,
      clickedFlag: true,
      repliedFlag: true,
      inquiryFlag: true,
      purchaseFlag: false,
      responseDate: new Date("2026-05-12"),
      notes: "Seed response placeholder"
    }
  });

  const influencerCampaign = await prisma.influencerCampaign.create({
    data: {
      campaignId: campaign.id,
      influencerId: influencer.id,
      activationRole: "Demo testimonial",
      contentFormat: "Short video",
      plannedPublishDate: new Date("2026-05-14"),
      expectedReach: 12000,
      budgetAllocated: 25000,
      approvalStatus: "approved",
      trackingCode: "KP-COTTON-AKOLA-01",
      notes: "Focus on field proof and retailer follow-up."
    }
  });
  await prisma.influencerPerformance.create({
    data: {
      influencerCampaignId: influencerCampaign.id,
      actualReach: 0,
      viewsOrListens: 0,
      shares: 0,
      replies: 0,
      inquiriesGenerated: 0,
      retailerVisitsAttributed: 0,
      purchasesAttributed: 0,
      costPerInquiry: 0,
      conversionRate: 0,
      performanceNotes: "Awaiting campaign launch"
    }
  });

  await prisma.uploadRecord.createMany({
    data: [
      {
        fileName: "akola_cotton_survey_may.csv",
        purpose: "Survey CSV",
        rows: 128,
        status: "Imported",
        aiConfidence: 91,
        importedRows: 124,
        uploadedAt: new Date("2026-05-10")
      },
      {
        fileName: "maize_farmer_panel_bihar.csv",
        purpose: "Survey CSV",
        rows: 76,
        status: "Imported",
        aiConfidence: 86,
        importedRows: 73,
        uploadedAt: new Date("2026-05-09")
      },
      {
        fileName: "retailer_campaign_history_q1.csv",
        purpose: "Campaign History",
        rows: 42,
        status: "Needs Review",
        aiConfidence: 74,
        importedRows: 35,
        uploadedAt: new Date("2026-05-08")
      },
      {
        fileName: "channel_scoring_model_v0.json",
        purpose: "Model Upload",
        rows: 1,
        status: "Validated",
        aiConfidence: 93,
        importedRows: 1,
        uploadedAt: new Date("2026-05-07")
      }
    ]
  });

  await prisma.dataHealthIssue.createMany({
    data: [
      {
        category: "Missing values",
        label: "Farm size absent in recent farmer rows",
        issueCount: 14,
        severity: "medium",
        recommendedFix: "Ask field reps to capture land size during the next retailer visit.",
        status: "open"
      },
      {
        category: "Duplicate records",
        label: "Potential duplicate farmers by phone and village",
        issueCount: 5,
        severity: "low",
        recommendedFix: "Merge duplicate farmer profiles before running high-value targeting.",
        status: "open"
      },
      {
        category: "Low confidence mappings",
        label: "Ambiguous crop names from survey CSV",
        issueCount: 8,
        severity: "medium",
        recommendedFix: "Review crop aliases and add common local-language variants.",
        status: "open"
      },
      {
        category: "Validation errors",
        label: "Campaign history rows missing channel",
        issueCount: 3,
        severity: "high",
        recommendedFix: "Map blank channels to retailer, WhatsApp, SMS, voice, or field rep.",
        status: "open"
      }
    ]
  });

  console.log("Seeded Krishi Pracharak core database.");
}

main()
  .catch((error) => {
    console.error(error);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
