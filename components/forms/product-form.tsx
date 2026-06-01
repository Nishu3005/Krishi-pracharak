import type { Product } from "@prisma/client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export function ProductForm({
  redirectTo,
  product,
  compact = false
}: {
  redirectTo: string;
  product?: Product;
  compact?: boolean;
}) {
  const key = product ? `product-${product.id}` : `product-new-${redirectTo.replace(/\W/g, "")}`;

  return (
    <form action="/api/products" method="post" className="space-y-4">
      <input type="hidden" name="redirectTo" value={redirectTo} />
      <input type="hidden" name="id" value={product?.id ?? ""} />
      <input type="hidden" name="_action" value={product ? "update" : "create"} />

      <div>
        <Label htmlFor={`${key}-name`}>Product Name</Label>
        <Input id={`${key}-name`} name="name" placeholder="CropShield Pro" defaultValue={product?.name ?? ""} required />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <Label htmlFor={`${key}-category`}>Category</Label>
          <Input id={`${key}-category`} name="category" placeholder="Insecticide" defaultValue={product?.category ?? ""} required />
        </div>
        <div>
          <Label htmlFor={`${key}-type`}>Product Type</Label>
          <Input id={`${key}-type`} name="productType" placeholder="Chemical, biological, hybrid seed" defaultValue={product?.productType ?? ""} />
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <Label htmlFor={`${key}-price`}>Price per Unit</Label>
          <Input id={`${key}-price`} name="pricePerUnit" type="number" step="0.01" placeholder="850" defaultValue={product?.pricePerUnit?.toString() ?? ""} />
        </div>
        <div>
          <Label htmlFor={`${key}-unit`}>Unit Type</Label>
          <Input id={`${key}-unit`} name="unitType" placeholder="litre, kg, packet" defaultValue={product?.unitType ?? ""} />
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <Label htmlFor={`${key}-threat`}>Target Pest Type</Label>
          <Input id={`${key}-threat`} name="targetPestType" placeholder="Insect, fungus, weed" defaultValue={product?.targetPestType ?? ""} />
        </div>
        <div>
          <Label htmlFor={`${key}-stage`}>Crop Stage Relevance</Label>
          <Input id={`${key}-stage`} name="cropStageRelevance" placeholder="Vegetative, flowering" defaultValue={product?.cropStageRelevance ?? ""} />
        </div>
      </div>
      {!compact ? (
        <>
          <div>
            <Label htmlFor={`${key}-active`}>Active Ingredient</Label>
            <Input id={`${key}-active`} name="activeIngredient" placeholder="Lambda-cyhalothrin" defaultValue={product?.activeIngredient ?? ""} />
          </div>
          <div>
            <Label htmlFor={`${key}-positioning`}>Description / Positioning</Label>
            <Textarea
              id={`${key}-positioning`}
              name="positioning"
              placeholder="High-efficacy pest control with low spray complexity"
              defaultValue={product?.positioning ?? ""}
            />
          </div>
        </>
      ) : null}
      <div className="grid gap-3 md:grid-cols-2">
        <label className="flex items-center gap-2 rounded-xl border border-border bg-white/80 px-3 py-2 text-sm">
          <input type="checkbox" name="organicFlag" value="true" defaultChecked={product?.organicFlag ?? false} />
          Organic flag
        </label>
        <label className="flex items-center gap-2 rounded-xl border border-border bg-white/80 px-3 py-2 text-sm">
          <input type="checkbox" name="sustainableFlag" value="true" defaultChecked={product?.sustainableFlag ?? false} />
          Sustainable flag
        </label>
      </div>
      <Button type="submit" className="w-full">
        {product ? "Save Product" : "Add Product"}
      </Button>
    </form>
  );
}
