"use client";

import { useMutation } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "~/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "~/components/ui/dialog";
import { Label } from "~/components/ui/label";
import { Textarea } from "~/components/ui/textarea";
import { requestRemoval } from "~/lib/api/endpoints";
import { describeApiError } from "~/lib/api-error";

export function RemovalRequestDialog({
  postId,
  postTitle,
  open,
  onOpenChange,
}: {
  postId: string;
  postTitle: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [details, setDetails] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setDetails("");
      setError(null);
    }
  }, [open]);

  const mutation = useMutation({
    mutationFn: () => requestRemoval(postId, details.trim()),
    onSuccess: () => {
      toast.success("Removal request sent to the moderators");
      onOpenChange(false);
    },
    onError: (mutationError) => {
      setError(describeApiError(mutationError));
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Ask a moderator to remove this post</DialogTitle>
          <DialogDescription>
            Use this when you no longer have the ghost key for “{postTitle}”.
            A human checks the details before removing anything.
          </DialogDescription>
        </DialogHeader>

        <form
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            setError(null);
            if (!details.trim()) {
              setError("Describe the post so a moderator can verify it.");
              return;
            }
            mutation.mutate();
          }}
        >
          <div className="space-y-1.5">
            <Label htmlFor="removal-details">What did you post?</Label>
            <Textarea
              id="removal-details"
              value={details}
              onChange={(event) => setDetails(event.target.value)}
              placeholder="Exact title/body, approximate date and time, and the photo description."
              rows={5}
              maxLength={2000}
              disabled={mutation.isPending}
              required
            />
            <p className="text-xs text-muted-foreground">
              Do not include your account secret or any other password.
            </p>
          </div>

          {error ? (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          ) : null}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              disabled={mutation.isPending}
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={mutation.isPending || details.trim().length === 0}
            >
              {mutation.isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : null}
              {mutation.isPending ? "Sending…" : "Send request"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
