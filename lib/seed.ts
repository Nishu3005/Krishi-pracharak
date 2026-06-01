import { prisma } from "@/lib/prisma";

export async function ensureSeedData() {
  const existingProducts = await prisma.product.count();
  if (existingProducts > 0) {
    return;
  }

  const [marathi, hindi] = await Promise.all([
    prisma.language.upsert({
      where: { name: "Marathi" },
      create: { name: "Marathi", scriptType: "Native script" },
      update: {}
    }),
    prisma.language.upsert({
      where: { name: "Hindi" },
      create: { name: "Hindi", scriptType: "Native script" },
      update: {}
    })
  ]);

  const [maharashtra, telangana, bihar] = await Promise.all([
    prisma.region.upsert({
      where: {
        country_state_district_blockTaluk_village: {
          country: "India",
          state: "Maharashtra",
          district: "Akola",
          blockTaluk: "",
          village: ""
        }
      },
      create: {
        country: "India",
        state: "Maharashtra",
        district: "Akola",
        blockTaluk: "",
        village: "",
        agroClimaticZone: "Central Plateau"
      },
      update: {}
    }),
    prisma.region.upsert({
      where: {
        country_state_district_blockTaluk_village: {
          country: "India",
          state: "Telangana",
          district: "Warangal",
          blockTaluk: "",
          village: ""
        }
      },
      create: {
        country: "India",
        state: "Telangana",
        district: "Warangal",
        blockTaluk: "",
        village: "",
        agroClimaticZone: "Semi-arid tropics"
      },
      update: {}
    }),
    prisma.region.upsert({
      where: {
        country_state_district_blockTaluk_village: {
          country: "India",
          state: "Bihar",
          district: "Begusarai",
          blockTaluk: "",
          village: ""
        }
      },
      create: {
        country: "India",
        state: "Bihar",
        district: "Begusarai",
        blockTaluk: "",
        village: "",
        agroClimaticZone: "Middle Gangetic Plains"
      },
      update: {}
    })
  ]);

  const [cotton, maize] = await Promise.all([
    prisma.crop.upsert({
      where: { name: "Cotton" },
      create: {
        name: "Cotton",
        category: "Cash crop",
        season: "Kharif",
        averageDurationDays: 165,
        typicalGrowthStages: "Sowing, vegetative, flowering, boll formation, harvest"
      },
      update: {}
    }),
    prisma.crop.upsert({
      where: { name: "Maize" },
      create: {
        name: "Maize",
        category: "Cereal",
        season: "Kharif",
        averageDurationDays: 110,
        typicalGrowthStages: "Sowing, vegetative, tasseling, grain filling, harvest"
      },
      update: {}
    })
  ]);

  const [cropShield, rootRise] = await Promise.all([
    prisma.product.create({
      data: {
        name: "CropShield Pro",
        category: "Insecticide",
        productType: "Chemical",
        sustainableFlag: false,
        organicFlag: false,
        pricePerUnit: 850,
        unitType: "litre",
        activeIngredient: "Lambda-cyhalothrin",
        targetPestType: "Insect",
        cropStageRelevance: "Vegetative to flowering",
        positioning: "High-efficacy pest control with low spray complexity",
        status: "active"
      }
    }),
    prisma.product.create({
      data: {
        name: "RootRise Max",
        category: "Seed",
        productType: "Hybrid seed",
        sustainableFlag: true,
        organicFlag: false,
        pricePerUnit: 1350,
        unitType: "packet",
        activeIngredient: "Hybrid maize genetics",
        targetPestType: "Stress tolerance",
        cropStageRelevance: "Sowing",
        positioning: "Higher vigor for erratic rainfall conditions",
        status: "active"
      }
    })
  ]);

  await Promise.all([
    prisma.productCropFit.create({
      data: {
        productId: cropShield.id,
        cropId: cotton.id,
        outbreakType: "Pest",
        outbreakName: "Pink bollworm",
        recommendedStage: "Flowering",
        relevanceScore: 92,
        approvedFlag: true
      }
    }),
    prisma.productCropFit.create({
      data: {
        productId: rootRise.id,
        cropId: maize.id,
        outbreakType: "Nutrient issue",
        outbreakName: "Early vigor stress",
        recommendedStage: "Sowing",
        relevanceScore: 88,
        approvedFlag: true
      }
    })
  ]);

  const [ramesh, suresh, anita] = await Promise.all([
    prisma.farmer.create({
      data: {
        name: "Ramesh Patil",
        regionId: maharashtra.id,
        primaryCropId: cotton.id,
        landSizeAcres: 6,
        annualIncomeBand: "Medium",
        literacyLevel: "Moderate",
        smartphoneUser: true,
        featurePhoneUser: false,
        preferredLanguageId: marathi.id,
        ageBand: "31-45",
        farmerSegment: "Progressive smallholder",
        trustChannel: "WhatsApp"
      }
    }),
    prisma.farmer.create({
      data: {
        name: "Suresh Rao",
        regionId: telangana.id,
        primaryCropId: cotton.id,
        landSizeAcres: 4,
        annualIncomeBand: "High",
        literacyLevel: "Moderate",
        smartphoneUser: true,
        featurePhoneUser: true,
        preferredLanguageId: hindi.id,
        ageBand: "46-60",
        farmerSegment: "Risk-aware adopter",
        trustChannel: "Retailer"
      }
    }),
    prisma.farmer.create({
      data: {
        name: "Anita Devi",
        regionId: bihar.id,
        primaryCropId: maize.id,
        landSizeAcres: 3,
        annualIncomeBand: "Low",
        literacyLevel: "Low",
        smartphoneUser: false,
        featurePhoneUser: true,
        preferredLanguageId: hindi.id,
        ageBand: "31-45",
        farmerSegment: "Price-sensitive smallholder",
        trustChannel: "Voice call"
      }
    })
  ]);

  await Promise.all([
    prisma.channelPreference.create({
      data: {
        farmerId: ramesh.id,
        whatsappOptIn: true,
        smsOptIn: true,
        voiceCallOptIn: false,
        retailerInfluenceScore: 62,
        fieldRepInfluenceScore: 70,
        preferredContactTime: "Morning",
        engagementScore: 78
      }
    }),
    prisma.channelPreference.create({
      data: {
        farmerId: suresh.id,
        whatsappOptIn: false,
        smsOptIn: true,
        voiceCallOptIn: true,
        retailerInfluenceScore: 86,
        fieldRepInfluenceScore: 72,
        preferredContactTime: "Evening",
        engagementScore: 64
      }
    }),
    prisma.channelPreference.create({
      data: {
        farmerId: anita.id,
        whatsappOptIn: false,
        smsOptIn: true,
        voiceCallOptIn: true,
        retailerInfluenceScore: 58,
        fieldRepInfluenceScore: 61,
        preferredContactTime: "Afternoon",
        engagementScore: 45
      }
    })
  ]);

  await Promise.all([
    prisma.ecosystemCondition.create({
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
    }),
    prisma.outbreak.create({
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
    })
  ]);

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

  await Promise.all([
    prisma.campaignMessage.create({
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
    }),
    prisma.campaignTarget.create({
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
    }),
    prisma.influencerCampaign.create({
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
    })
  ]);
}
