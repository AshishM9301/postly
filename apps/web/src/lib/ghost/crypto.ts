/**
 * Ghost cryptography. Framework-agnostic on purpose: plain TypeScript on top of
 * WebCrypto so the same algorithms can be copied into a Kotlin / Swift client.
 *
 * The browser is the only place the ghost secret exists. The network only ever
 * carries `HMAC-SHA256(secret, targetId)`, base64url encoded.
 */

/** A ghost secret is 32 random bytes (256 bits). */
export type GhostSecret = Uint8Array;

export const SECRET_BYTES = 32;

const BASE64URL_ALPHABET =
  "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";

/** RFC 4648 §5 base64url, no padding. */
export function toBase64Url(bytes: Uint8Array): string {
  let output = "";
  for (let index = 0; index < bytes.length; index += 3) {
    const first = bytes[index] ?? 0;
    const second = bytes[index + 1];
    const third = bytes[index + 2];

    const triple = (first << 16) | ((second ?? 0) << 8) | (third ?? 0);

    output += BASE64URL_ALPHABET.charAt((triple >>> 18) & 0x3f);
    output += BASE64URL_ALPHABET.charAt((triple >>> 12) & 0x3f);
    if (second !== undefined) {
      output += BASE64URL_ALPHABET.charAt((triple >>> 6) & 0x3f);
    }
    if (third !== undefined) {
      output += BASE64URL_ALPHABET.charAt(triple & 0x3f);
    }
  }
  return output;
}

/** Inverse of {@link toBase64Url}. */
export function fromBase64Url(value: string): Uint8Array {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  if (!/^[A-Za-z0-9+/]*={0,2}$/.test(normalized)) {
    throw new Error("Value is not valid base64url");
  }
  const padded = normalized.padEnd(
    normalized.length + ((4 - (normalized.length % 4)) % 4),
    "=",
  );
  const binary = atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

/**
 * Generate a secret with the platform CSPRNG. Never use `Math.random` here.
 */
export function generateSecret(): GhostSecret {
  return crypto.getRandomValues(new Uint8Array(SECRET_BYTES));
}

/**
 * `owner_key = HMAC-SHA256(secret, targetId)`, base64url.
 *
 * The secret is the HMAC **key**; the target id is the **message**. Reversing
 * those produces keys the server cannot verify.
 */
export async function deriveOwnerKey(
  secret: GhostSecret,
  targetId: string,
): Promise<string> {
  const keyBytes = new Uint8Array(secret.length);
  keyBytes.set(secret);
  const key = await crypto.subtle.importKey(
    "raw",
    keyBytes,
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(targetId),
  );
  return toBase64Url(new Uint8Array(signature));
}
