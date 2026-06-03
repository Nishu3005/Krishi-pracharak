"use client";

import { useEffect, useMemo, useState } from "react";
import { Bot, Download, MessageSquareText, PlayCircle, Send, Sparkles } from "lucide-react";

import type { GeneratedCampaign, Segment } from "@/lib/types";
import { CHANNELS, REGIONS } from "@/lib/constants";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

type GenerationResponse = {
  generated: GeneratedCampaign;
  savedCampaignId: number;
};

export type CampaignProductOption = {
  id: number;
  name: string;
  category: string;
  positioning: string | null;
};

export type CampaignInfluencerOption = {
  id: number;
  name: string;
  channel: string;
};

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

type SegmentRequest = {
  productId: string;
  region: string;
  channel: string;
  influencerId: string;
  additionalInfo: string;
};

type SegmentResponse = {
  provider: string;
  model: string;
  overallStrategy: string;
  dataGaps: string[];
  assumptions: string[];
  segments: Segment[];
};

const generatedTabs = [
  { key: "whatsapp", label: "WhatsApp" },
  { key: "sms", label: "SMS" },
  { key: "voiceScript", label: "Voice Script" },
  { key: "videoScript", label: "Video Script" },
  { key: "imagePrompt", label: "Image Prompt" },
  { key: "influencerScript", label: "Influencer Script" },
  { key: "fieldRepScript", label: "Field Rep Script" },
  { key: "retailerScript", label: "Retailer Script" }
] as const;

type GeneratedContentTab = (typeof generatedTabs)[number]["key"];

function contentTabForChannel(channelValue: string): GeneratedContentTab | null {
  if (channelValue === "WhatsApp") return "whatsapp";
  if (channelValue === "SMS") return "sms";
  if (channelValue === "Voice") return "voiceScript";
  if (channelValue === "Video") return "videoScript";
  if (channelValue === "Image") return "imagePrompt";
  return null;
}

const suggestedQuestions = [
  "Why was this segment selected?",
  "Which channel is best for this segment?",
  "What worked in previous campaigns?",
  "Which influencer is best for this region?",
  "What is the expected inquiry rate?",
  "What are the risks in this campaign?",
  "How is the priority score calculated?"
];

const agentTrace = [
  "Data Retrieval Agent fetched database and dynamic data",
  "Segment Agent created farmer personas",
  "Prompt Agent created channel-specific prompts",
  "Orchestrator Agent delegated generation",
  "Content Agent generated outputs",
  "Safety Agent checked compliance"
];

function scoreClass(score: number) {
  if (score >= 80) return "bg-primary text-primary-foreground";
  if (score >= 65) return "bg-secondary text-secondary-foreground";
  return "bg-muted text-foreground";
}

function compactScoreLabel(label: string, score: number) {
  return `${label} ${score}`;
}

function complianceClass(status: GeneratedCampaign["compliance"]["status"]) {
  if (status === "Passed") return "bg-emerald-100 text-emerald-900";
  if (status === "Warning") return "bg-amber-100 text-amber-950";
  return "bg-red-100 text-red-900";
}

