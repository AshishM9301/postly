"use client";

import { useQuery } from "@tanstack/react-query";
import { MapPin, UserRound } from "lucide-react";

import { BlurhashImage } from "~/components/blurhash-image";
import { CategoryIcon } from "~/components/category-icon";
import { PostComments } from "~/components/post-comments";
import { StatusBadge } from "~/components/status-badge";
import { Avatar, AvatarFallback } from "~/components/ui/avatar";
import { Badge } from "~/components/ui/badge";
import { Card, CardContent, CardHeader } from "~/components/ui/card";
import { getSignedMediaUrl, type FeedPost } from "~/lib/api/endpoints";
import { timeAgo } from "~/lib/time";
import { VoteButtons } from "~/components/vote-buttons";

export function PostCard({ post }: { post: FeedPost }) {
  const media = post.media[0] ?? null;
  const signed = useQuery({
    queryKey: ["media", media?.id],
    queryFn: () => getSignedMediaUrl(media?.id ?? ""),
    enabled: media !== null,
    staleTime: 4 * 60 * 1000,
    retry: 1,
  });

  return (
    <Card className="gap-0 overflow-hidden py-0 ring-foreground/10">
      <CardHeader className="gap-2 px-4 pt-4 pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2">
            <Avatar size="sm">
              <AvatarFallback className="bg-primary/10 text-primary">
                <UserRound className="size-3.5" />
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0 leading-tight">
              <p className="truncate text-sm font-medium">{post.alias}</p>
              <p className="truncate text-xs text-muted-foreground">
                {post.area.name} · {post.area.district} · {timeAgo(post.created_at)}
              </p>
            </div>
          </div>
          <StatusBadge status={post.status} />
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge variant="secondary" className="gap-1">
            <CategoryIcon slug={post.category.slug} className="size-3" />
            {post.category.name}
          </Badge>
          <Badge variant="outline" className="gap-1 text-muted-foreground">
            <MapPin className="size-3" />
            {post.area.pincode}
          </Badge>
          {typeof post.distance_meters === "number" ? (
            <Badge variant="outline" className="text-muted-foreground">
              {formatDistance(post.distance_meters)}
            </Badge>
          ) : null}
        </div>
      </CardHeader>

      <CardContent className="space-y-3 px-4 pb-3">
        <div className="space-y-1">
          <h2 className="text-base leading-snug font-semibold">{post.title}</h2>
          <p className="text-sm whitespace-pre-wrap text-foreground/85">{post.body}</p>
        </div>

        {media?.kind === "IMAGE" ? (
          <BlurhashImage
            src={signed.data?.url ?? null}
            blurHash={media.blur_hash}
            alt={post.title}
            className="aspect-[4/3] w-full rounded-lg"
          />
        ) : null}

        {media?.kind === "VIDEO" && signed.data?.url ? (
          <video
            controls
            preload="metadata"
            src={signed.data.url}
            className="w-full rounded-lg bg-black"
          />
        ) : null}
      </CardContent>

      <div className="flex items-center justify-between gap-2 border-t px-4 py-2.5">
        <VoteButtons
          targetId={post.id}
          initialUpvotes={post.upvote_count}
          initialDownvotes={post.downvote_count}
        />
        <PostComments post={post} />
      </div>
    </Card>
  );
}

function formatDistance(meters: number): string {
  if (meters < 1000) {
    return `${meters} m away`;
  }
  return `${(meters / 1000).toFixed(1)} km away`;
}
