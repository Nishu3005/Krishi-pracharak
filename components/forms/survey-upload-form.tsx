import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";

export function SurveyUploadForm() {
  return (
    <form action="/api/ingestion/upload" method="post" encType="multipart/form-data" className="space-y-4">
      <div>
        <Label htmlFor="csvType">CSV Type</Label>
        <Select id="csvType" name="csvType" defaultValue="auto-detect">
          <option value="auto-detect">Auto-detect</option>
          <option value="farmer survey">Farmer survey</option>
          <option value="product data">Product data</option>
          <option value="influencer data">Influencer data</option>
          <option value="campaign history">Campaign history</option>
        </Select>
      </div>
      <div>
        <Label htmlFor="surveyCsv">CSV File</Label>
        <Input id="surveyCsv" name="file" type="file" accept=".csv,text/csv" required />
      </div>
      <Button type="submit" className="w-full">
        Upload and Stage CSV
      </Button>
    </form>
  );
}
