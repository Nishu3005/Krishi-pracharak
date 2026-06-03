import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";

export function SurveyUploadForm({
  provider,
  model,
  apiConfigured
}: {
  provider: string;
  model: string;
  apiConfigured: boolean;
}) {
  return (
    <form action="/api/ingestion/upload" method="post" encType="multipart/form-data" className="space-y-4">
      <div className="rounded-xl border border-border bg-muted/35 p-4 text-sm">
        <p className="font-semibold">AI Provider: {provider}</p>
        <p className="mt-1 text-foreground/66">Model: {model}</p>
        <p className="mt-3 text-amber-800">Full CSV content will be sent to TokenRouter API for analysis.</p>
        {!apiConfigured ? (
          <p className="mt-3 font-semibold text-red-700">TokenRouter API key missing. Real AI is required for this workflow.</p>
        ) : null}
      </div>
      <div>
        <Label htmlFor="csvType">CSV Type</Label>
        <Select id="csvType" name="csvType" defaultValue="auto-detect">
          <option value="auto-detect">Auto-detect</option>
          <option value="farmer_survey">Farmer survey</option>
          <option value="product_data">Product data</option>
          <option value="influencer_data">Influencer data</option>
          <option value="campaign_history">Campaign history</option>
        </Select>
      </div>
      <div>
        <Label htmlFor="surveyCsv">CSV File</Label>
        <Input id="surveyCsv" name="file" type="file" accept=".csv,text/csv" required />
      </div>
      <Button type="submit" className="w-full" disabled={!apiConfigured}>
        Upload and Stage CSV
      </Button>
    </form>
  );
}
