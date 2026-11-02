"use client";

import {
  deriveOwnerKey,
  ensureSessionAlias,
  generateSecret,
  getPostKey,
  getSessionKey,
  rotateAlias,
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
