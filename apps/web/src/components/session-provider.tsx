"use client";

import { useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { toast } from "sonner";

import { SignInDialog } from "~/components/sign-in-dialog";
import { ApiError } from "~/lib/api/client";
import { getMe, rotateSessionAlias, signInPseudo } from "~/lib/api/endpoints";
import {
  generateSecret,
  getAccountSecret,
  saveAccountSecret,
  toBase64Url,
} from "~/lib/ghost";
import {
  clearSession,
  getSessionAlias,
  getSessionMode,
  getSessionToken,
  setSessionAlias,
  setSessionMode,
  setSessionToken,
  type ActiveSession,
  type SessionMode,
} from "~/lib/session";
import { clearMyVotes } from "~/lib/votes-store";

type SessionContextValue = {
  session: ActiveSession | null;
  openSignIn: () => void;
  signIn: (secret: string) => Promise<string>;
  signInNew: () => Promise<string>;
  signInStored: () => Promise<string>;
  signOut: () => void;
  rotateAlias: () => Promise<string>;
  refreshSession: () => void;
};

const SessionContext = createContext<SessionContextValue | null>(null);

function asMode(mode: string | null): SessionMode | null {
  return mode === "pseudonymous" || mode === "google" ? mode : null;
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [session, setSession] = useState<ActiveSession | null>(null);
  const [signInOpen, setSignInOpen] = useState(false);

  const resetPersonalQueries = useCallback(async () => {
    await Promise.all([
      queryClient.resetQueries({ queryKey: ["feed"] }),
      queryClient.resetQueries({ queryKey: ["comments"] }),
      queryClient.resetQueries({ queryKey: ["me"] }),
      queryClient.resetQueries({ queryKey: ["own-post-ids"] }),
    ]);
  }, [queryClient]);

  useEffect(() => {
    let active = true;
    const token = getSessionToken();
    if (!token) {
      return;
    }

    const alias = getSessionAlias();
    const mode = asMode(getSessionMode());
    if (alias && mode) {
      setSession({ token, alias, mode, userId: null });
    }

    void getMe()
      .then((me) => {
        if (!active) {
          return;
        }
        const serverMode = asMode(me.mode);
        if (me.alias && serverMode) {
          const next: ActiveSession = {
            token,
            alias: me.alias,
            mode: serverMode,
            userId: me.user_id,
          };
          setSession(next);
          setSessionAlias(next.alias);
          setSessionMode(next.mode);
        }
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }
        if (error instanceof ApiError && error.status === 401) {
          clearSession();
          setSession(null);
          toast.error("Your session expired. You are posting as a ghost.");
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const signIn = useCallback(
    async (secret: string) => {
      const auth = await signInPseudo(secret);
      setSessionToken(auth.token);
      setSessionAlias(auth.alias);
      setSessionMode(auth.mode);

      let next: ActiveSession = {
        token: auth.token,
        alias: auth.alias,
        mode: auth.mode,
        userId: null,
      };
      setSession(next);

      await saveAccountSecret(secret).catch(() => {
        toast.error(
          "Signed in, but the secret could not be saved to this device's vault.",
        );
      });
      clearMyVotes();
      await resetPersonalQueries();

      try {
        const me = await getMe();
        const serverMode = asMode(me.mode);
        if (me.alias && serverMode) {
          next = {
            ...next,
            alias: me.alias,
            mode: serverMode,
            userId: me.user_id,
          };
          setSession(next);
          setSessionAlias(next.alias);
          setSessionMode(next.mode);
        }
      } catch {
        // The auth response already carries a usable alias/session.
      }

      return next.alias;
    },
    [resetPersonalQueries],
  );

  const signInNew = useCallback(
    () => signIn(toBase64Url(generateSecret())),
    [signIn],
  );

  const signInStored = useCallback(async () => {
    const secret = await getAccountSecret();
    if (secret === null) {
      throw new Error("No saved account secret exists on this device.");
    }
    return signIn(secret);
  }, [signIn]);

  const signOut = useCallback(() => {
    clearSession();
    setSession(null);
    clearMyVotes();
    void resetPersonalQueries().then(() => {
      toast.success("Signed out. You are now posting as a ghost.");
    });
  }, [resetPersonalQueries]);

  const rotateAlias = useCallback(async () => {
    if (session === null) {
      throw new Error("You are not signed in.");
    }
    const result = await rotateSessionAlias();
    const mode = asMode(result.mode);
    if (mode === null) {
      throw new Error("The server returned an unexpected identity mode.");
    }
    const next: ActiveSession = { ...session, alias: result.alias, mode };
    setSession(next);
    setSessionAlias(result.alias);
    setSessionMode(mode);
    return result.alias;
  }, [session]);

  const refreshSession = useCallback(() => {
    const token = getSessionToken();
    if (!token) {
      setSession(null);
      return;
    }
    const alias = getSessionAlias();
    const mode = asMode(getSessionMode());
    setSession(alias && mode ? { token, alias, mode, userId: null } : null);
  }, []);

  const openSignIn = useCallback(() => setSignInOpen(true), []);

  const value = useMemo(
    () => ({
      session,
      openSignIn,
      signIn,
      signInNew,
      signInStored,
      signOut,
      rotateAlias,
      refreshSession,
    }),
    [
      session,
      openSignIn,
      signIn,
      signInNew,
      signInStored,
      signOut,
      rotateAlias,
      refreshSession,
    ],
  );

  return (
    <SessionContext.Provider value={value}>
      {children}
      <SignInDialog
        open={signInOpen}
        onOpenChange={setSignInOpen}
        session={session}
        signIn={signIn}
        signInNew={signInNew}
        signInStored={signInStored}
        signOut={signOut}
      />
    </SessionContext.Provider>
  );
}

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext);
  if (context === null) {
    throw new Error("useSession must be used inside SessionProvider");
  }
  return context;
}
