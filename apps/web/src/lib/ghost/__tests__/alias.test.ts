import assert from "node:assert/strict";
import { beforeEach, describe, it } from "node:test";

import {
  ALIAS_ALPHABET,
  ALIAS_LENGTH,
  ALIAS_PREFIX,
  ALIAS_UNBIASED_LIMIT,
  clearSessionAlias,
  ensureSessionAlias,
  generateAlias,
  getSessionAlias,
  rotateAlias,
  setSessionAlias,
} from "../alias.ts";

class MemoryStorage {
  private readonly data = new Map<string, string>();

  get length(): number {
    return this.data.size;
  }

  clear(): void {
    this.data.clear();
  }

  getItem(key: string): string | null {
    return this.data.get(key) ?? null;
  }

  key(index: number): string | null {
    return Array.from(this.data.keys())[index] ?? null;
  }

  removeItem(key: string): void {
    this.data.delete(key);
  }

  setItem(key: string, value: string): void {
    this.data.set(key, value);
  }
}

const storage = new MemoryStorage();
Object.defineProperty(globalThis, "sessionStorage", {
  value: storage,
  configurable: true,
  writable: true,
});

describe("ghost aliases", () => {
  beforeEach(() => {
    storage.clear();
  });

  it("generates readable aliases from the non-ambiguous alphabet", () => {
    for (let index = 0; index < 50; index += 1) {
      const alias = generateAlias();
      assert.ok(alias.startsWith(ALIAS_PREFIX));
      assert.equal(alias.length, ALIAS_PREFIX.length + ALIAS_LENGTH);
      for (const character of alias.slice(ALIAS_PREFIX.length)) {
        assert.ok(ALIAS_ALPHABET.includes(character));
      }
    }
  });

  it("rejects biased bytes so every alias character is equally likely", () => {
    assert.equal(ALIAS_ALPHABET.length, 31);
    assert.equal(ALIAS_UNBIASED_LIMIT, 248);
    assert.ok(ALIAS_UNBIASED_LIMIT % ALIAS_ALPHABET.length === 0);
  });

  it("creates and persists an alias for the session", () => {
    const alias = ensureSessionAlias();

    assert.equal(getSessionAlias(), alias);
    assert.equal(ensureSessionAlias(), alias);
  });

  it("rotates the alias and stores the new one", () => {
    const previous = ensureSessionAlias();
    const rotated = rotateAlias();

    assert.notEqual(rotated, previous);
    assert.equal(getSessionAlias(), rotated);
    assert.ok(rotated.startsWith(ALIAS_PREFIX));
  });

  it("clears the alias", () => {
    setSessionAlias("Neighbor_test");
    clearSessionAlias();

    assert.equal(getSessionAlias(), null);
  });
});
