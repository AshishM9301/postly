import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import { describe, it } from "node:test";

import {
  deriveOwnerKey,
  fromBase64Url,
  generateSecret,
  SECRET_BYTES,
  toBase64Url,
} from "../crypto.ts";

const FIXED_SECRET = Uint8Array.from(
  { length: SECRET_BYTES },
  (_, index) => index,
);
const FIXED_TARGET = "post-123";
// Independently produced by node:crypto:
// createHmac("sha256", Buffer.from([0..31])).update("post-123").digest("base64url")
const FIXED_OWNER_KEY = "BaCamp9SDkGtI1yYKz_76ElI3Kq2QXghpcnxz0UACEI";

function nodeOwnerKey(secret: Uint8Array, targetId: string): string {
  return createHmac("sha256", secret).update(targetId).digest("base64url");
}

describe("ghost crypto", () => {
  it("matches the recorded node:crypto test vector", async () => {
    assert.equal(
      await deriveOwnerKey(FIXED_SECRET, FIXED_TARGET),
      FIXED_OWNER_KEY,
    );
    assert.equal(nodeOwnerKey(FIXED_SECRET, FIXED_TARGET), FIXED_OWNER_KEY);
  });

  it("is deterministic and agrees with node:crypto for arbitrary ids", async () => {
    const secret = generateSecret();
    const targetId = crypto.randomUUID();

    const first = await deriveOwnerKey(secret, targetId);
    const second = await deriveOwnerKey(secret, targetId);

    assert.equal(first, second);
    assert.equal(first, nodeOwnerKey(secret, targetId));
  });

  it("produces different keys for different target ids", async () => {
    const secret = generateSecret();

    const first = await deriveOwnerKey(secret, "post-a");
    const second = await deriveOwnerKey(secret, "post-b");

    assert.notEqual(first, second);
  });

  it("generates 32 random bytes with the platform CSPRNG", () => {
    const first = generateSecret();
    const second = generateSecret();

    assert.equal(first.length, SECRET_BYTES);
    assert.equal(first.length, 32);
    assert.notDeepEqual(first, second);
    assert.notDeepEqual(first, new Uint8Array(SECRET_BYTES));
  });

  it("round-trips base64url and never emits +, / or =", () => {
    for (let length = 0; length <= 64; length += 1) {
      const bytes = crypto.getRandomValues(new Uint8Array(length));
      const encoded = toBase64Url(bytes);

      assert.doesNotMatch(encoded, /[+/=]/);
      assert.deepEqual(fromBase64Url(encoded), bytes);
    }
  });

  it("rejects values that are not base64url", () => {
    assert.throws(() => fromBase64Url("not base64!"));
  });
});
