"use client";

import { DataPrivacyButton } from "~/components/data-privacy-button";
import { SessionButton } from "~/components/session-button";
import { ThemeToggle } from "~/components/theme-toggle";

const labelClass =
  "[&_span]:opacity-0 [&_span]:transition-opacity [&_span]:duration-150 group-hover/nav:[&_span]:opacity-100 group-focus-within/nav:[&_span]:opacity-100";

export function RailFooter() {
  return (
    <div className="space-y-1 border-t p-2">
      <SessionButton
        showLabel
        className={`w-full justify-start gap-3 px-3 ${labelClass}`}
      />
      <DataPrivacyButton
        showLabel
        className={`w-full justify-start gap-3 px-3 ${labelClass}`}
      />
      <ThemeToggle
        showLabel
        className={`w-full justify-start gap-3 px-3 ${labelClass}`}
      />
    </div>
  );
}
