import Link from "next/link";
import { BarChart3, Bot, Boxes, DatabaseZap, Megaphone, Sprout } from "lucide-react";

import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: BarChart3 },
  { href: "/campaigns/create", label: "Create Campaign", icon: Megaphone },
  { href: "/data", label: "Data Hub", icon: DatabaseZap },
  { href: "/products", label: "Products", icon: Boxes },
  { href: "/influencers", label: "Influencers", icon: Bot }
] as const;

export function AppSidebar() {
  return (
    <aside className="grain hidden w-72 flex-col border-r border-border/60 bg-white/65 px-6 py-8 lg:flex">
      <div className="mb-10 flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground">
          <Sprout className="h-6 w-6" />
        </div>
        <div>
          <p className="font-serif text-2xl">Krishi Pracharak</p>
          <p className="text-sm text-foreground/60">Agri marketing intelligence</p>
        </div>
      </div>

      <nav className="space-y-2">
        {navItems.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium text-foreground/72 transition hover:bg-white hover:text-foreground"
            )}
          >
            <Icon className="h-5 w-5" />
            {label}
          </Link>
        ))}
      </nav>

      <div className="mt-auto rounded-3xl bg-primary/95 p-5 text-primary-foreground shadow-soft">
        <p className="font-serif text-xl">Rule-Based AI Core</p>
        <p className="mt-2 text-sm text-primary-foreground/80">
          Modular planning, segmentation, and content generation ready to swap with live LLMs later.
        </p>
      </div>
    </aside>
  );
}
