import type { Influencer, Language, Region } from "@prisma/client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

type InfluencerWithContext = Influencer & {
  region?: Region | null;
  language?: Language | null;
};

export function InfluencerForm({
  redirectTo,
  influencer,
  compact = false
}: {
  redirectTo: string;
  influencer?: InfluencerWithContext;
  compact?: boolean;
}) {
  const key = influencer ? `influencer-${influencer.id}` : `influencer-new-${redirectTo.replace(/\W/g, "")}`;

  return (
    <form action="/api/influencers" method="post" className="space-y-4">
      <input type="hidden" name="redirectTo" value={redirectTo} />
      <input type="hidden" name="id" value={influencer?.id ?? ""} />
      <input type="hidden" name="_action" value={influencer ? "update" : "create"} />

      <div>
        <Label htmlFor={`${key}-name`}>Influencer Name</Label>
        <Input id={`${key}-name`} name="name" placeholder="Dr. Kavya Fields" defaultValue={influencer?.name ?? ""} required />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <Label htmlFor={`${key}-channel`}>Primary Channel</Label>
          <Input id={`${key}-channel`} name="channel" placeholder="YouTube" defaultValue={influencer?.channel ?? ""} required />
        </div>
        <div>
          <Label htmlFor={`${key}-type`}>Influencer Type</Label>
          <Input id={`${key}-type`} name="influencerType" placeholder="Agri creator, FPO leader" defaultValue={influencer?.influencerType ?? ""} />
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <Label htmlFor={`${key}-region`}>Region</Label>
          <Input id={`${key}-region`} name="region" placeholder="Maharashtra" defaultValue={influencer?.region?.state ?? ""} />
        </div>
        <div>
          <Label htmlFor={`${key}-language`}>Language</Label>
          <Input id={`${key}-language`} name="primaryLanguage" placeholder="Marathi" defaultValue={influencer?.language?.name ?? ""} />
        </div>
      </div>
      <div>
        <Label htmlFor={`${key}-crop`}>Crop Expertise</Label>
        <Input id={`${key}-crop`} name="primaryCropFocus" placeholder="Cotton growers" defaultValue={influencer?.primaryCropFocus ?? ""} />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <Label htmlFor={`${key}-reach`}>Audience Size</Label>
          <Input id={`${key}-reach`} name="reachScore" type="number" min={0} defaultValue={influencer?.reachScore ?? 5000} />
        </div>
        <div>
          <Label htmlFor={`${key}-followers`}>Follower Count</Label>
          <Input id={`${key}-followers`} name="followerCount" type="number" min={0} defaultValue={influencer?.followerCount ?? 25000} />
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <Label htmlFor={`${key}-engagement`}>Engagement Rate</Label>
          <Input id={`${key}-engagement`} name="engagementRate" type="number" min={0} max={100} step="0.1" defaultValue={influencer?.engagementRate?.toString() ?? 8.5} />
        </div>
        <div>
          <Label htmlFor={`${key}-trust`}>Trust Score</Label>
          <Input id={`${key}-trust`} name="trustScore" type="number" min={0} max={100} defaultValue={influencer?.trustScore?.toString() ?? 80} />
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <Label htmlFor={`${key}-cost`}>Cost per Campaign</Label>
          <Input id={`${key}-cost`} name="costPerCampaign" type="number" min={0} step="0.01" placeholder="25000" defaultValue={influencer?.costPerCampaign?.toString() ?? ""} />
        </div>
        <div>
          <Label htmlFor={`${key}-format`}>Preferred Content Format</Label>
          <Input id={`${key}-format`} name="contentFormat" placeholder="Short video, voice note" defaultValue={influencer?.contentFormat ?? ""} />
        </div>
      </div>
      {!compact ? (
        <>
          <div>
            <Label htmlFor={`${key}-strength`}>Content Strength</Label>
            <Textarea id={`${key}-strength`} name="contentStrength" placeholder="Field demos and WhatsApp voice notes" defaultValue={influencer?.contentStrength ?? ""} />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <Label htmlFor={`${key}-phone`}>Contact Phone</Label>
              <Input id={`${key}-phone`} name="contactPhone" placeholder="+91 90000 00000" defaultValue={influencer?.contactPhone ?? ""} />
            </div>
            <div>
              <Label htmlFor={`${key}-terms`}>Commercial Terms</Label>
              <Input id={`${key}-terms`} name="commercialTerms" placeholder="Paid, commission, field demo honorarium" defaultValue={influencer?.commercialTerms ?? ""} />
            </div>
          </div>
        </>
      ) : null}
      <Button type="submit" className="w-full">
        {influencer ? "Save Influencer" : "Add Influencer"}
      </Button>
    </form>
  );
}
