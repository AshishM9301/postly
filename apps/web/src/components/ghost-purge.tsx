"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Loader2, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "~/components/ui/button";
import { purgeGhost } from "~/lib/api/endpoints";
import { describeApiError } from "~/lib/api-error";
import {
  clearSessionAlias,
  deleteSessionKey,
  getSessionKey,
  listOwnCommentIds,
  listOwnPostEntries,
  toBase64Url,
} from "~/lib/ghost";
import { clearMyVotes } from "~/lib/votes-store";

async function vaultSummary() {
  const [posts, comments, sessionKey] = await Promise.all([
    listOwnPostEntries(),
    listOwnCommentIds(),
    getSessionKey(),
  ]);
  return {
    posts: posts.length,
    comments: comments.length,
    hasSessionKey: sessionKey !== null,
  };
}

export function GhostPurge({ active }: { active: boolean }) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{
    posts: number;
    comments: number;
    votes: number;
  } | null>(null);

  useEffect(() => {
    if (active) {
      setError(null);
      setResult(null);
    }
  }, [active]);

  const vault = useQuery({
    queryKey: ["vault-summary"],
    queryFn: vaultSummary,
    enabled: active,
  });

  const mutation = useMutation({
    mutationFn: async () => {
      const sessionKey = await getSessionKey();
      if (sessionKey === null) {
        throw new Error("No ghost session key exists on this device.");
      }
      return purgeGhost(toBase64Url(sessionKey));
    },
    onSuccess: async (purged) => {
      await deleteSessionKey();
      clearSessionAlias();
      clearMyVotes();
      await Promise.all([
        queryClient.resetQueries({ queryKey: ["feed"] }),
        queryClient.resetQueries({ queryKey: ["comments"] }),
        queryClient.resetQueries({ queryKey: ["vault-summary"] }),
        queryClient.resetQueries({ queryKey: ["own-post-ids"] }),
      ]);
      setResult(purged);
      toast.success(
        `Server deleted ${purged.posts} posts, ${purged.comments} comments and ${purged.votes} votes`,
      );
    },
    onError: (mutationError) => {
      setError(describeApiError(mutationError));
    },
  });

  function purge() {
    setError(null);
    if (
      !window.confirm(
        "Purge this browser's ghost session? The server will delete every post, comment and vote it can match to this device's session key. Content created with a separate per-post or per-comment key is NOT covered and must be deleted individually. This cannot be undone.",
      )
    ) {
      return;
    }
    mutation.mutate();
  }

  if (vault.isPending) {
    return (
      <section className="space-y-2">
        <h3 className="font-medium">Ghost data on this device</h3>
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
          Reading the local key vault…
        </p>
      </section>
    );
  }

  if (vault.isError) {
    return (
      <section className="space-y-2">
        <h3 className="font-medium">Ghost data on this device</h3>
        <p role="alert" className="text-sm text-destructive">
          Could not read the local key vault.
        </p>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => void vault.refetch()}
        >
          <RefreshCw className="size-4" />
          Try again
        </Button>
      </section>
    );
  }

  return (
    <section className="space-y-3">
      <div>
        <h3 className="font-medium">Ghost data on this device</h3>
        <p className="text-sm text-muted-foreground">
          This browser holds keys for {vault.data.posts} post
          {vault.data.posts === 1 ? "" : "s"} and {vault.data.comments} comment
          {vault.data.comments === 1 ? "" : "s"}.
        </p>
      </div>

      <p className="flex items-start gap-2 text-sm text-destructive">
        <AlertTriangle className="mt-0.5 size-4 shrink-0" />
        <span>
          The session purge only covers content derived from the session key
          (mostly votes). Posts and comments created with their own per-item
          keys are <strong>not</strong> swept — delete those individually.
          This cannot be undone.
        </span>
      </p>

      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}

      {result ? (
        <p role="status" className="rounded-lg bg-muted p-3 text-sm">
          Server deleted <strong>{result.posts}</strong> posts,{" "}
          <strong>{result.comments}</strong> comments and{" "}
          <strong>{result.votes}</strong> votes. The session key was removed
          from this device.
        </p>
      ) : null}

      <Button
        type="button"
        variant="destructive"
        disabled={mutation.isPending}
        onClick={purge}
      >
        {mutation.isPending ? (
          <Loader2 className="size-4 animate-spin" />
        ) : (
          <AlertTriangle className="size-4" />
        )}
        {mutation.isPending ? "Purging…" : "Purge everything from this device"}
      </Button>
    </section>
  );
}
