"use client";

/**
 * The bearer-token session store.
 *
 * Only the opaque server token lives here; the pseudonymous **secret** is an
 * account credential and must stay in the vault (T-025 wires the sign-in).
 */

export type SessionMode = "google" | "pseudonymous";

const TOKEN_KEY = "postly.session.token";
const ALIAS_KEY = "postly.session.alias";
const MODE_KEY = "postly.session.mode";

function store(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function read(key: string): string | null {
  return store()?.getItem(key) ?? null;
}

function write(key: string, value: string | null): void {
  const storage = store();
  if (!storage) {
    return;
  }
  if (value === null) {
    storage.removeItem(key);
  } else {
    storage.setItem(key, value);
  }
}

export function getSessionToken(): string | null {
  return read(TOKEN_KEY);
}

export function setSessionToken(token: string | null): void {
  write(TOKEN_KEY, token);
}

export function getSessionAlias(): string | null {
  return read(ALIAS_KEY);
}

export function setSessionAlias(alias: string | null): void {
  write(ALIAS_KEY, alias);
}

export function getSessionMode(): SessionMode | null {
  const mode = read(MODE_KEY);
  return mode === "google" || mode === "pseudonymous" ? mode : null;
}

export function setSessionMode(mode: SessionMode | null): void {
  write(MODE_KEY, mode);
}

export function clearSession(): void {
  const storage = store();
  if (!storage) {
    return;
  }
  storage.removeItem(TOKEN_KEY);
  storage.removeItem(ALIAS_KEY);
  storage.removeItem(MODE_KEY);
}
