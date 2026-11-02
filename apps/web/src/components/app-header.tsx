"use client";

import { Plus, UserRound } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { useComposer } from "~/components/composer-provider";
import { DataPrivacyButton } from "~/components/data-privacy-button";
import { SessionButton } from "~/components/session-button";
import { useSession } from "~/components/session-provider";
import { ThemeToggle } from "~/components/theme-toggle";
import { Avatar, AvatarFallback } from "~/components/ui/avatar";
import { Button } from "~/components/ui/button";
import { describeApiError } from "~/lib/api-error";
import { ensureGhostIdentity, rotateGhostAlias } from "~/lib/identity";

export function AppHeader() {
  const [ghostAlias, setGhostAlias] = useState<string | null>(null);
  const [rotating, setRotating] = useState(false);
  const { openComposer } = useComposer();
  const { session, rotateAlias } = useSession();

  useEffect(() => {
    let cancelled = false;
    void ensureGhostIdentity()
      .then((identity) => {
        if (!cancelled) {
          setGhostAlias(identity.alias);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setGhostAlias(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const alias = session?.alias ?? ghostAlias;
  const mode = session?.mode ?? "ghost";

  async function rotate() {
    if (rotating) {
      return;
    }
    setRotating(true);
    try {
      if (session) {
        const next = await rotateAlias();
        toast.success(`You are now posting as ${next}`);
      } else {
        const next = rotateGhostAlias();
        setGhostAlias(next);
        toast.success(`You are now posting as ${next}`);
      }
    } catch (error) {
      toast.error(describeApiError(error));
    } finally {
      setRotating(false);
    }
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
            disabled={rotating}
            onClick={() => void rotate()}
            title={`Posting as ${alias ?? "…"} (${mode}) — rotate alias`}
            aria-label={`Posting as ${alias ?? "unknown"} (${mode}). Rotate alias`}
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
          <SessionButton className="md:hidden" />
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
