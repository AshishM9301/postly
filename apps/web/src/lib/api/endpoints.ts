import { api } from "./client";
import type { components } from "./types";

export type AreaOut = components["schemas"]["AreaOut"];
export type AreaDetection = components["schemas"]["AreaDetection"];
export type CategoryOut = components["schemas"]["CategoryOut"];
export type FeedPost = components["schemas"]["FeedPost"];
export type FeedPage = components["schemas"]["FeedPage"];
export type MediaUploadOut = components["schemas"]["MediaUploadOut"];
export type ModerationState = components["schemas"]["ModerationState"];
export type PostCreate = components["schemas"]["PostCreate"];
export type PostOut = components["schemas"]["PostOut"];
export type PostStatus = components["schemas"]["PostStatus"];
export type SignedUrlOut = components["schemas"]["SignedUrlOut"];
export type VoteOut = components["schemas"]["VoteOut"];

export type FeedTabName = "for-you" | "trending" | "new" | "nearby";

export type FeedQuery = {
  areaId?: string;
  categoryId?: string;
  limit?: number;
  cursor?: string | null;
};

export type NearbyQuery = FeedQuery & {
  lat: number;
  lng: number;
  radiusM?: number;
};

function queryParams(query: FeedQuery): Record<string, string | number | undefined> {
  return {
    area_id: query.areaId,
    category_id: query.categoryId,
    limit: query.limit,
    cursor: query.cursor ?? undefined,
  };
}

export async function getFeed(tab: FeedTabName, query: FeedQuery = {}): Promise<FeedPage> {
  const envelope = await api.requestEnvelope<FeedPost[]>(`/feed/${tab}`, {
    query: queryParams(query),
  });

  const meta = envelope.meta ?? {};
  return {
    data: envelope.data,
    meta: {
      cursor: typeof meta.cursor === "string" ? meta.cursor : null,
      has_more: Boolean(meta.has_more),
    },
  };
}

export async function getNearbyFeed(query: NearbyQuery): Promise<FeedPage> {
  const envelope = await api.requestEnvelope<FeedPost[]>("/feed/nearby", {
    query: {
      ...queryParams(query),
      lat: query.lat,
      lng: query.lng,
      radius_m: query.radiusM,
    },
  });

  const meta = envelope.meta ?? {};
  return {
    data: envelope.data,
    meta: {
      cursor: typeof meta.cursor === "string" ? meta.cursor : null,
      has_more: Boolean(meta.has_more),
    },
  };
}

export async function getCategories(): Promise<CategoryOut[]> {
  return api.request<CategoryOut[]>("/categories");
}

export async function searchAreas(q: string, limit = 8): Promise<AreaOut[]> {
  return api.request<AreaOut[]>("/areas/search", { query: { q, limit } });
}

export async function detectArea(lat: number, lng: number): Promise<AreaDetection> {
  return api.request<AreaDetection>("/areas/detect", { query: { lat, lng } });
}

export async function createPost(body: PostCreate): Promise<PostOut> {
  return api.request<PostOut>("/posts", { method: "POST", body });
}

export async function uploadMedia(
  file: File,
  postId: string,
  ownerKey: string,
): Promise<MediaUploadOut> {
  const form = new FormData();
  form.set("file", file);
  form.set("post_id", postId);
  form.set("owner_key", ownerKey);
  return api.request<MediaUploadOut>("/media", { method: "POST", body: form });
}

export async function getSignedMediaUrl(mediaId: string): Promise<SignedUrlOut> {
  return api.request<SignedUrlOut>(`/media/${mediaId}/signed`);
}

export async function castVote(
  targetType: "POST" | "COMMENT",
  targetId: string,
  value: 1 | -1,
  voterKey?: string | null,
): Promise<VoteOut> {
  return api.request<VoteOut>(`/votes/${targetType}/${targetId}`, {
    method: "PUT",
    body: { value, voter_key: voterKey ?? null },
  });
}

export async function removeVote(
  targetType: "POST" | "COMMENT",
  targetId: string,
  voterKey?: string | null,
): Promise<VoteOut> {
  return api.request<VoteOut>(`/votes/${targetType}/${targetId}`, {
    method: "DELETE",
    body: { voter_key: voterKey ?? null },
  });
}
