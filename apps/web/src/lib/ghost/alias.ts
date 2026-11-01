/**
 * Ghost aliases.
 *
 * An alias is a human-readable, non-identifying label (`Neighbor_7f3a`). It is
 * stored per browser session; rotating it changes the label for *new* content,
 * while older posts keep the alias snapshot the server stored with them.
 */

export const ALIAS_PREFIX = "Neighbor_";
export const ALIAS_LENGTH = 4;

/** No 0/o, 1/i/l — an alias should survive being read aloud. */
export const ALIAS_ALPHABET = "23456789abcdefghjkmnpqrstuvwxyz";

const STORAGE_KEY = "postly.ghost.alias";

/**
 * Largest multiple of the alphabet size that fits in a byte. Bytes at or above
 * this are rejected so every alias character is equally likely (no modulo bias:
 * `256 % 31 = 8`, so accepting the whole byte range would favour the first 8).
 */
export const ALIAS_UNBIASED_LIMIT =
  Math.floor(256 / ALIAS_ALPHABET.length) * ALIAS_ALPHABET.length;

export function generateAlias(): string {
  let suffix = "";
  while (suffix.length < ALIAS_LENGTH) {
    const bytes = crypto.getRandomValues(
      new Uint8Array(ALIAS_LENGTH - suffix.length),
    );
    for (const byte of bytes) {
      if (byte >= ALIAS_UNBIASED_LIMIT) {
        continue;
      }
      suffix += ALIAS_ALPHABET.charAt(byte % ALIAS_ALPHABET.length);
    }
  }
  return `${ALIAS_PREFIX}${suffix}`;
}

function aliasStorage(): Storage | null {
  try {
    return typeof sessionStorage === "undefined" ? null : sessionStorage;
  } catch {
    return null;
  }
}

export function getSessionAlias(): string | null {
  const storage = aliasStorage();
  if (storage === null) {
    return null;
  }
  const value = storage.getItem(STORAGE_KEY);
  return value?.startsWith(ALIAS_PREFIX) ? value : null;
}

export function setSessionAlias(alias: string): void {
  aliasStorage()?.setItem(STORAGE_KEY, alias);
}

/** Return the current alias, creating and persisting one if needed. */
export function ensureSessionAlias(): string {
  const current = getSessionAlias();
  if (current !== null) {
    return current;
  }
  const alias = generateAlias();
  setSessionAlias(alias);
  return alias;
}

/**
 * Create a fresh alias for this session. The previous alias is not rewritten
 * into older posts — those snapshots are immutable on the server.
 */
export function rotateAlias(): string {
  const alias = generateAlias();
  setSessionAlias(alias);
  return alias;
}

export function clearSessionAlias(): void {
  aliasStorage()?.removeItem(STORAGE_KEY);
}
