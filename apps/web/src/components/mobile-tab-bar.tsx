"use client";

import { Plus } from "lucide-react";

import { useComposer } from "~/components/composer-provider";
import { FEED_TABS, useFeedTab } from "~/components/feed-tab-provider";
import { cn } from "~/lib/utils";

export function MobileTabBar() {
  const { tab, selectTab } = useFeedTab();
  const { openComposer } = useComposer();

  return (
    <nav
      aria-label="Primary mobile"
      className="fixed inset-x-0 bottom-0 z-50 border-t bg-background/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden"
    >
      <div className="grid grid-cols-5">
        {FEED_TABS.map(({ value, label, icon: Icon }) => {
          const active = tab === value;
          return (
            <button
              key={value}
              type="button"
              aria-current={active ? "page" : undefined}
              onClick={() => selectTab(value)}
              className={cn(
                "flex h-14 flex-col items-center justify-center gap-0.5 text-[10px] font-medium transition-colors",
                active ? "text-primary" : "text-muted-foreground hover:text-foreground",
              )}
            >
              <Icon className={cn("size-5", active && "fill-current")} />
              <span>{label}</span>
            </button>
          );
        })}

        <button
          type="button"
          onClick={openComposer}
          className="flex h-14 flex-col items-center justify-center gap-0.5 text-[10px] font-semibold text-primary transition-colors hover:text-primary/80"
        >
          <Plus className="size-5" />
          <span>Report</span>
        </button>
      </div>
    </nav>
  );
}
