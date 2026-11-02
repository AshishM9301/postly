"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "~/components/ui/button";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { deleteMe, getMe } from "~/lib/api/endpoints";
import { describeApiError } from "~/lib/api-error";
import { clearSession, getSessionToken } from "~/lib/session";
import { clearMyVotes } from "~/lib/votes-store";

export function AccountDeletion({
  active,
  onDeleted,
}: {
  active: boolean;
  onDeleted?: () => void;
}) {
  const token = active ? getSessionToken() : null;
  const queryClient = useQueryClient();
  const [secret, setSecret] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (active) {
      setSecret("");
      setError(null);
    }
  }, [active]);

  const me = useQuery({
    queryKey: ["me", token],
    queryFn: getMe,
    enabled: active && token !== null,
    retry: false,
  });

  const mutation = useMutation({
    mutationFn: () =>
      deleteMe(me.data?.mode === "pseudonymous" ? secret : null),
    onSuccess: async () => {
      clearSession();
      clearMyVotes();
      await Promise.all([
        queryClient.resetQueries({ queryKey: ["feed"] }),
        queryClient.resetQueries({ queryKey: ["comments"] }),
        queryClient.resetQueries({ queryKey: ["me"] }),
        queryClient.resetQueries({ queryKey: ["own-post-ids"] }),
      ]);
      toast.success("Your account and its content were deleted");
      onDeleted?.();
    },
    onError: (mutationError) => {
      setError(describeApiError(mutationError));
    },
  });

  if (token === null) {
    return (
      <section className="space-y-2">
        <h3 className="font-medium">Account</h3>
        <p className="text-sm text-muted-foreground">
          No account session is stored on this device. You are posting as a
          ghost; account sign-in is a separate step.
        </p>
      </section>
    );
  }

  if (me.isPending) {
    return (
      <section className="space-y-2">
        <h3 className="font-medium">Account</h3>
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
          Checking your session…
        </p>
      </section>
    );
  }

  if (me.isError) {
    return (
      <section className="space-y-2">
        <h3 className="font-medium">Account</h3>
        <p role="alert" className="text-sm text-destructive">
          {describeApiError(me.error)}
        </p>
      </section>
    );
  }

  const pseudonymous = me.data.mode === "pseudonymous";

  function removeAccount() {
    setError(null);
    if (pseudonymous && !secret.trim()) {
      setError("Enter your account secret to delete a pseudonymous account.");
      return;
    }
    if (
      !window.confirm(
        "Delete your account permanently? Your posts (with photos), comments, votes, follows and notifications go with it. Replies to your comments stay. This cannot be undone.",
      )
    ) {
      return;
    }
    mutation.mutate();
  }

  return (
    <section className="space-y-3">
      <div>
        <h3 className="font-medium">Account</h3>
        <p className="text-sm text-muted-foreground">
          Signed in as {me.data.alias ?? "unknown"} ({me.data.mode}).
        </p>
      </div>

      <p className="flex items-start gap-2 text-sm text-destructive">
        <AlertTriangle className="mt-0.5 size-4 shrink-0" />
        <span>
          Deleting your account permanently removes its posts (and their media
          files), comments, votes, follows, area follows, reveals,
          notifications, sessions and push subscriptions. Replies to your
          comments are kept and move up a level.
        </span>
      </p>

      {pseudonymous ? (
        <div className="space-y-1.5">
          <Label htmlFor="delete-account-secret">Account secret</Label>
          <Input
            id="delete-account-secret"
            type="password"
            autoComplete="off"
            value={secret}
            onChange={(event) => setSecret(event.target.value)}
            placeholder="Your 32+ character account secret"
            disabled={mutation.isPending}
          />
          <p className="text-xs text-muted-foreground">
            This is the secret you signed up with. It is never sent anywhere
            except the delete request.
          </p>
        </div>
      ) : null}

      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}

      <Button
        type="button"
        variant="destructive"
        disabled={mutation.isPending}
        onClick={removeAccount}
      >
        {mutation.isPending ? (
          <Loader2 className="size-4 animate-spin" />
        ) : (
          <AlertTriangle className="size-4" />
        )}
        {mutation.isPending ? "Deleting…" : "Delete my account"}
      </Button>
    </section>
  );
}
