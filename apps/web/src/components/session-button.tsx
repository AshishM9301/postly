"use client";

import { LogIn, UserCheck } from "lucide-react";

import { useSession } from "~/components/session-provider";
import { Button } from "~/components/ui/button";

export function SessionButton({
  className,
  showLabel = false,
}: {
  className?: string;
  showLabel?: boolean;
}) {
  const { session, openSignIn } = useSession();
  const label = session ? `Account (${session.alias})` : "Sign in";

  return (
    <Button
      type="button"
      variant="ghost"
      size={showLabel ? "sm" : "icon"}
      className={className}
      aria-label={label}
      title={label}
      onClick={openSignIn}
    >
      {session ? (
        <UserCheck className="size-5 text-primary" />
      ) : (
        <LogIn className="size-5" />
      )}
      {showLabel ? (
        <span className="whitespace-nowrap text-sm">
          {session ? "Account" : "Sign in"}
        </span>
      ) : (
        <span className="sr-only">{label}</span>
      )}
    </Button>
  );
}
