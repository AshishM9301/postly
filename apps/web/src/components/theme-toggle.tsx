"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

import { Button } from "~/components/ui/button";

export function ThemeToggle({
  className,
  showLabel = false,
}: {
  className?: string;
  showLabel?: boolean;
}) {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const isDark = mounted && resolvedTheme === "dark";
  const next = isDark ? "light" : "dark";
  const label = `Switch to ${next} theme`;

  return (
    <Button
      type="button"
      variant="ghost"
      size={showLabel ? "sm" : "icon"}
      className={className}
      aria-label={label}
      title={label}
      onClick={() => setTheme(next)}
    >
      {isDark ? <Sun className="size-5" /> : <Moon className="size-5" />}
      {showLabel ? (
        <span className="whitespace-nowrap text-sm">{isDark ? "Light" : "Dark"}</span>
      ) : (
        <span className="sr-only">{label}</span>
      )}
    </Button>
  );
}
