import type { Crop, Region } from "@prisma/client";
import { NextResponse } from "next/server";

import { buildSegments } from "@/lib/ai/segmentation";
import { prisma } from "@/lib/prisma";
import { segmentationSchema } from "@/lib/validators";

const MOCK_OBSERVATION_DATE = new Date("2026-05-21T00:00:00.000Z");

function fetchWeatherData(region: Region) {
  const state = region.state.toLowerCase();

  if (state.includes("bihar")) {
    return {
      temperatureAvg: 35,
      rainfallMm: 42,
      humidityPercent: 78,
      soilType: "Alluvial soil",
      soilPh: 6.8,
      soilMoisture: 58,
      irrigationType: "Rainfed with tube well support",
      weatherSummary: "Humid with uneven rainfall",
      riskLevel: "High"
    };
  }

  if (state.includes("maharashtra")) {
    return {
      temperatureAvg: 33,
      rainfallMm: 24,
      humidityPercent: 72,
      soilType: "Black soil",
      soilPh: 7.2,
      soilMoisture: 61,
      irrigationType: "Borewell",
      weatherSummary: "Humid pest-favorable weather",
      riskLevel: "High"
    };
  }

  if (state.includes("telangana") || state.includes("karnataka")) {
    return {
      temperatureAvg: 34,
      rainfallMm: 16,
      humidityPercent: 64,
      soilType: "Red loamy soil",
      soilPh: 7,
      soilMoisture: 47,
      irrigationType: "Mixed irrigation",
      weatherSummary: "Warm and moisture-stressed",
      riskLevel: "Medium"
    };
  }

  return {
    temperatureAvg: 31,
    rainfallMm: 20,
    humidityPercent: 68,
    soilType: "Mixed soil",
    soilPh: 7,
    soilMoisture: 52,
    irrigationType: "Mixed",
    weatherSummary: "Variable field conditions",
    riskLevel: "Medium"
  };
}

function fetchOutbreakData(region: Region, crop: Crop) {
  const state = region.state.toLowerCase();
  const cropName = crop.name.toLowerCase();

  if (state.includes("bihar") && cropName.includes("maize")) {
    return {
      outbreakType: "Nutrient issue",
      outbreakName: "Late sowing and early vigor stress",
      severity: "High",
      source: "Mock weather and field advisory signal",
      symptoms: "Uneven germination, moisture stress, and delayed early growth reported in comparable blocks.",
      recommendationWindowDays: 12
    };
  }

  if (cropName.includes("cotton")) {
    return {
      outbreakType: "Pest",
      outbreakName: "Pink bollworm pressure",
      severity: state.includes("maharashtra") ? "High" : "Medium",
      source: "Mock field scouting signal",
      symptoms: "Flowering-stage pest risk and early boll damage indicators.",
      recommendationWindowDays: 10
    };
  }

  return {
    outbreakType: "Weather risk",
    outbreakName: `${crop.name} stress watch`,
    severity: "Medium",
    source: "Mock agronomic risk model",
    symptoms: "Weather variability may affect crop-stage performance.",
    recommendationWindowDays: 14
  };
}

async function resolveSelectedRegion(regionName?: string) {
  if (!regionName) {
    return null;
  }

  const existing = await prisma.region.findFirst({ where: { state: regionName } });
  if (existing) {
    return existing;
  }

  return prisma.region.create({
    data: {
      country: "India",
      state: regionName,
      district: "",
      blockTaluk: "",
      village: ""
    }
  });
}

async function upsertMockEcosystem(region: Region) {
  const weather = fetchWeatherData(region);
  const existing = await prisma.ecosystemCondition.findFirst({
    where: {
      regionId: region.id,
      observationDate: MOCK_OBSERVATION_DATE
    }
  });

  if (existing) {
    return prisma.ecosystemCondition.update({
      where: { id: existing.id },
      data: weather
    });
  }

  return prisma.ecosystemCondition.create({
    data: {
      regionId: region.id,
      observationDate: MOCK_OBSERVATION_DATE,
      ...weather
    }
  });
}

