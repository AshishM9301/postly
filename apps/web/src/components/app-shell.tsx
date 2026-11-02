"use client";

import { AppHeader } from "~/components/app-header";
import { DesktopNav } from "~/components/desktop-nav";
import { FeedTabProvider } from "~/components/feed-tab-provider";
import { MobileTabBar } from "~/components/mobile-tab-bar";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <FeedTabProvider>
      <div className="min-h-screen bg-background">
        <DesktopNav />
        <div className="md:pl-16">
          <AppHeader />
          <main className="mx-auto w-full max-w-xl px-4 py-4 pb-[calc(5.5rem+env(safe-area-inset-bottom))] md:pb-8">
            {children}
          </main>
        </div>
        <MobileTabBar />
      </div>
    </FeedTabProvider>
  );
}
