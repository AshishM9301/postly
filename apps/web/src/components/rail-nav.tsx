"use client";

import { Plus } from "lucide-react";

import { useComposer } from "~/components/composer-provider";
import { FEED_TABS, useFeedTab } from "~/components/feed-tab-provider";
import { cn } from "~/lib/utils";

const labelClass =
  "whitespace-nowrap opacity-0 transition-opacity duration-150 group-hover/nav:opacity-100 group-focus-within/nav:opacity-100";

export function RailNav() {
  const { tab, selectTab } = useFeedTab();
  const { openComposer } = useComposer();

  return (
    <nav className="flex flex-1 flex-col gap-1 overflow-hidden px-2 py-2">
      {FEED_TABS.map(({ value, label, icon: Icon }) => {
        const active = tab === value;
        return (
          <button
            key={value}
            type="button"
            title={label}
            aria-current={active ? "page" : undefined}
            onClick={() => selectTab(value)}
            className={cn(
              "flex h-11 w-full items-center gap-3 overflow-hidden rounded-lg px-3 text-sm font-medium transition-colors",
              active
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            <Icon className="size-5 shrink-0" />
            <span className={labelClass}>{label}</span>
          </button>
        );
      })}

      <button
        type="button"
        title="Report a problem"
        onClick={openComposer}
        className="mt-1 flex h-11 w-full items-center gap-3 overflow-hidden rounded-lg bg-primary/10 px-3 text-sm font-semibold text-primary transition-colors hover:bg-primary/15"
      >
        <Plus className="size-5 shrink-0" />
        <span className={labelClass}>Report</span>
      </button>
    </nav>
  );
}
