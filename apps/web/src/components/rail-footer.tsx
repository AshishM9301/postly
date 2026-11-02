"use client";

import { ThemeToggle } from "~/components/theme-toggle";

export function RailFooter() {
  return (
    <div className="border-t p-2">
      <ThemeToggle
        showLabel
        className="w-full justify-start gap-3 px-3 [&_span]:opacity-0 [&_span]:transition-opacity [&_span]:duration-150 group-hover/nav:[&_span]:opacity-100 group-focus-within/nav:[&_span]:opacity-100"
      />
    </div>
  );
}
