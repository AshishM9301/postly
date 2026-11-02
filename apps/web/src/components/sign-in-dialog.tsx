"use client";

import { Loader2, LogIn, Sparkles, UserCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "~/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "~/components/ui/dialog";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { describeApiError } from "~/lib/api-error";
import { getAccountSecret } from "~/lib/ghost";
import type { ActiveSession } from "~/lib/session";

type Action = "new" | "stored" | "manual" | "signout" | null;

export function SignInDialog({
  open,
  onOpenChange,
  session,
  signIn,
  signInNew,
  signInStored,
  signOut,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  session: ActiveSession | null;
  signIn: (secret: string) => Promise<string>;
  signInNew: () => Promise<string>;
  signInStored: () => Promise<string>;
  signOut: () => void;
}) {
  const [storedSecret, setStoredSecret] = useState<string | null | undefined>(
    undefined,
  );
  const [manualSecret, setManualSecret] = useState("");
  const [action, setAction] = useState<Action>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    setError(null);
    setManualSecret("");
    setStoredSecret(undefined);
    void getAccountSecret()
      .then(setStoredSecret)
      .catch(() => setStoredSecret(null));
  }, [open]);

  async function run(
    kind: Exclude<Action, "signout" | null>,
    operation: () => Promise<string>,
  ) {
    setAction(kind);
    setError(null);
    try {
      const alias = await operation();
      toast.success(`Signed in as ${alias}`);
      setManualSecret("");
      onOpenChange(false);
    } catch (mutationError) {
      setError(describeApiError(mutationError));
    } finally {
      setAction(null);
    }
  }

  function createNew() {
    if (
      !window.confirm(
        "Create a new pseudonymous account? A secret will be generated and stored in this device's vault. If the vault is cleared, you lose access to the account — its content stays on the server.",
      )
    ) {
      return;
    }
    void run("new", signInNew);
  }

  function signInWithStoredSecret() {
    void run("stored", signInStored);
  }

  function signInWithManualSecret() {
    const secret = manualSecret.trim();
    if (secret.length < 32) {
      setError("A pseudonymous secret must be at least 32 characters.");
      return;
    }
    void run("manual", () => signIn(secret));
  }

  function confirmSignOut() {
    if (
      !window.confirm(
        "Sign out? The session token and alias leave this device. Your account and its content stay on the server. The account secret stays in this device's vault so you can sign back in.",
      )
    ) {
      return;
    }
    setAction("signout");
    signOut();
    setAction(null);
    onOpenChange(false);
  }

  if (session) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <UserCheck className="size-5 text-primary" />
              Signed in
            </DialogTitle>
            <DialogDescription>
              You are posting as <strong>{session.alias}</strong> (
              {session.mode}).
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              The session is stored on this device and survives a reload. Your
              account secret stays in the device vault; keep it if you want to
              sign in again after signing out.
            </p>
            <Button
              type="button"
              variant="outline"
              onClick={confirmSignOut}
              disabled={action === "signout"}
            >
              Sign out
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Sign in</DialogTitle>
          <DialogDescription>
            A pseudonymous identity needs no email or phone. The secret is the
            only key to the account.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {storedSecret ? (
            <section className="space-y-2">
              <h3 className="text-sm font-medium">This device</h3>
              <p className="text-sm text-muted-foreground">
                An account secret is already saved in this device’s vault.
              </p>
              <Button
                type="button"
                onClick={signInWithStoredSecret}
                disabled={action !== null}
              >
                {action === "stored" ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <LogIn className="size-4" />
                )}
                Sign in with this device’s secret
              </Button>
            </section>
          ) : null}

          <section className="space-y-2">
            <h3 className="text-sm font-medium">New identity</h3>
            <p className="text-sm text-muted-foreground">
              Generate a 256-bit secret on this device, then create or reopen the
              account that belongs to it.
            </p>
            <Button
              type="button"
              variant="outline"
              onClick={createNew}
              disabled={action !== null || storedSecret === undefined}
            >
              {action === "new" ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Sparkles className="size-4" />
              )}
              Create a pseudonymous identity
            </Button>
          </section>

          <form
            className="space-y-2 border-t pt-4"
            onSubmit={(event) => {
              event.preventDefault();
              signInWithManualSecret();
            }}
          >
            <h3 className="text-sm font-medium">I already have a secret</h3>
            <div className="space-y-1.5">
              <Label htmlFor="account-secret">Account secret</Label>
              <Input
                id="account-secret"
                type="password"
                autoComplete="off"
                value={manualSecret}
                onChange={(event) => setManualSecret(event.target.value)}
                placeholder="Paste your 32+ character secret"
                disabled={action !== null}
              />
            </div>
            <Button
              type="submit"
              variant="outline"
              disabled={action !== null || manualSecret.trim().length === 0}
            >
              {action === "manual" ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <LogIn className="size-4" />
              )}
              Sign in with this secret
            </Button>
          </form>

          {error ? (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          ) : null}

          <p className="text-xs text-muted-foreground">
            The secret is stored only in this device’s vault. The server stores
            a hash of it, never the secret itself.
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}
