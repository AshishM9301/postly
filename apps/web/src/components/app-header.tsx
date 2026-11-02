"use client";

import { Plus, UserRound } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { useComposer } from "~/components/composer-provider";
import { DataPrivacyButton } from "~/components/data-privacy-button";
import { ThemeToggle } from "~/components/theme-toggle";
import { Avatar, AvatarFallback } from "~/components/ui/avatar";
import { Button } from "~/components/ui/button";
import { ensureGhostIdentity, rotateGhostAlias } from "~/lib/identity";

export function AppHeader() {
  const [alias, setAlias] = useState<string | null>(null);
  const { openComposer } = useComposer();

  useEffect(() => {
    let cancelled = false;
    void ensureGhostIdentity()
      .then((identity) => {
        if (!cancelled) {
          setAlias(identity.alias);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setAlias(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function rotate() {
    const next = rotateGhostAlias();
    setAlias(next);
    toast.success(`You are now posting as ${next}`);
  }

  return (
    <header className="sticky top-0 z-40 border-b bg-background/90 backdrop-blur">
      <div className="mx-auto flex w-full max-w-xl items-center justify-between gap-3 px-4 py-3">
        <div className="flex min-w-0 items-center gap-2">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary text-lg font-bold text-primary-foreground">
            P
          </div>
          <div className="min-w-0">
            <h1 className="text-lg leading-none font-semibold">Postly</h1>
            <p className="truncate text-xs text-muted-foreground">
              Local problems, community answers
            </p>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-1.5">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={rotate}
            title="Rotate your anonymous alias"
            aria-label="Rotate your anonymous alias"
          >
            <Avatar size="sm">
              <AvatarFallback className="bg-muted text-muted-foreground">
                <UserRound className="size-3.5" />
              </AvatarFallback>
            </Avatar>
            <span className="hidden max-w-28 truncate sm:inline">
              {alias ?? "…"}
            </span>
          </Button>
          <ThemeToggle className="md:hidden" />
          <DataPrivacyButton className="md:hidden" />
          <Button
            type="button"
            size="sm"
            className="gap-1.5"
            onClick={openComposer}
          >
            <Plus className="size-4" />
            Report
          </Button>
        </div>
      </div>
    </header>
  );
}