async function upsertMockOutbreak(region: Region, crop: Crop) {
  const outbreak = fetchOutbreakData(region, crop);
  const existing = await prisma.outbreak.findFirst({
    where: {
      regionId: region.id,
      cropId: crop.id,
      outbreakName: outbreak.outbreakName,
      activeFlag: true
    }
  });

  if (existing) {
    return prisma.outbreak.update({
      where: { id: existing.id },
      data: {
        ...outbreak,
        detectedDate: MOCK_OBSERVATION_DATE,
        activeFlag: true
      }
    });
  }

  return prisma.outbreak.create({
    data: {
      regionId: region.id,
      cropId: crop.id,
      detectedDate: MOCK_OBSERVATION_DATE,
      activeFlag: true,
      ...outbreak
    }
  });
}

export async function POST(request: Request) {
  const json = await request.json();
  const parsed = segmentationSchema.safeParse(json);

  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid request." }, { status: 400 });
  }

  const product = await prisma.product.findUnique({
    where: { id: parsed.data.productId },
    include: {
      cropFits: {
        include: { crop: true },
        orderBy: { relevanceScore: "desc" }
      }
    }
  });

  if (!product) {
    return NextResponse.json({ error: "Product not found." }, { status: 404 });
  }

  const selectedRegion = await resolveSelectedRegion(parsed.data.region);
  const cropIds = product.cropFits.map((fit) => fit.cropId);
  const crops = product.cropFits.map((fit) => fit.crop);
  const regions = selectedRegion
    ? [selectedRegion]
    : await prisma.region.findMany({
        orderBy: [{ state: "asc" }, { district: "asc" }],
        take: 12
      });

  const mockRegions = regions.length ? regions.slice(0, 6) : [];
  const mockCrops = crops.length
    ? crops
    : await prisma.crop.findMany({
        orderBy: { name: "asc" },
        take: 4
      });

  await Promise.all(mockRegions.map((region) => upsertMockEcosystem(region)));
  await Promise.all(
    mockRegions.flatMap((region) =>
      mockCrops.slice(0, 3).map((crop) => upsertMockOutbreak(region, crop))
    )
  );

  const farmers = await prisma.farmer.findMany({
    where: {
      regionId: selectedRegion?.id,
      primaryCropId: cropIds.length ? { in: cropIds } : undefined
    },
    include: {
      primaryCrop: true,
      region: true,
      preferredLanguage: true,
      assets: true,
      farmingPractices: true,
      channelPreferences: true
    },
    orderBy: { createdAt: "desc" },
    take: 250
  });

  const regionIds = regions.map((region) => region.id);
  const scopedRegionWhere = regionIds.length ? { in: regionIds } : undefined;
  const [ecosystemConditions, outbreaks, campaigns] = await Promise.all([
    prisma.ecosystemCondition.findMany({
      where: { regionId: scopedRegionWhere },
      orderBy: { observationDate: "desc" },
      take: 24
    }),
    prisma.outbreak.findMany({
      where: {
        regionId: scopedRegionWhere,
        cropId: cropIds.length ? { in: cropIds } : undefined,
        activeFlag: true
      },
      orderBy: [{ detectedDate: "desc" }, { id: "desc" }],
      take: 24
    }),
    prisma.campaign.findMany({
      where: {
        productId: product.id,
        regionId: selectedRegion?.id
      },
      include: {
        targets: {
          include: { response: true }
        }
      },
      orderBy: { id: "desc" },
      take: 12
    })
  ]);

  const segments = buildSegments({
    product,
    region: selectedRegion,
    regions,
    crops,
    farmers,
    ecosystemConditions,
    outbreaks,
    campaigns,
    additionalInfo: parsed.data.additionalInfo
  });

  return NextResponse.json({ segments });
}
