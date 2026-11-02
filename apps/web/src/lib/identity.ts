"use client";

import {
  deriveOwnerKey,
  ensureSessionAlias,
  generateSecret,
  getCommentKey,
  getPostKey,
  getSessionKey,
  rotateAlias,
  saveCommentKey,
  savePostKey,
  saveSessionKey,
} from "~/lib/ghost";

export type GhostIdentity = {
  sessionKey: Uint8Array;
  alias: string;
};

export type GhostPostIdentity = {
  alias: string;
  ownerKey: string;
};

export type GhostCommentIdentity = {
  alias: string;
  ownerKey: string;
};

export function isBrowser(): boolean {
  return typeof window !== "undefined";
}

/** Reuse the local session key, creating one on first use. */
export async function ensureGhostIdentity(): Promise<GhostIdentity> {
  let sessionKey = await getSessionKey();
  if (sessionKey === null) {
    sessionKey = generateSecret();
    await saveSessionKey(sessionKey);
  }
  return { sessionKey, alias: ensureSessionAlias() };
}

/**
 * Save a fresh per-post key and derive the owner key the server stores.
 * Called once, right before creating the post.
 */
export async function createGhostPostIdentity(postId: string): Promise<GhostPostIdentity> {
  const { alias } = await ensureGhostIdentity();
  const postKey = generateSecret();
  await savePostKey(postId, postKey, alias);
  return { alias, ownerKey: await deriveOwnerKey(postKey, postId) };
}

/** Recompute the owner key for an existing post (media upload, edits, delete). */
export async function ownerKeyForPost(postId: string): Promise<string | null> {
  const postKey = await getPostKey(postId);
  if (postKey === null) {
    return null;
  }
  return deriveOwnerKey(postKey, postId);
}

/** Save a fresh per-comment key and derive the owner key for this comment id. */
export async function createGhostCommentIdentity(
  commentId: string,
): Promise<GhostCommentIdentity> {
  const { alias } = await ensureGhostIdentity();
  const commentKey = generateSecret();
  await saveCommentKey(commentId, commentKey, alias);
  return { alias, ownerKey: await deriveOwnerKey(commentKey, commentId) };
}

/** Recompute the owner key for an existing comment (delete/edit). */
export async function ownerKeyForComment(
  commentId: string,
): Promise<string | null> {
  const commentKey = await getCommentKey(commentId);
  if (commentKey === null) {
    return null;
  }
  return deriveOwnerKey(commentKey, commentId);
}

/** Ghost votes are keyed per target: `a:HMAC(sessionKey, targetId)`. */
export async function voterKeyFor(targetId: string): Promise<string> {
  const { sessionKey } = await ensureGhostIdentity();
  return `a:${await deriveOwnerKey(sessionKey, targetId)}`;
}

/** New alias for new content; older posts keep their snapshot. */
export function rotateGhostAlias(): string {
  return rotateAlias();
}

export function currentGhostAlias(): string {
  return ensureSessionAlias();
}
