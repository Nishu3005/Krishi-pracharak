import Link from "next/link";

export function MobileNav() {
  return (
    <div className="sticky top-0 z-20 border-b border-border/70 bg-background/95 px-4 py-3 backdrop-blur lg:hidden">
      <div className="flex items-center justify-between">
        <div>
          <p className="font-serif text-xl">KrishiPulse AI</p>
          <p className="text-xs text-foreground/60">Hackathon MVP</p>
        </div>
        <Link
          href="/campaigns/create"
          className="rounded-xl bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground"
        >
          Create Campaign
        </Link>
      </div>
    </div>
  );
}
