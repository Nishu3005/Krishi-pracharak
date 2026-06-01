import { Edit3, Trash2 } from "lucide-react";

import { ProductForm } from "@/components/forms/product-form";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { getDataManagementData } from "@/lib/data";

export const dynamic = "force-dynamic";

function money(value: unknown, unit?: string | null) {
  if (value === null || value === undefined || value === "") {
    return "N/A";
  }
  return `₹${Number(value).toLocaleString("en-IN")}${unit ? ` / ${unit}` : ""}`;
}

function flagLabel(value: boolean) {
  return value ? "Yes" : "No";
}

export default async function ProductsPage({
  searchParams
}: {
  searchParams: { status?: string };
}) {
  const { products } = await getDataManagementData();

  return (
    <div>
      <PageHeader
        eyebrow="Catalog"
        title="Products"
        description="Maintain product master data, crop-stage fit, threat relevance, pricing, and sustainability signals."
        badge={`${products.length} products`}
      />

      {searchParams.status ? (
        <div className="mb-6 rounded-2xl border border-border bg-white/82 px-4 py-3 text-sm text-foreground/72 shadow-soft">
          Latest action: <span className="font-semibold">{searchParams.status.replaceAll("-", " ")}</span>
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[0.78fr_1.22fr]">
        <Card className="bg-white/88">
          <CardTitle>Add Product</CardTitle>
          <CardDescription className="mt-1">Create a product record for segmentation and campaign planning.</CardDescription>
          <div className="mt-6">
            <ProductForm redirectTo="/products" />
          </div>
        </Card>

        <Card className="bg-white/88">
          <CardTitle>Product List</CardTitle>
          <CardDescription className="mt-1">All products currently available in the portfolio.</CardDescription>
          <div className="mt-6 overflow-x-auto">
            <table className="w-full min-w-[1040px] border-separate border-spacing-0 text-left text-sm">
              <thead>
                <tr className="text-xs uppercase text-foreground/48">
                  <th className="border-b border-border pb-3 font-semibold">Product</th>
                  <th className="border-b border-border pb-3 font-semibold">Category</th>
                  <th className="border-b border-border pb-3 font-semibold">Type</th>
                  <th className="border-b border-border pb-3 font-semibold">Price</th>
                  <th className="border-b border-border pb-3 font-semibold">Crop Stage</th>
                  <th className="border-b border-border pb-3 font-semibold">Target Pest</th>
                  <th className="border-b border-border pb-3 font-semibold">Organic</th>
                  <th className="border-b border-border pb-3 font-semibold">Sustainable</th>
                  <th className="border-b border-border pb-3 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody>
                {products.map((product) => (
                  <tr key={product.id} className="align-top">
                    <td className="border-b border-border/65 py-4 pr-4">
                      <p className="font-semibold">{product.name}</p>
                      <p className="mt-1 max-w-[260px] text-xs leading-5 text-foreground/55">{product.positioning || "No positioning added."}</p>
                    </td>
                    <td className="border-b border-border/65 py-4 pr-4">{product.category}</td>
                    <td className="border-b border-border/65 py-4 pr-4 text-foreground/68">{product.productType || "N/A"}</td>
                    <td className="border-b border-border/65 py-4 pr-4">{money(product.pricePerUnit, product.unitType)}</td>
                    <td className="border-b border-border/65 py-4 pr-4 text-foreground/68">{product.cropStageRelevance || "All"}</td>
                    <td className="border-b border-border/65 py-4 pr-4 text-foreground/68">{product.targetPestType || "N/A"}</td>
                    <td className="border-b border-border/65 py-4 pr-4">{flagLabel(product.organicFlag)}</td>
                    <td className="border-b border-border/65 py-4 pr-4">{flagLabel(product.sustainableFlag)}</td>
                    <td className="border-b border-border/65 py-4">
                      <Badge>{product.status}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      <Card className="mt-8 bg-white/88">
        <CardTitle>Product-Crop Fit Table</CardTitle>
        <CardDescription className="mt-1">Approved fit records connecting products to crops, threats, stages, and relevance scores.</CardDescription>
        <div className="mt-6 overflow-x-auto">
          <table className="w-full min-w-[900px] border-separate border-spacing-0 text-left text-sm">
            <thead>
              <tr className="text-xs uppercase text-foreground/48">
                <th className="border-b border-border pb-3 font-semibold">Product</th>
                <th className="border-b border-border pb-3 font-semibold">Crop</th>
                <th className="border-b border-border pb-3 font-semibold">Outbreak Type</th>
                <th className="border-b border-border pb-3 font-semibold">Outbreak Name</th>
                <th className="border-b border-border pb-3 font-semibold">Recommended Stage</th>
                <th className="border-b border-border pb-3 font-semibold">Relevance</th>
                <th className="border-b border-border pb-3 font-semibold">Approved</th>
              </tr>
            </thead>
            <tbody>
              {products.flatMap((product) =>
                product.cropFits.length ? (
                  product.cropFits.map((fit) => (
                    <tr key={fit.id}>
                      <td className="border-b border-border/65 py-4 pr-4 font-medium">{product.name}</td>
                      <td className="border-b border-border/65 py-4 pr-4">{fit.crop.name}</td>
                      <td className="border-b border-border/65 py-4 pr-4 text-foreground/68">{fit.outbreakType || "N/A"}</td>
                      <td className="border-b border-border/65 py-4 pr-4 text-foreground/68">{fit.outbreakName || "N/A"}</td>
                      <td className="border-b border-border/65 py-4 pr-4 text-foreground/68">{fit.recommendedStage || "N/A"}</td>
                      <td className="border-b border-border/65 py-4 pr-4">{fit.relevanceScore ? `${fit.relevanceScore}%` : "N/A"}</td>
                      <td className="border-b border-border/65 py-4">{flagLabel(fit.approvedFlag)}</td>
                    </tr>
                  ))
                ) : (
                  <tr key={`empty-${product.id}`}>
                    <td className="border-b border-border/65 py-4 pr-4 font-medium">{product.name}</td>
                    <td className="border-b border-border/65 py-4 text-foreground/55" colSpan={6}>
                      No crop-fit records yet.
                    </td>
                  </tr>
                )
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="mt-8 grid gap-6 xl:grid-cols-2">
        {products.map((product) => (
          <Card key={product.id} className="bg-white/88">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <Edit3 className="h-5 w-5 text-primary" />
                  <CardTitle>Edit {product.name}</CardTitle>
                </div>
                <CardDescription className="mt-1">Update product details or remove this product from the MVP database.</CardDescription>
              </div>
              <form action="/api/products" method="post">
                <input type="hidden" name="redirectTo" value="/products" />
                <input type="hidden" name="id" value={product.id} />
                <input type="hidden" name="_action" value="delete" />
                <button
                  type="submit"
                  className="inline-flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-800"
                >
                  <Trash2 className="h-4 w-4" />
                  Delete
                </button>
              </form>
            </div>
            <div className="mt-6">
              <ProductForm redirectTo="/products" product={product} compact />
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
