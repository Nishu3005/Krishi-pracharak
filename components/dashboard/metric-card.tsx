import { Card, CardDescription, CardTitle } from "@/components/ui/card";

export function MetricCard({
  title,
  value,
  description,
  accent = "default"
}: {
  title: string;
  value: string | number;
  description: string;
  accent?: "default" | "green" | "amber" | "blue";
}) {
  const accentClass = {
    default: "border-border",
    green: "border-primary/25 bg-primary/5",
    amber: "border-secondary/70 bg-secondary/25",
    blue: "border-sky-200 bg-sky-50/80"
  }[accent];

  return (
    <Card className={`bg-white/86 ${accentClass}`}>
      <CardDescription>{title}</CardDescription>
      <CardTitle className="mt-3 text-4xl tracking-normal">{value}</CardTitle>
      <p className="mt-2 text-sm text-foreground/66">{description}</p>
    </Card>
  );
}
