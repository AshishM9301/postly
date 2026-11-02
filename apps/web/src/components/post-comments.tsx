"use client";

import { MessageCircle } from "lucide-react";
import { useState } from "react";

import { CommentThread } from "~/components/comment-thread";
import { Button } from "~/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "~/components/ui/dialog";
import type { FeedPost } from "~/lib/api/endpoints";

export function PostComments({ post }: { post: FeedPost }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="gap-1.5 text-muted-foreground"
        aria-label={`Open comments (${post.comment_count})`}
        onClick={() => setOpen(true)}
      >
        <MessageCircle className="size-4" aria-hidden="true" />
        <span className="tabular-nums">{post.comment_count}</span>
        <span className="sr-only">comments</span>
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Comments</DialogTitle>
            <DialogDescription className="line-clamp-2">
              {post.title}
            </DialogDescription>
          </DialogHeader>
          {open ? <CommentThread postId={post.id} /> : null}
        </DialogContent>
      </Dialog>
    </>
  );
}
