"use client";

import { useInfiniteQuery } from "@tanstack/react-query";
import { Loader2, RefreshCw } from "lucide-react";

import { PostCard } from "~/components/post-card";
import { Button } from "~/components/ui/button";
import { Card, CardContent } from "~/components/ui/card";
import { Skeleton } from "~/components/ui/skeleton";
import {
  getFeed,
  getNearbyFeed,
  type FeedTabName,
} from "~/lib/api/endpoints";
import type { Coordinates } from "~/lib/geo";

export function FeedList({
  tab,
  areaId,
  categoryId,
  coords,
}: {
  tab: FeedTabName;
  areaId?: string;
  categoryId?: string;
  coords?: Coordinates | null;
}) {
  const enabled = tab !== "nearby" || coords !== null;

  const query = useInfiniteQuery({
    queryKey: ["feed", tab, areaId, categoryId, coords?.lat, coords?.lng],
    initialPageParam: null as string | null,
    enabled,
    queryFn: ({ pageParam }) => {
      if (tab === "nearby" && coords) {
        return getNearbyFeed({
          lat: coords.lat,
          lng: coords.lng,
          areaId,
          categoryId,
          cursor: pageParam,
          limit: 10,
        });
      }
      return getFeed(tab, {
        areaId,
        categoryId,
        cursor: pageParam,
        limit: 10,
      });
    },
    getNextPageParam: (lastPage) =>
      lastPage.meta.has_more ? lastPage.meta.cursor : undefined,
  });

  if (!enabled) {
    return (
      <FeedMessage
        title="Location needed"
        body="Allow location access to see problems near you, or use the other tabs."
      />
    );
  }

  if (query.isPending) {
    return (
      <div className="space-y-3" aria-label="Loading posts">
        {[0, 1, 2].map((index) => (
          <Skeleton key={index} className="h-56 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  if (query.isError) {
    return (
      <Card>
        <CardContent className="flex flex-col items-start gap-3 p-4">
          <div>
            <p className="font-medium">Could not load the feed</p>
            <p className="text-sm text-muted-foreground">
              {query.error instanceof Error
                ? query.error.message
                : "Check that the API is running."}
            </p>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => void query.refetch()}
          >
            <RefreshCw className="size-4" />
            Try again
          </Button>
        </CardContent>
      </Card>
    );
  }

  const seen = new Set<string>();
  const posts = query.data.pages
    .flatMap((page) => page.data)
    .filter((post) => {
      if (seen.has(post.id)) {
        return false;
      }
      seen.add(post.id);
      return true;
    });

  if (posts.length === 0) {
    return (
      <FeedMessage
        title="Nothing here yet"
        body="Be the first to report a problem in your area."
      />
    );
  }

  return (
    <div className="space-y-3">
      {posts.map((post) => (
        <PostCard key={post.id} post={post} />
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
            "Load more"
          )}
        </Button>
      ) : null}
    </div>
  );
}

function FeedMessage({ title, body }: { title: string; body: string }) {
  return (
    <Card>
      <CardContent className="flex flex-col items-start gap-1 p-6">
        <p className="font-medium">{title}</p>
        <p className="text-sm text-muted-foreground">{body}</p>
      </CardContent>
    </Card>
  );
}
