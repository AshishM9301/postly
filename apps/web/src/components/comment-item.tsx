"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Reply, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { CommentForm } from "~/components/comment-form";
import { Button } from "~/components/ui/button";
import { VoteButtons } from "~/components/vote-buttons";
import { deleteComment, type CommentOut } from "~/lib/api/endpoints";
import { deleteCommentKey } from "~/lib/ghost";
import { ownerKeyForComment } from "~/lib/identity";
import { timeAgo } from "~/lib/time";

export type CommentNode = CommentOut & { replies: CommentNode[] };

export function CommentItem({
  postId,
  comment,
  ownCommentIds,
  sessionUserId,
  onOwnCommentChanged,
}: {
  postId: string;
  comment: CommentNode;
  ownCommentIds: Set<string>;
  sessionUserId: string | null;
  onOwnCommentChanged: () => void;
}) {
  const queryClient = useQueryClient();
  const [replyOpen, setReplyOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const vaultOwned = ownCommentIds.has(comment.id);
  const sessionOwned =
    sessionUserId !== null && comment.author?.id === sessionUserId;
  const isOwn = vaultOwned || sessionOwned;

  async function remove() {
    if (
      !window.confirm(
        "Delete this comment? Its replies will stay and move up a level.",
      )
    ) {
      return;
    }

    setDeleting(true);
    try {
      const ownerKey = vaultOwned
        ? await ownerKeyForComment(comment.id)
        : null;
      if (vaultOwned && ownerKey === null) {
        throw new Error("This device has no key for that comment anymore.");
      }
      await deleteComment(comment.id, ownerKey);
      if (vaultOwned) {
        await deleteCommentKey(comment.id);
      }
      await queryClient.invalidateQueries({ queryKey: ["comments", postId] });
      await queryClient.invalidateQueries({ queryKey: ["feed"] });
      onOwnCommentChanged();
      toast.success("Comment deleted; replies were kept");
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Could not delete the comment.",
      );
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div>
      <div className="space-y-1.5">
        <div className="flex items-baseline justify-between gap-2">
          <p className="truncate text-sm font-medium">{comment.alias}</p>
          <span className="shrink-0 text-xs text-muted-foreground">
            {timeAgo(comment.created_at)}
          </span>
        </div>
        <p className="text-sm whitespace-pre-wrap text-foreground/90">
          {comment.body}
        </p>
      </div>

      <div className="mt-2 flex items-center justify-between gap-2">
        <VoteButtons
          targetId={comment.id}
          targetType="COMMENT"
          initialUpvotes={comment.upvote_count}
          initialDownvotes={comment.downvote_count}
        />
        <div className="flex items-center gap-1">
          <Button
            type="button"
            variant="ghost"
            size="xs"
            className="gap-1 text-muted-foreground"
            aria-expanded={replyOpen}
            onClick={() => setReplyOpen((open) => !open)}
          >
            <Reply className="size-3.5" />
            Reply
          </Button>
          {isOwn ? (
            <Button
              type="button"
              variant="ghost"
              size="xs"
              className="gap-1 text-destructive hover:text-destructive"
              disabled={deleting}
              onClick={() => void remove()}
            >
              <Trash2 className="size-3.5" />
              {deleting ? "Deleting…" : "Delete"}
            </Button>
          ) : null}
        </div>
      </div>

      {replyOpen ? (
        <div className="mt-3">
          <CommentForm
            postId={postId}
            parentId={comment.id}
            compact
            onPosted={() => {
              setReplyOpen(false);
              onOwnCommentChanged();
            }}
            onCancel={() => setReplyOpen(false)}
          />
        </div>
      ) : null}

      {comment.replies.length > 0 ? (
        <div className="mt-3 space-y-4 border-l pl-3">
          {comment.replies.map((reply) => (
            <CommentItem
              key={reply.id}
              postId={postId}
              comment={reply}
              ownCommentIds={ownCommentIds}
              sessionUserId={sessionUserId}
              onOwnCommentChanged={onOwnCommentChanged}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}
