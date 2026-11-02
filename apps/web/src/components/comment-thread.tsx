"use client";

import { useInfiniteQuery } from "@tanstack/react-query";
import { Loader2, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { CommentForm } from "~/components/comment-form";
import { CommentItem, type CommentNode } from "~/components/comment-item";
import { useSession } from "~/components/session-provider";
import { Button } from "~/components/ui/button";
import { Skeleton } from "~/components/ui/skeleton";
import { getComments, type CommentOut } from "~/lib/api/endpoints";
import { listOwnCommentIds } from "~/lib/ghost";

function buildTree(comments: CommentOut[]): CommentNode[] {
  const nodes = new Map<string, CommentNode>();
  for (const comment of comments) {
    nodes.set(comment.id, { ...comment, replies: [] });
  }

  const roots: CommentNode[] = [];
  for (const comment of comments) {
    const node = nodes.get(comment.id);
    if (!node) {
      continue;
    }
    const parent = comment.parent_id ? nodes.get(comment.parent_id) : undefined;
    if (parent) {
      parent.replies.push(node);
    } else {
      roots.push(node);
    }
  }
  return roots;
}

export function CommentThread({ postId }: { postId: string }) {
  const [ownCommentIds, setOwnCommentIds] = useState<Set<string>>(new Set());
  const { session } = useSession();

  const refreshOwnCommentIds = useCallback(() => {
    void listOwnCommentIds()
      .then((ids) => setOwnCommentIds(new Set(ids)))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    let active = true;
    void listOwnCommentIds()
      .then((ids) => {
        if (active) {
          setOwnCommentIds(new Set(ids));
        }
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

  const query = useInfiniteQuery({
    queryKey: ["comments", postId],
    initialPageParam: null as string | null,
    queryFn: ({ pageParam }) =>
      getComments(postId, { limit: 50, cursor: pageParam }),
    getNextPageParam: (lastPage) =>
      lastPage.meta.has_more ? lastPage.meta.cursor : undefined,
  });

  const comments = useMemo(() => {
    const seen = new Set<string>();
    const flat: CommentOut[] = [];
    for (const page of query.data?.pages ?? []) {
      for (const comment of page.data) {
        if (!seen.has(comment.id)) {
          seen.add(comment.id);
          flat.push(comment);
        }
      }
    }
    return flat;
  }, [query.data]);

  const tree = useMemo(() => buildTree(comments), [comments]);

  return (
    <div className="space-y-4">
      <CommentForm postId={postId} onPosted={refreshOwnCommentIds} />

      <div className="border-t pt-4">
        {query.isPending ? (
          <div className="space-y-3" aria-label="Loading comments">
            {[0, 1, 2].map((index) => (
              <Skeleton key={index} className="h-20 w-full rounded-lg" />
            ))}
          </div>
        ) : query.isError ? (
          <div className="flex flex-col items-start gap-2">
            <p className="text-sm text-muted-foreground">
              {query.error instanceof Error
                ? query.error.message
                : "Could not load the comments."}
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void query.refetch()}
            >
              <RefreshCw className="size-4" />
              Try again
            </Button>
          </div>
        ) : tree.length === 0 ? (
          <p className="py-4 text-center text-sm text-muted-foreground">
            No comments yet. Start the discussion.
          </p>
        ) : (
          <div className="space-y-5">
            {tree.map((comment) => (
              <CommentItem
                key={comment.id}
                postId={postId}
                comment={comment}
                ownCommentIds={ownCommentIds}
                sessionUserId={session?.userId ?? null}
                onOwnCommentChanged={refreshOwnCommentIds}
              />
            ))}

            {query.hasNextPage ? (
              <Button
                type="button"
                variant="outline"
                className="w-full"
                disabled={query.isFetchingNextPage}
                onClick={() => void query.fetchNextPage()}
              >
                {query.isFetchingNextPage ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    Loading
                  </>
                ) : (
                  "Load more comments"
                )}
              </Button>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
