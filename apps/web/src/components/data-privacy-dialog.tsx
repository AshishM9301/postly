"use client";

import { AccountDeletion } from "~/components/account-deletion";
import { GhostPurge } from "~/components/ghost-purge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "~/components/ui/dialog";

export function DataPrivacyDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Data & privacy</DialogTitle>
          <DialogDescription>
            Deletion is permanent. Ghost keys live only on this device, so a
            key can never be recovered from the server.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5">
          <AccountDeletion active={open} onDeleted={() => onOpenChange(false)} />
          <div className="border-t pt-4">
            <GhostPurge active={open} />
          </div>
          <div className="border-t pt-4">
            <h3 className="font-medium">Lost a key?</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              A post you cannot prove ownership of has an “Ask a moderator”
              action on its card. Include the exact wording, approximate date
              and anything only the author would know.
            </p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
