import { CampaignBuilder } from "@/components/campaign/campaign-builder";
import { PageHeader } from "@/components/layout/page-header";
import { getCampaignBuilderData } from "@/lib/data";

export const dynamic = "force-dynamic";

export default async function CreateCampaignPage() {
  const { products, influencers } = await getCampaignBuilderData();

  return (
    <div>
      <PageHeader
        eyebrow="Stage 2"
        title="Create Campaign"
        description="Select campaign inputs, create farmer persona segments, then generate channel-ready content and strategy responses from the right pane."
        badge="Campaign module"
      />
      <CampaignBuilder products={products} influencers={influencers} />
    </div>
  );
}
