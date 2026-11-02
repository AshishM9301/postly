"use client";

import { ShieldCheck } from "lucide-react";

import { useDataPrivacy } from "~/components/data-provider";
import { Button } from "~/components/ui/button";

export function DataPrivacyButton({
  className,
  showLabel = false,
}: {
  className?: string;
  showLabel?: boolean;
}) {
  const { openDataPrivacy } = useDataPrivacy();
  const label = "Data & privacy";

  return (
    <Button
      type="button"
      variant="ghost"
      size={showLabel ? "sm" : "icon"}
      className={className}
      aria-label={label}
      title={label}
      onClick={openDataPrivacy}
    >
      <ShieldCheck className="size-5" />
      {showLabel ? (
        <span className="whitespace-nowrap text-sm">Data &amp; privacy</span>
      ) : (
        <span className="sr-only">{label}</span>
      )}
    </Button>
  );
}
