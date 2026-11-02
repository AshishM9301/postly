"use client";

const labelClass =
  "opacity-0 transition-opacity duration-150 group-hover/nav:opacity-100 group-focus-within/nav:opacity-100";

export function RailBrand() {
  return (
    <div className="flex h-16 shrink-0 items-center gap-3 overflow-hidden px-3.5">
      <div className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary text-lg font-bold text-primary-foreground">
        P
      </div>
      <div className={`min-w-0 ${labelClass}`}>
        <p className="truncate text-base leading-none font-semibold">Postly</p>
        <p className="truncate text-xs text-muted-foreground">Local problems</p>
      </div>
    </div>
  );
}
