import { Badge } from "@/components/ui/badge";

type PageHeaderProps = {
  eyebrow: string;
  title: string;
  description: string;
  badge?: string;
};

export function PageHeader({ eyebrow, title, description, badge }: PageHeaderProps) {
  return (
    <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-primary/70">{eyebrow}</p>
        <h1 className="mt-2 font-serif text-4xl text-foreground">{title}</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-foreground/72">{description}</p>
      </div>
      {badge ? <Badge>{badge}</Badge> : null}
    </div>
  );
}
