"use client";

import { useQuery, useQueryClient, type InfiniteData } from "@tanstack/react-query";
import { Flag, Loader2, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { RemovalRequestDialog } from "~/components/removal-request-dialog";
import { Button } from "~/components/ui/button";
import {
  deletePostById,
  getMe,
  type FeedPage,
} from "~/lib/api/endpoints";
import { describeApiError } from "~/lib/api-error";
import { ghostTransport } from "~/lib/api/ghost";
import { deleteOwnPost, listOwnPosts } from "~/lib/ghost";
import { getSessionToken } from "~/lib/session";
import { setMyVote } from "~/lib/votes-store";

export function PostActions({ post }: { post: FeedPage["data"][number] }) {
  const queryClient = useQueryClient();
  const [removalOpen, setRemovalOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const token = getSessionToken();

  const ownPosts = useQuery({
    queryKey: ["own-post-ids"],
    queryFn: listOwnPosts,
    staleTime: Infinity,
  });

  const me = useQuery({
    queryKey: ["me", token],
    queryFn: getMe,
    enabled: token !== null,
    retry: false,
    staleTime: 60_000,
  });

  const ghostOwned = ownPosts.data?.includes(post.id) ?? false;
  const sessionOwned =
    token !== null &&
    post.author !== null &&
    me.data?.user_id !== null &&
    me.data?.user_id === post.author.id;

  async function dropFromLocalState() {
    setMyVote(post.id, null);
    queryClient.setQueriesData<InfiniteData<FeedPage>>(
      { queryKey: ["feed"] },
      (data) =>
        data
          ? {
              ...data,
              pages: data.pages.map((page) => ({
                ...page,
                data: page.data.filter((row) => row.id !== post.id),
              })),
            }
          : data,
    );
    queryClient.removeQueries({ queryKey: ["comments", post.id] });
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["feed"] }),
      queryClient.invalidateQueries({ queryKey: ["own-post-ids"] }),
    ]);
  }

  async function remove() {
    if (
      !window.confirm(
        "Delete this post permanently? Its photos, comments and votes are removed too. This cannot be undone.",
      )
    ) {
      return;
    }

    setDeleting(true);
    try {
      if (ghostOwned) {
        await deleteOwnPost(post.id, { transport: ghostTransport });
      } else {
        await deletePostById(post.id);
      }
      await dropFromLocalState();
      toast.success("Post deleted");
    } catch (error) {
      toast.error(describeApiError(error));
    } finally {
      setDeleting(false);
    }
  }

  if (ownPosts.isPending || (token !== null && me.isPending)) {
    return <div className="size-7" aria-hidden="true" />;
  }

  if (!ghostOwned && !sessionOwned) {
    return (
      <>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          aria-label="Ask a moderator to remove this post"
          title="Ask a moderator to remove this post"
          onClick={() => setRemovalOpen(true)}
        >
          <Flag className="size-4" />
        </Button>
        <RemovalRequestDialog
          postId={post.id}
          postTitle={post.title}
          open={removalOpen}
          onOpenChange={setRemovalOpen}
        />
      </>
    );
  }

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon-sm"
      className="text-destructive hover:text-destructive"
      aria-label="Delete this post"
      title="Delete this post"
      disabled={deleting}
      onClick={() => void remove()}
    >
      {deleting ? (
        <Loader2 className="size-4 animate-spin" />
      ) : (
        <Trash2 className="size-4" />
      )}
    </Button>
  );
}
