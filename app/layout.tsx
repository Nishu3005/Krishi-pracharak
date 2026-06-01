import type { Metadata } from "next";

import "@/app/globals.css";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { MobileNav } from "@/components/layout/mobile-nav";

export const metadata: Metadata = {
  title: "Krishi Pracharak",
  description: "Agricultural AI marketing intelligence MVP"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className="flex min-h-screen">
          <AppSidebar />
          <main className="flex-1">
            <MobileNav />
            <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-10 lg:py-10">{children}</div>
          </main>
        </div>
      </body>
    </html>
  );
}
