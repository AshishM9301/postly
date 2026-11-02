"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useId, useState, type FormEvent } from "react";

import { Button } from "~/components/ui/button";
import { Textarea } from "~/components/ui/textarea";
import { createComment, type CommentOut } from "~/lib/api/endpoints";
import { deleteCommentKey } from "~/lib/ghost";
import { createGhostCommentIdentity } from "~/lib/identity";
import { getSessionToken } from "~/lib/session";

export function CommentForm({
  postId,
  parentId = null,
  compact = false,
  onPosted,
  onCancel,
}: {
  postId: string;
  parentId?: string | null;
  compact?: boolean;
  onPosted?: (comment: CommentOut) => void;
  onCancel?: () => void;
}) {
  const inputId = useId();
  const queryClient = useQueryClient();
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async () => {
      const commentId = crypto.randomUUID();

      if (getSessionToken() !== null) {
        return createComment(postId, {
          id: commentId,
          body: body.trim(),
          parent_id: parentId,
        });
      }

      const identity = await createGhostCommentIdentity(commentId);
      try {
        return await createComment(postId, {
          id: commentId,
          body: body.trim(),
          parent_id: parentId,
          alias: identity.alias,
          owner_key: identity.ownerKey,
        });
      } catch (error) {
        await deleteCommentKey(commentId).catch(() => undefined);
        throw error;
      }
    },
    onSuccess: async (comment) => {
      setBody("");
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["comments", postId] });
      await queryClient.invalidateQueries({ queryKey: ["feed"] });
      onPosted?.(comment);
    },
    onError: (mutationError) => {
      setError(
        mutationError instanceof Error
          ? mutationError.message
          : "Could not post the comment.",
      );
    },
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!body.trim()) {
      setError("Write something first.");
      return;
    }
    mutation.mutate();
  }

  return (
    <form className="space-y-2" onSubmit={submit}>
      <label htmlFor={inputId} className="sr-only">
        {parentId ? "Reply to this comment" : "Write a comment"}
      </label>
      <Textarea
        id={inputId}
        value={body}
        onChange={(event) => setBody(event.target.value)}
        placeholder={
          parentId
            ? "Reply to this comment…"
            : "What do you think? Add context or a correction."
        }
        rows={compact ? 2 : 3}
        maxLength={5000}
        disabled={mutation.isPending}
      />
      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
      <div className="flex justify-end gap-2">
        {onCancel ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={mutation.isPending}
            onClick={onCancel}
          >
            Cancel
          </Button>
        ) : null}
        <Button
          type="submit"
          size="sm"
          disabled={mutation.isPending || body.trim().length === 0}
        >
          {mutation.isPending ? "Posting…" : parentId ? "Reply" : "Post comment"}
        </Button>
      </div>
    </form>
  );
}