export function CampaignBuilder({
  products,
  influencers
}: {
  products: CampaignProductOption[];
  influencers: CampaignInfluencerOption[];
}) {
  const [productId, setProductId] = useState(products[0]?.id ? String(products[0].id) : "");
  const [channel, setChannel] = useState("");
  const [additionalInfo, setAdditionalInfo] = useState("");
  const [influencerId, setInfluencerId] = useState("");
  const [region, setRegion] = useState("");
  const [segments, setSegments] = useState<Segment[]>([]);
  const [segmentMetadata, setSegmentMetadata] = useState<Omit<SegmentResponse, "segments"> | null>(null);
  const [selectedSegment, setSelectedSegment] = useState<string>("");
  const [generated, setGenerated] = useState<GeneratedCampaign | null>(null);
  const [generatedChannel, setGeneratedChannel] = useState("");
  const [activePane, setActivePane] = useState<"chat" | "content">("chat");
  const [activeContentTab, setActiveContentTab] = useState<GeneratedContentTab>("whatsapp");
  const [chatQuestion, setChatQuestion] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: "Ask about the selected product, previous campaigns, retailers, farmers, influencers, or campaign strategy."
    }
  ]);
  const [loading, setLoading] = useState<"segments" | "generate" | "chat" | null>(null);
  const [error, setError] = useState("");

  const activeProduct = useMemo(
    () => products.find((product) => String(product.id) === productId),
    [productId, products]
  );

  const activeInfluencer = useMemo(
    () => influencers.find((influencer) => String(influencer.id) === influencerId),
    [influencerId, influencers]
  );

  const activeSegment = useMemo(
    () => segments.find((segment) => segment.name === selectedSegment) ?? segments[0],
    [segments, selectedSegment]
  );

  const genericConversion = generated
    ? Math.max(1, generated.expectedPerformance.expectedConversion - generated.expectedPerformance.expectedUpliftOverGeneric)
    : null;

  const effectiveGeneratedChannel = generatedChannel || channel;

  const visibleGeneratedTabs = useMemo(() => {
    const selectedContentTab = contentTabForChannel(effectiveGeneratedChannel);
    return selectedContentTab ? generatedTabs.filter((tab) => tab.key === selectedContentTab) : generatedTabs;
  }, [effectiveGeneratedChannel]);

  useEffect(() => {
    if (!generated || visibleGeneratedTabs.some((tab) => tab.key === activeContentTab)) {
      return;
    }

    setActiveContentTab(visibleGeneratedTabs[0]?.key ?? "whatsapp");
  }, [activeContentTab, generated, visibleGeneratedTabs]);

  async function requestSegments(request: SegmentRequest, limit?: number) {
    const response = await fetch("/api/campaigns/segments", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(request)
    });

    if (!response.ok) {
      const payload = (await response.json().catch(() => null)) as { error?: string } | null;
      throw new Error(payload?.error || "Unable to create segments.");
    }

    const payload = (await response.json()) as SegmentResponse;
    return {
      ...payload,
      segments: limit ? payload.segments.slice(0, limit) : payload.segments
    };
  }

  async function createSegments() {
    setLoading("segments");
    setError("");
    setGenerated(null);
    setGeneratedChannel("");
    setSegmentMetadata(null);
    try {
      const payload = await requestSegments({
        productId,
        region,
        channel,
        influencerId,
        additionalInfo
      });
      const nextSegments = payload.segments;
      setSegmentMetadata({
        provider: payload.provider,
        model: payload.model,
        overallStrategy: payload.overallStrategy,
        dataGaps: payload.dataGaps,
        assumptions: payload.assumptions
      });
      setSegments(nextSegments);
      setSelectedSegment(nextSegments[0]?.name ?? "");
      setActivePane("chat");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create segments.");
    } finally {
      setLoading(null);
    }
  }

  async function runDemoScenario() {
    const seedProduct = products.find((product) => product.category.toLowerCase().includes("seed")) ?? products[0];
    if (!seedProduct) {
      setError("Add a seed product before running the Bihar demo.");
      return;
    }

    const demoRequest = {
      productId: String(seedProduct.id),
      region: "Bihar",
      channel: "WhatsApp",
      influencerId: "",
      additionalInfo: "target smallholder farmers before sowing season"
    };

    setLoading("segments");
    setError("");
    setGenerated(null);
    setGeneratedChannel("");
    setSegmentMetadata(null);
    setProductId(demoRequest.productId);
    setRegion(demoRequest.region);
    setChannel(demoRequest.channel);
    setInfluencerId(demoRequest.influencerId);
    setAdditionalInfo(demoRequest.additionalInfo);

    try {
      const payload = await requestSegments(demoRequest, 3);
      const nextSegments = payload.segments;
      setSegmentMetadata({
        provider: payload.provider,
        model: payload.model,
        overallStrategy: payload.overallStrategy,
        dataGaps: payload.dataGaps,
        assumptions: payload.assumptions
      });
      setSegments(nextSegments);
      setSelectedSegment(nextSegments[0]?.name ?? "");
      setActivePane("chat");
      setChatMessages((messages) => [
        ...messages,
        {
          role: "assistant",
          content: "Bihar Seed Campaign Demo loaded with RootRise-style seed product context, Bihar region, and three high-priority farmer personas."
        }
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to run demo scenario.");
    } finally {
      setLoading(null);
    }
  }

  async function generateForSegment(segment: Segment) {
    setLoading("generate");
    setError("");
    setSelectedSegment(segment.name);
    try {
      const response = await fetch("/api/campaigns/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          productId,
          region,
          channel,
          influencerId,
          additionalInfo,
          segment
        })
      });

      if (!response.ok) {
        throw new Error("Unable to generate campaign content.");
      }

      const payload = (await response.json()) as GenerationResponse;
      const selectedContentTab = contentTabForChannel(channel);
      setGenerated(payload.generated);
      setGeneratedChannel(channel);
      setActivePane("content");
      setActiveContentTab(selectedContentTab ?? "whatsapp");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to generate campaign content.");
    } finally {
      setLoading(null);
    }
  }

  async function askChat() {
    const question = chatQuestion.trim();
    if (!question) {
      return;
    }

    setLoading("chat");
    setError("");
    setChatQuestion("");
    setChatMessages((messages) => [...messages, { role: "user", content: question }]);

    try {
      const response = await fetch("/api/campaigns/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          productId,
          region,
          channel,
          influencerId,
          additionalInfo,
          segment: activeSegment,
          expectedPerformance: generated?.expectedPerformance,
          compliance: generated?.compliance,
          question
        })
      });

      if (!response.ok) {
        throw new Error("Unable to answer from campaign data.");
      }

      const payload = (await response.json()) as { answer: string };
      setChatMessages((messages) => [...messages, { role: "assistant", content: payload.answer }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to answer from campaign data.");
    } finally {
      setLoading(null);
    }
  }

  async function askSuggestedQuestion(question: string) {
    setChatQuestion(question);
    setLoading("chat");
    setError("");
    setChatMessages((messages) => [...messages, { role: "user", content: question }]);

    try {
      const response = await fetch("/api/campaigns/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          productId,
          region,
          channel,
          influencerId,
          additionalInfo,
          segment: activeSegment,
          expectedPerformance: generated?.expectedPerformance,
          compliance: generated?.compliance,
          question
        })
      });

      if (!response.ok) {
        throw new Error("Unable to answer from campaign data.");
      }

      const payload = (await response.json()) as { answer: string };
      setChatMessages((messages) => [...messages, { role: "assistant", content: payload.answer }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to answer from campaign data.");
    } finally {
      setChatQuestion("");
      setLoading(null);
    }
  }

  function exportCampaignPack() {
    if (!generated || !activeProduct || !activeSegment) {
      setError("Generate content for a segment before exporting a campaign pack.");
      return;
    }

    const selectedGeneratedContentTab = contentTabForChannel(effectiveGeneratedChannel);
    const generatedContent = selectedGeneratedContentTab
      ? { [selectedGeneratedContentTab]: generated.content[selectedGeneratedContentTab] }
      : generated.content;

    const pack = {
      campaignBrief: generated.campaignBrief,
      selectedProduct: activeProduct,
      selectedRegion: region || activeSegment.region,
      selectedSegment: activeSegment,
      selectedInfluencer: activeInfluencer ?? null,
      channel: effectiveGeneratedChannel || "All",
      generatedContent,
      compliance: generated.compliance,
      predictedMetrics: generated.expectedPerformance,
      genericVsAiComparison: {
        genericCampaignConversion: genericConversion,
        krishiPulseAiPredictedConversion: generated.expectedPerformance.expectedConversion,
        expectedUplift: generated.expectedPerformance.expectedUpliftOverGeneric
      },
      agentTrace
    };
    const blob = new Blob([JSON.stringify(pack, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${activeProduct.name}-${activeSegment.name}`.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") + "-campaign-pack.json";
    link.click();
    URL.revokeObjectURL(url);
  }

  function updateGeneratedContent(value: string) {
    setGenerated((current) => {
      if (!current) {
        return current;
      }

      return {
        ...current,
        content: {
          ...current.content,
          [activeContentTab]: value
        }
      };
    });
  }

  const activeContent = generated?.content[activeContentTab] ?? "";

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-primary">Hackathon demo mode</p>
          <p className="text-sm text-foreground/60">Load a polished Bihar seed campaign scenario with one click.</p>
        </div>
        <Button onClick={runDemoScenario} disabled={loading !== null || !products.length} className="shrink-0">
          <PlayCircle className="mr-2 h-4 w-4" />
          Run Bihar Seed Campaign Demo
        </Button>
      </div>

      <Card className="bg-white/88">
        <div className="grid gap-4 xl:grid-cols-[0.82fr_1.25fr_1fr_1fr_1fr]">
          <div>
            <Label htmlFor="campaign-channel">Channel</Label>
            <Select id="campaign-channel" value={channel} onChange={(event) => setChannel(event.target.value)}>
              <option value="">Optional</option>
              {CHANNELS.map((entry) => (
                <option key={entry} value={entry}>
                  {entry}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label htmlFor="campaign-info">Additional Info</Label>
            <Textarea
              id="campaign-info"
              value={additionalInfo}
              onChange={(event) => setAdditionalInfo(event.target.value)}
              placeholder="Market context, disease pressure, competitor notes"
              className="min-h-[44px]"
            />
          </div>
          <div>
            <Label htmlFor="campaign-influencer">Influencer</Label>
            <Select
              id="campaign-influencer"
              value={influencerId}
              onChange={(event) => setInfluencerId(event.target.value)}
            >
              <option value="">Optional</option>
              {influencers.map((influencer) => (
                <option key={influencer.id} value={influencer.id}>
                  {influencer.name}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label htmlFor="campaign-product">Product</Label>
            <Select id="campaign-product" value={productId} onChange={(event) => setProductId(event.target.value)} required>
              {products.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.name}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label htmlFor="campaign-region">Region</Label>
            <Select id="campaign-region" value={region} onChange={(event) => setRegion(event.target.value)}>
              <option value="">Optional</option>
              {REGIONS.map((entry) => (
                <option key={entry} value={entry}>
                  {entry}
                </option>
              ))}
            </Select>
          </div>
        </div>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="bg-white/84">
          <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div>
              <CardTitle>Farmer Persona Segments</CardTitle>
              <CardDescription className="mt-1">
                Create segments from product, region, farmer data, and planner notes. Channel and influencer are applied during generation.
              </CardDescription>
            </div>
            <Button onClick={createSegments} disabled={!productId || loading !== null} className="shrink-0">
              <Sparkles className="mr-2 h-4 w-4" />
              {loading === "segments" ? "Creating..." : "Create Segments"}
            </Button>
          </div>

          {error ? <p className="mt-4 text-sm font-medium text-red-700">{error}</p> : null}

          {segmentMetadata ? (
            <div className="mt-5 grid gap-3 rounded-2xl border border-primary/15 bg-primary/5 p-4 text-sm md:grid-cols-2">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary/70">AI Provider</p>
                <p className="mt-1 font-semibold">{segmentMetadata.provider}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary/70">Model Used</p>
                <p className="mt-1 font-semibold">{segmentMetadata.model}</p>
              </div>
              <div className="md:col-span-2">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary/70">Overall Strategy</p>
                <p className="mt-1 leading-6 text-foreground/72">{segmentMetadata.overallStrategy}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary/70">Data Gaps</p>
                <ul className="mt-1 space-y-1 text-foreground/68">
                  {(segmentMetadata.dataGaps.length ? segmentMetadata.dataGaps : ["No major data gaps returned."]).map((entry) => (
                    <li key={entry}>{entry}</li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary/70">Assumptions</p>
                <ul className="mt-1 space-y-1 text-foreground/68">
                  {(segmentMetadata.assumptions.length ? segmentMetadata.assumptions : ["No assumptions returned."]).map((entry) => (
                    <li key={entry}>{entry}</li>
                  ))}
                </ul>
              </div>
            </div>
          ) : null}

          <div className="mt-6 grid gap-4">
            {segments.length === 0 ? (
              [0, 1, 2].map((index) => (
                <div key={index} className="rounded-2xl border border-dashed border-border bg-muted/30 p-5">
                  <div className="h-4 w-44 rounded-full bg-border/70" />
                  <div className="mt-4 h-3 w-full max-w-xl rounded-full bg-border/50" />
                  <div className="mt-2 h-3 w-3/4 rounded-full bg-border/40" />
                  <div className="mt-5 grid gap-3 md:grid-cols-2">
                    <div className="h-20 rounded-xl bg-white/70" />
                    <div className="h-20 rounded-xl bg-white/70" />
                  </div>
                </div>
              ))
            ) : (
              segments.map((segment) => (
                <div key={segment.name} className="rounded-2xl border border-border bg-white/80 p-5">
                  <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                    <div className="space-y-2">
                      <p className="font-semibold text-foreground">{segment.name}</p>
                      <p className="text-sm leading-6 text-foreground/68">{segment.farmerPersona}</p>
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary/70">{segment.recommendedTone}</p>
                    </div>
                    <Button
                      variant={selectedSegment === segment.name ? "default" : "outline"}
                      onClick={() => generateForSegment(segment)}
                      disabled={loading !== null}
                      className="shrink-0"
                    >
                      {loading === "generate" && selectedSegment === segment.name ? "Generating..." : "Generate"}
                    </Button>
                  </div>

                  <div className="mt-4 grid gap-3 md:grid-cols-4">
                    <div className="rounded-xl border border-border bg-muted/25 p-3">
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-foreground/45">Region</p>
                      <p className="mt-2 text-sm font-semibold">{segment.region}</p>
                    </div>
                    <div className="rounded-xl border border-border bg-muted/25 p-3">
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-foreground/45">Main Crop</p>
                      <p className="mt-2 text-sm font-semibold">{segment.mainCrop}</p>
                    </div>
                    <div className="rounded-xl border border-border bg-muted/25 p-3">
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-foreground/45">Estimated Farmers</p>
                      <p className="mt-2 text-sm font-semibold">{segment.estimatedFarmers.toLocaleString("en-IN")}</p>
                    </div>
                    <div className="rounded-xl border border-border bg-muted/25 p-3">
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-foreground/45">Scores</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${scoreClass(segment.priorityScore)}`}>
                          Priority {segment.priorityScore}
                        </span>
                        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${scoreClass(segment.dataConfidenceScore)}`}>
                          Confidence {segment.dataConfidenceScore}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    <div className="rounded-xl border border-border bg-muted/25 p-3">
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-foreground/45">Farmer Need</p>
                      <p className="mt-2 text-sm leading-6 text-foreground/68">{segment.farmerNeed}</p>
                    </div>
                    <div className="rounded-xl border border-border bg-muted/25 p-3">
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-foreground/45">Product Relevance</p>
                      <p className="mt-2 text-sm leading-6 text-foreground/68">{segment.productRelevance}</p>
                    </div>
                    <div className="rounded-xl border border-border bg-muted/25 p-3">
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-foreground/45">Ecosystem Context</p>
                      <p className="mt-2 text-sm leading-6 text-foreground/68">{segment.ecosystemContext}</p>
                    </div>
                    <div className="rounded-xl border border-border bg-muted/25 p-3">
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-foreground/45">Outbreak / Weather Trigger</p>
                      <p className="mt-2 text-sm leading-6 text-foreground/68">{segment.outbreakWeatherTrigger}</p>
                    </div>
                  </div>

                  <div className="mt-4 rounded-xl border border-primary/20 bg-primary/5 p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary/70">Why this segment?</p>
                    {segment.whyThisSegment?.length ? (
                      <ul className="mt-2 space-y-1 text-sm leading-6 text-foreground/72">
                        {segment.whyThisSegment.map((reason) => (
                          <li key={reason}>{reason}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="mt-2 text-sm leading-6 text-foreground/72">{segment.whyCreated}</p>
                    )}
                  </div>

                  {segment.recommendedNextAction ? (
                    <div className="mt-4 rounded-xl border border-border bg-muted/25 p-4">
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-foreground/45">Recommended Next Action</p>
                      <p className="mt-2 text-sm leading-6 text-foreground/72">{segment.recommendedNextAction}</p>
                    </div>
                  ) : null}

                  {segment.scoreBreakdown || segment.dataConfidenceBreakdown ? (
                    <div className="mt-4 grid gap-3 md:grid-cols-2">
                      {segment.scoreBreakdown ? (
                        <div className="rounded-xl border border-border bg-muted/25 p-3">
                          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-foreground/45">Priority Inputs</p>
                          <div className="mt-2 flex flex-wrap gap-2 text-xs text-foreground/68">
                            {[
                              compactScoreLabel("Product fit", segment.scoreBreakdown.productFit),
                              compactScoreLabel("Region", segment.scoreBreakdown.regionalRelevance),
                              compactScoreLabel("Crop stage", segment.scoreBreakdown.cropStageRelevance),
                              compactScoreLabel("Urgency", segment.scoreBreakdown.weatherOutbreakUrgency),
                              compactScoreLabel("Need", segment.scoreBreakdown.farmerNeed),
                              compactScoreLabel("Past response", segment.scoreBreakdown.pastCampaignResponse)
                            ].map((entry) => (
                              <span key={entry} className="rounded-full bg-white px-2.5 py-1">
                                {entry}
                              </span>
                            ))}
                          </div>
                        </div>
                      ) : null}
                      {segment.dataConfidenceBreakdown ? (
                        <div className="rounded-xl border border-border bg-muted/25 p-3">
                          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-foreground/45">Confidence Inputs</p>
                          <div className="mt-2 flex flex-wrap gap-2 text-xs text-foreground/68">
                            {[
                              compactScoreLabel("Survey", segment.dataConfidenceBreakdown.surveyDataAvailability),
                              compactScoreLabel("Region", segment.dataConfidenceBreakdown.regionDataAvailability),
                              compactScoreLabel("Weather", segment.dataConfidenceBreakdown.weatherDataFreshness),
                              compactScoreLabel("Outbreak", segment.dataConfidenceBreakdown.outbreakDataConfidence),
                              compactScoreLabel("History", segment.dataConfidenceBreakdown.campaignHistoryAvailability)
                            ].map((entry) => (
                              <span key={entry} className="rounded-full bg-white px-2.5 py-1">
                                {entry}
                              </span>
                            ))}
                          </div>
                        </div>
                      ) : null}
                    </div>
                  ) : null}

                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    <div className="rounded-xl border border-border bg-muted/25 p-3">
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-foreground/45">Traits</p>
                      <ul className="mt-2 space-y-1 text-sm text-foreground/68">
                        {segment.traits.map((trait) => (
                          <li key={trait}>{trait}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="rounded-xl border border-border bg-muted/25 p-3">
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-foreground/45">Triggers</p>
                      <ul className="mt-2 space-y-1 text-sm text-foreground/68">
                        {segment.triggers.map((trigger) => (
                          <li key={trigger}>{trigger}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>

        <Card className="bg-primary text-primary-foreground">
          <div className="flex items-center gap-2">
            <Bot className="h-5 w-5" />
            <CardTitle className="text-primary-foreground">Campaign Assistant</CardTitle>
          </div>
          <CardDescription className="mt-1 text-primary-foreground/78">
            Database-backed responses and generated campaign outputs.
          </CardDescription>

          <div className="mt-5 grid grid-cols-2 gap-2 rounded-2xl bg-white/10 p-1">
            <button
              type="button"
              onClick={() => setActivePane("chat")}
              className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${activePane === "chat" ? "bg-white text-primary" : "text-primary-foreground/78 hover:bg-white/10"}`}
            >
              Chat
            </button>
            <button
              type="button"
              onClick={() => setActivePane("content")}
              className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${activePane === "content" ? "bg-white text-primary" : "text-primary-foreground/78 hover:bg-white/10"}`}
            >
              Generated Content
            </button>
          </div>

          <div className="mt-5 rounded-3xl bg-white/10 p-5">
            <p className="text-xs uppercase tracking-[0.18em] text-primary-foreground/70">Selected Product</p>
            <p className="mt-2 font-serif text-3xl">{activeProduct?.name ?? "Choose a product"}</p>
            <p className="mt-3 text-sm leading-6 text-primary-foreground/82">
              {activeProduct?.positioning || "Add positioning details on the product screen to enrich future copy."}
            </p>
          </div>

          {activePane === "chat" ? (
            <div className="mt-5">
              <div className="mb-4 flex flex-wrap gap-2">
                {suggestedQuestions.map((question) => (
                  <button
                    key={question}
                    type="button"
                    onClick={() => askSuggestedQuestion(question)}
                    disabled={loading !== null}
                    className="rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-xs font-semibold text-primary-foreground/86 transition hover:bg-white/18 disabled:opacity-50"
                  >
                    {question}
                  </button>
                ))}
              </div>
              <div className="max-h-[440px] space-y-3 overflow-y-auto pr-1">
                {chatMessages.map((message, index) => (
                  <div
                    key={`${message.role}-${index}`}
                    className={`rounded-2xl px-4 py-3 text-sm leading-6 ${
                      message.role === "user"
                        ? "ml-8 bg-white text-primary"
                        : "mr-8 bg-black/10 text-primary-foreground/90"
                    }`}
                  >
                    {message.content}
                  </div>
                ))}
              </div>
              <div className="mt-4 flex gap-2">
                <input
                  value={chatQuestion}
                  onChange={(event) => setChatQuestion(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      askChat();
                    }
                  }}
                  placeholder="Ask about farmers, retailers, product fit, or strategy"
                  className="h-11 min-w-0 flex-1 rounded-xl border border-white/20 bg-white px-3 text-sm text-foreground outline-none"
                />
                <Button onClick={askChat} disabled={loading !== null || !chatQuestion.trim()} className="bg-white text-primary hover:bg-white/95">
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ) : generated ? (
            <div className="mt-5 space-y-5">
              <div className="flex justify-end">
                <Button onClick={exportCampaignPack} className="bg-white text-primary hover:bg-white/95">
                  <Download className="mr-2 h-4 w-4" />
                  Export Campaign Pack
                </Button>
              </div>
              <div className="rounded-3xl bg-white/12 p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-xs uppercase tracking-[0.18em] text-primary-foreground/70">Campaign Brief</p>
                  <span className={`rounded-full px-3 py-1 text-xs font-semibold ${complianceClass(generated.compliance.status)}`}>
                    Compliance {generated.compliance.status}
                  </span>
                </div>
                <p className="mt-3 text-sm leading-7 text-primary-foreground/88">{generated.campaignBrief}</p>
              </div>
              <div className="rounded-3xl bg-white/12 p-5">
                <p className="text-xs uppercase tracking-[0.18em] text-primary-foreground/70">Campaign Hook</p>
                <p className="mt-2 text-lg font-semibold">{generated.hook}</p>
              </div>
              <div className="flex gap-2 overflow-x-auto rounded-2xl bg-white/10 p-1">
                {visibleGeneratedTabs.map((tab) => (
                  <button
                    key={tab.key}
                    type="button"
                    onClick={() => setActiveContentTab(tab.key)}
                    className={`shrink-0 rounded-xl px-3 py-2 text-xs font-semibold transition ${activeContentTab === tab.key ? "bg-white text-primary" : "text-primary-foreground/78 hover:bg-white/10"}`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
              <div className="rounded-3xl bg-white/12 p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <MessageSquareText className="h-5 w-5 text-primary-foreground/75" />
                    <p className="text-xs uppercase tracking-[0.18em] text-primary-foreground/70">
                      {generatedTabs.find((tab) => tab.key === activeContentTab)?.label}
                    </p>
                  </div>
                  <span className="rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-semibold text-primary-foreground/76">
                    Editable
                  </span>
                </div>
                <h3 className="mt-3 font-serif text-3xl">{generated.headline}</h3>
                <Textarea
                  value={activeContent}
                  onChange={(event) => updateGeneratedContent(event.target.value)}
                  className="mt-4 min-h-[260px] resize-y border-white/15 bg-white/10 text-primary-foreground placeholder:text-primary-foreground/45 focus-visible:ring-white/50"
                  aria-label={`Edit ${generatedTabs.find((tab) => tab.key === activeContentTab)?.label ?? "generated content"}`}
                />
                <div className="mt-5 rounded-2xl border border-white/15 bg-white/8 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-primary-foreground/70">Call to Action</p>
                  <p className="mt-2 text-sm text-primary-foreground">{generated.callToAction}</p>
                </div>
              </div>
              <div className="rounded-3xl bg-white/12 p-5">
                <p className="text-xs uppercase tracking-[0.18em] text-primary-foreground/70">Compliance Notes</p>
                <ul className="mt-3 space-y-2 text-sm leading-6 text-primary-foreground/88">
                  {generated.compliance.notes.map((note) => (
                    <li key={note}>{note}</li>
                  ))}
                </ul>
              </div>
              <div className="rounded-3xl bg-white/12 p-5">
                <p className="text-xs uppercase tracking-[0.18em] text-primary-foreground/70">Expected Performance</p>
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  {[
                    ["Predicted reach", generated.expectedPerformance.predictedReach.toLocaleString("en-IN")],
                    ["Expected engagement", `${generated.expectedPerformance.expectedEngagement}%`],
                    ["Expected inquiry rate", `${generated.expectedPerformance.expectedInquiryRate}%`],
                    ["Expected conversion", `${generated.expectedPerformance.expectedConversion}%`],
                    ["Uplift over generic", `${generated.expectedPerformance.expectedUpliftOverGeneric}%`]
                  ].map(([label, value]) => (
                    <div key={label} className="rounded-2xl border border-white/15 bg-white/8 p-3">
                      <p className="text-xs uppercase tracking-[0.14em] text-primary-foreground/62">{label}</p>
                      <p className="mt-2 text-lg font-semibold text-primary-foreground">{value}</p>
                    </div>
                  ))}
                </div>
              </div>
              {genericConversion !== null ? (
                <div className="rounded-3xl bg-white/12 p-5">
                  <p className="text-xs uppercase tracking-[0.18em] text-primary-foreground/70">Generic vs AI Campaign</p>
                  <div className="mt-3 grid gap-3 sm:grid-cols-3">
                    {[
                      ["Generic conversion", `${genericConversion}%`],
                      ["Krishi Pracharak predicted", `${generated.expectedPerformance.expectedConversion}%`],
                      ["Expected uplift", `${generated.expectedPerformance.expectedUpliftOverGeneric}%`]
                    ].map(([label, value]) => (
                      <div key={label} className="rounded-2xl border border-white/15 bg-white/8 p-3">
                        <p className="text-xs uppercase tracking-[0.14em] text-primary-foreground/62">{label}</p>
                        <p className="mt-2 text-lg font-semibold text-primary-foreground">{value}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
              <div className="rounded-3xl bg-white/12 p-5">
                <p className="text-xs uppercase tracking-[0.18em] text-primary-foreground/70">Agent Trace</p>
                <div className="mt-3 space-y-2">
                  {agentTrace.map((step, index) => (
                    <div key={step} className="flex gap-3 rounded-2xl border border-white/15 bg-white/8 p-3 text-sm text-primary-foreground/88">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white text-xs font-bold text-primary">
                        {index + 1}
                      </span>
                      <span>{step}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="mt-5 rounded-3xl border border-dashed border-white/25 bg-white/10 p-8 text-sm leading-6 text-primary-foreground/80">
              Create segments, choose Generate on a segment card, and the channel-specific content tabs will appear here.
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
