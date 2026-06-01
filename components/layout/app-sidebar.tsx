"use client";

import Link from "next/link";
import {
  BarChart3,
  Bot,
  Boxes,
  DatabaseZap,
  Megaphone,
  PanelLeftClose,
  PanelLeftOpen,
  Sprout
} from "lucide-react";
import { useState } from "react";

import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: BarChart3 },
  { href: "/campaigns/create", label: "Create Campaign", icon: Megaphone },
  { href: "/data", label: "Data Hub", icon: DatabaseZap },
  { href: "/products", label: "Products", icon: Boxes },
  { href: "/influencers", label: "Influencers", icon: Bot }
] as const;

export function AppSidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        "grain hidden flex-col border-r border-border/60 bg-white/65 py-8 transition-[width,padding] duration-300 lg:flex",
        isCollapsed ? "w-24 px-4" : "w-72 px-6"
      )}
    >
      <div className={cn("mb-10 flex items-center gap-3", isCollapsed && "justify-center")}>
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground">
          <Sprout className="h-6 w-6" />
        </div>
        <div className={cn("min-w-0", isCollapsed && "sr-only")}>
          <p className="font-serif text-2xl">Krishi Pracharak</p>
          <p className="text-sm text-foreground/60">Agri marketing intelligence</p>
        </div>
      </div>

      <button
        type="button"
        onClick={() => setIsCollapsed((current) => !current)}
        className={cn(
          "mb-6 flex h-10 items-center gap-3 rounded-2xl border border-border/70 bg-white/75 px-4 text-sm font-medium text-foreground/72 shadow-sm transition hover:bg-white hover:text-foreground",
          isCollapsed && "mx-auto w-12 justify-center px-0"
        )}
        aria-label={isCollapsed ? "Open sidebar" : "Close sidebar"}
        title={isCollapsed ? "Open sidebar" : "Close sidebar"}
      >
        {isCollapsed ? <PanelLeftOpen className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}
        {!isCollapsed && <span>Close</span>}
      </button>

      <nav className="space-y-2">
        {navItems.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium text-foreground/72 transition hover:bg-white hover:text-foreground",
              isCollapsed && "justify-center px-0"
            )}
            title={isCollapsed ? label : undefined}
          >
            <Icon className="h-5 w-5" />
            <span className={cn(isCollapsed && "sr-only")}>{label}</span>
          </Link>
        ))}
      </nav>

      <div className={cn("mt-auto rounded-3xl bg-primary/95 p-5 text-primary-foreground shadow-soft", isCollapsed && "hidden")}>
        <p className="font-serif text-xl">Rule-Based AI Core</p>
        <p className="mt-2 text-sm text-primary-foreground/80">
          Modular planning, segmentation, and content generation ready to swap with live LLMs later.
        </p>
      </div>
    </aside>
  );
}
