import "fake-indexeddb/auto";

import assert from "node:assert/strict";
import { beforeEach, describe, it } from "node:test";

import { deriveOwnerKey, generateSecret } from "../crypto.ts";
import {
  closeVault,
  countOwnPosts,
  deleteAccountSecret,
  deleteCommentKey,
  deleteOwnPost,
  exportVaultJson,
  getAccountSecret,
  getCommentKey,
  getPostKey,
  getSessionKey,
  GhostVaultError,
  importVault,
  listOwnCommentIds,
  listOwnPosts,
  resetVault,
  saveAccountSecret,
  saveCommentKey,
  savePostKey,
  saveSessionKey,
  type GhostVaultErrorCode,
} from "../vault.ts";
import { ApiClient } from "../../api/client.ts";
import { createGhostTransport } from "../../api/ghost.ts";

function isVaultError(code: GhostVaultErrorCode) {
  return (error: unknown): boolean =>
    error instanceof GhostVaultError && error.code === code;
}

describe("ghost key vault", () => {
  beforeEach(async () => {
    await resetVault();
  });

  it("persists keys across a new IndexedDB connection", async () => {
    const postSecret = generateSecret();
    const sessionSecret = generateSecret();

    await saveSessionKey(sessionSecret);
    await savePostKey("post-1", postSecret, "Neighbor_abcd");

    await closeVault();

    assert.deepEqual(await getSessionKey(), sessionSecret);
    assert.deepEqual(await getPostKey("post-1"), postSecret);
    assert.deepEqual(await listOwnPosts(), ["post-1"]);
    assert.equal(await countOwnPosts(), 1);
  });

  it("stores the pseudonymous account secret in the vault", async () => {
    const secret = "account-secret-" + "x".repeat(40);

    await saveAccountSecret(secret);

    assert.equal(await getAccountSecret(), secret);
    assert.deepEqual(await listOwnPosts(), []);
    assert.deepEqual(await listOwnCommentIds(), []);

    await deleteAccountSecret();

    assert.equal(await getAccountSecret(), null);
  });

  it("stores comment keys separately from post keys", async () => {
    const commentSecret = generateSecret();

    await saveCommentKey("comment-1", commentSecret, "Neighbor_cccc");

    assert.deepEqual(await getCommentKey("comment-1"), commentSecret);
    assert.deepEqual(await listOwnCommentIds(), ["comment-1"]);
    assert.deepEqual(await listOwnPosts(), []);
    assert.equal(await countOwnPosts(), 0);

    await deleteCommentKey("comment-1");

    assert.equal(await getCommentKey("comment-1"), null);
    assert.deepEqual(await listOwnCommentIds(), []);
  });

  it("exports to JSON and imports it back", async () => {
    const sessionSecret = generateSecret();
    const postSecret = generateSecret();
    await saveSessionKey(sessionSecret);
    await savePostKey("post-2", postSecret, "Neighbor_zzzz");

    const json = await exportVaultJson();
    const parsed = JSON.parse(json) as { version: number };
    assert.equal(parsed.version, 1);
    assert.match(json, /"sessionKey"/);

    await resetVault();
    assert.equal(await getSessionKey(), null);
    assert.deepEqual(await listOwnPosts(), []);

    await importVault(json);

    assert.deepEqual(await getSessionKey(), sessionSecret);
    assert.deepEqual(await getPostKey("post-2"), postSecret);
    assert.deepEqual(await listOwnPosts(), ["post-2"]);
  });

  it("rejects a malformed or unsupported export", async () => {
    await assert.rejects(
      () => importVault("{not json"),
      isVaultError("invalid_vault"),
    );
    await assert.rejects(
      () => importVault(JSON.stringify({ version: 2, posts: [] })),
      isVaultError("invalid_vault"),
    );
    await assert.rejects(
      () => importVault(JSON.stringify({ version: 1, posts: [{ id: 1 }] })),
      isVaultError("invalid_vault"),
    );
  });

  it("reports a missing secret instead of inventing one", async () => {
    assert.equal(await getPostKey("never-saved"), null);

    let called = false;
    await assert.rejects(
      () =>
        deleteOwnPost("never-saved", {
          transport: async () => {
            called = true;
          },
        }),
      isVaultError("missing_secret"),
    );
    assert.equal(called, false);
  });

  it("computes the owner key locally and deletes through the API", async () => {
    const secret = generateSecret();
    await savePostKey("post-42", secret, "Neighbor_abcd");
    const expectedOwnerKey = await deriveOwnerKey(secret, "post-42");

    const calls: Array<{ url: string; init: RequestInit }> = [];
    const fetchImpl = async (url: string, init: RequestInit) => {
      calls.push({ url, init });
      return new Response(null, { status: 204 });
    };
    const client = new ApiClient({ baseUrl: "/api/v1", fetchImpl });

    await deleteOwnPost("post-42", {
      transport: createGhostTransport(client),
    });

    assert.equal(calls.length, 1);
    const call = calls[0];
    assert.ok(call);
    assert.equal(call.url, "/api/v1/posts/post-42");
    assert.equal(call.init.method, "DELETE");
    const rawBody = call.init.body;
    assert.equal(typeof rawBody, "string");
    if (typeof rawBody !== "string") {
      throw new Error("expected a JSON string body");
    }
    const body = JSON.parse(rawBody) as { owner_key: string };
    assert.equal(body.owner_key, expectedOwnerKey);

    assert.equal(await getPostKey("post-42"), null);
    assert.deepEqual(await listOwnPosts(), []);
  });

  it("keeps the secret when the delete call fails", async () => {
    const secret = generateSecret();
    await savePostKey("post-9", secret);

    const client = new ApiClient({
      baseUrl: "/api/v1",
      fetchImpl: async () => new Response("nope", { status: 500 }),
    });

    await assert.rejects(
      () =>
        deleteOwnPost("post-9", {
          transport: createGhostTransport(client),
        }),
      isVaultError("delete_failed"),
    );

    assert.deepEqual(await getPostKey("post-9"), secret);
    assert.deepEqual(await listOwnPosts(), ["post-9"]);
  });
});
