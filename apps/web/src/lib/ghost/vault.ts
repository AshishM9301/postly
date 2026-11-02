/**
 * The local ghost key vault.
 *
 * Secrets live in IndexedDB on this device. IndexedDB is same-origin storage,
 * not encryption: the real protection is that **the server never receives the
 * secret**. Clearing site data or losing this browser loses the ability to
 * delete the corresponding ghost posts.
 */

import {
  deriveOwnerKey,
  fromBase64Url,
  toBase64Url,
  type GhostSecret,
} from "./crypto.ts";

const DB_NAME = "postly-ghost";
const DB_VERSION = 1;
const STORE_NAME = "keys";
const SESSION_ID = "session";
const POST_PREFIX = "post:";
const COMMENT_PREFIX = "comment:";

export type GhostVaultErrorCode =
  | "indexeddb_unavailable"
  | "missing_secret"
  | "invalid_vault"
  | "delete_failed"
  | "browser_only";

export class GhostVaultError extends Error {
  readonly code: GhostVaultErrorCode;

  constructor(
    code: GhostVaultErrorCode,
    message: string,
    options?: { cause?: unknown },
  ) {
    super(message, options);
    this.name = "GhostVaultError";
    this.code = code;
  }
}

type StoredKey = {
  id: string;
  kind: "session" | "post" | "comment";
  key: string;
  alias?: string;
  createdAt: string;
};

export type GhostPostEntry = {
  id: string;
  alias: string | null;
  createdAt: string;
};

export type GhostVaultExport = {
  version: 1;
  exportedAt: string;
  sessionKey: string | null;
  posts: Array<{
    id: string;
    key: string;
    alias: string | null;
    createdAt: string;
  }>;
};

export type GhostDeleteTransport = (
  postId: string,
  ownerKey: string,
) => Promise<void>;

export type DeleteOwnPostOptions = {
  transport: GhostDeleteTransport;
};

let databasePromise: Promise<IDBDatabase> | null = null;

function postRecordId(postId: string): string {
  return `${POST_PREFIX}${postId}`;
}

function commentRecordId(commentId: string): string {
  return `${COMMENT_PREFIX}${commentId}`;
}

function decodeStoredKey(value: string): GhostSecret {
  try {
    return fromBase64Url(value);
  } catch (error) {
    throw new GhostVaultError(
      "invalid_vault",
      "Stored ghost key is not valid base64url",
      { cause: error },
    );
  }
}

function requestToPromise<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () =>
      reject(
        new GhostVaultError(
          "indexeddb_unavailable",
          "IndexedDB request failed",
          { cause: request.error },
        ),
      );
  });
}

function openDatabase(): Promise<IDBDatabase> {
  if (typeof indexedDB === "undefined") {
    return Promise.reject(
      new GhostVaultError(
        "indexeddb_unavailable",
        "IndexedDB is not available in this environment",
      ),
    );
  }
  if (databasePromise !== null) {
    return databasePromise;
  }

  databasePromise = new Promise<IDBDatabase>((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(STORE_NAME)) {
        database.createObjectStore(STORE_NAME, { keyPath: "id" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () =>
      reject(
        new GhostVaultError(
          "indexeddb_unavailable",
          "Could not open the ghost key vault",
          { cause: request.error },
        ),
      );
    request.onblocked = () =>
      reject(
        new GhostVaultError(
          "indexeddb_unavailable",
          "The ghost key vault is blocked by another tab",
        ),
      );
  }).catch((error: unknown) => {
    databasePromise = null;
    throw error;
  });

  return databasePromise;
}

async function withStore<T>(
  mode: IDBTransactionMode,
  operation: (store: IDBObjectStore) => IDBRequest<T>,
): Promise<T> {
  const database = await openDatabase();
  return new Promise<T>((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, mode);
    const request = operation(transaction.objectStore(STORE_NAME));
    let result: T | undefined;

    request.onsuccess = () => {
      result = request.result;
    };
    transaction.oncomplete = () => resolve(result as T);
    transaction.onerror = () =>
      reject(
        new GhostVaultError(
          "indexeddb_unavailable",
          "The key vault transaction failed",
          { cause: transaction.error },
        ),
      );
    transaction.onabort = () =>
      reject(
        new GhostVaultError(
          "indexeddb_unavailable",
          "The key vault transaction was aborted",
          { cause: transaction.error },
        ),
      );
  });
}

async function putRecords(records: StoredKey[]): Promise<void> {
  const database = await openDatabase();
  await new Promise<void>((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, "readwrite");
    const store = transaction.objectStore(STORE_NAME);
    for (const record of records) {
      store.put(record);
    }
    transaction.oncomplete = () => resolve();
    transaction.onerror = () =>
      reject(
        new GhostVaultError(
          "indexeddb_unavailable",
          "Could not write to the ghost key vault",
          { cause: transaction.error },
        ),
      );
    transaction.onabort = () =>
      reject(
        new GhostVaultError(
          "indexeddb_unavailable",
          "The ghost key vault write was aborted",
          { cause: transaction.error },
        ),
      );
  });
}

export async function saveSessionKey(secret: GhostSecret): Promise<void> {
  await putRecords([
    {
      id: SESSION_ID,
      kind: "session",
      key: toBase64Url(secret),
      createdAt: new Date().toISOString(),
    },
  ]);
}

export async function getSessionKey(): Promise<GhostSecret | null> {
  const record = await withStore<StoredKey | undefined>(
    "readonly",
    (store) => store.get(SESSION_ID) as IDBRequest<StoredKey | undefined>,
  );
  return record === undefined ? null : decodeStoredKey(record.key);
}

export async function deleteSessionKey(): Promise<void> {
  await withStore<undefined>("readwrite", (store) =>
    store.delete(SESSION_ID),
  );
}

export async function savePostKey(
  postId: string,
  secret: GhostSecret,
  alias?: string | null,
): Promise<void> {
  const record: StoredKey = {
    id: postRecordId(postId),
    kind: "post",
    key: toBase64Url(secret),
    createdAt: new Date().toISOString(),
  };
  if (alias) {
    record.alias = alias;
  }
  await putRecords([record]);
}

export async function getPostKey(postId: string): Promise<GhostSecret | null> {
  const record = await withStore<StoredKey | undefined>(
    "readonly",
    (store) =>
      store.get(postRecordId(postId)) as IDBRequest<StoredKey | undefined>,
  );
  return record === undefined ? null : decodeStoredKey(record.key);
}

export async function deletePostKey(postId: string): Promise<void> {
  await withStore<undefined>("readwrite", (store) =>
    store.delete(postRecordId(postId)),
  );
}

export async function saveCommentKey(
  commentId: string,
  secret: GhostSecret,
  alias?: string | null,
): Promise<void> {
  const record: StoredKey = {
    id: commentRecordId(commentId),
    kind: "comment",
    key: toBase64Url(secret),
    createdAt: new Date().toISOString(),
  };
  if (alias) {
    record.alias = alias;
  }
  await putRecords([record]);
}

export async function getCommentKey(
  commentId: string,
): Promise<GhostSecret | null> {
  const record = await withStore<StoredKey | undefined>(
    "readonly",
    (store) =>
      store.get(commentRecordId(commentId)) as IDBRequest<
        StoredKey | undefined
      >,
  );
  return record === undefined ? null : decodeStoredKey(record.key);
}

export async function deleteCommentKey(commentId: string): Promise<void> {
  await withStore<undefined>("readwrite", (store) =>
    store.delete(commentRecordId(commentId)),
  );
}

async function allRecords(): Promise<StoredKey[]> {
  return withStore<StoredKey[]>(
    "readonly",
    (store) => store.getAll() as IDBRequest<StoredKey[]>,
  );
}

/** Ids of ghost posts whose secret is still on this device. */
export async function listOwnPosts(): Promise<string[]> {
  return (await listOwnPostEntries()).map((entry) => entry.id);
}

/** Ids of ghost comments whose secret is still on this device. */
export async function listOwnCommentIds(): Promise<string[]> {
  const records = await allRecords();
  return records
    .filter((record) => record.kind === "comment")
    .sort((left, right) => left.createdAt.localeCompare(right.createdAt))
    .map((record) => record.id.slice(COMMENT_PREFIX.length));
}

export async function listOwnPostEntries(): Promise<GhostPostEntry[]> {
  const records = await allRecords();
  return records
    .filter((record) => record.kind === "post")
    .sort((left, right) => left.createdAt.localeCompare(right.createdAt))
    .map((record) => ({
      id: record.id.slice(POST_PREFIX.length),
      alias: record.alias ?? null,
      createdAt: record.createdAt,
    }));
}

/** Count for the logout warning: how many ghost posts you could still delete. */
export async function countOwnPosts(): Promise<number> {
  return (await listOwnPosts()).length;
}

export async function exportVault(): Promise<GhostVaultExport> {
  const records = await allRecords();
  const session = records.find((record) => record.kind === "session");

  return {
    version: 1,
    exportedAt: new Date().toISOString(),
    sessionKey: session?.key ?? null,
    posts: records
      .filter((record) => record.kind === "post")
      .sort((left, right) => left.createdAt.localeCompare(right.createdAt))
      .map((record) => ({
        id: record.id.slice(POST_PREFIX.length),
        key: record.key,
        alias: record.alias ?? null,
        createdAt: record.createdAt,
      })),
  };
}

export async function exportVaultJson(): Promise<string> {
  return JSON.stringify(await exportVault(), null, 2);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function parseVaultExport(input: unknown): GhostVaultExport {
  let parsed: unknown = input;
  if (typeof input === "string") {
    try {
      parsed = JSON.parse(input);
    } catch (error) {
      throw new GhostVaultError(
        "invalid_vault",
        "Vault export is not valid JSON",
        {
          cause: error,
        },
      );
    }
  }

  if (!isRecord(parsed) || parsed.version !== 1) {
    throw new GhostVaultError(
      "invalid_vault",
      "Unsupported vault export version",
    );
  }

  const sessionKey = parsed.sessionKey;
  if (sessionKey !== null && typeof sessionKey !== "string") {
    throw new GhostVaultError("invalid_vault", "Vault session key is invalid");
  }

  const posts = parsed.posts;
  if (!Array.isArray(posts)) {
    throw new GhostVaultError("invalid_vault", "Vault posts list is invalid");
  }

  const validated: GhostVaultExport["posts"] = [];
  for (const entry of posts) {
    if (
      !isRecord(entry) ||
      typeof entry.id !== "string" ||
      typeof entry.key !== "string"
    ) {
      throw new GhostVaultError("invalid_vault", "Vault post entry is invalid");
    }
    validated.push({
      id: entry.id,
      key: entry.key,
      alias: typeof entry.alias === "string" ? entry.alias : null,
      createdAt:
        typeof entry.createdAt === "string"
          ? entry.createdAt
          : new Date().toISOString(),
    });
  }

  return {
    version: 1,
    exportedAt:
      typeof parsed.exportedAt === "string"
        ? parsed.exportedAt
        : new Date().toISOString(),
    sessionKey,
    posts: validated,
  };
}

/** Merge an exported vault back into this device. */
export async function importVault(input: unknown): Promise<void> {
  const data = parseVaultExport(input);
  const records: StoredKey[] = [];

  if (data.sessionKey !== null) {
    records.push({
      id: SESSION_ID,
      kind: "session",
      key: toBase64Url(decodeStoredKey(data.sessionKey)),
      createdAt: data.exportedAt,
    });
  }

  for (const entry of data.posts) {
    records.push({
      id: postRecordId(entry.id),
      kind: "post",
      key: toBase64Url(decodeStoredKey(entry.key)),
      ...(entry.alias === null ? {} : { alias: entry.alias }),
      createdAt: entry.createdAt,
    });
  }

  if (records.length > 0) {
    await putRecords(records);
  }
}

/** Download the vault as a JSON file (browser only). */
export async function downloadVault(
  filename = "postly-ghost-keys.json",
): Promise<void> {
  if (typeof document === "undefined" || typeof URL === "undefined") {
    throw new GhostVaultError(
      "browser_only",
      "Downloading the vault requires a browser",
    );
  }
  const blob = new Blob([await exportVaultJson()], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

/**
 * Delete a ghost post by recomputing its owner key locally. The secret never
 * leaves the browser; only the resulting `owner_key` is handed to the injected
 * transport (the app pins it to the typed API client in `lib/api/ghost.ts`).
 */
export async function deleteOwnPost(
  postId: string,
  options: DeleteOwnPostOptions,
): Promise<void> {
  const secret = await getPostKey(postId);
  if (secret === null) {
    throw new GhostVaultError(
      "missing_secret",
      `No ghost secret is stored for post ${postId}`,
    );
  }

  const ownerKey = await deriveOwnerKey(secret, postId);

  try {
    await options.transport(postId, ownerKey);
  } catch (error) {
    throw new GhostVaultError(
      "delete_failed",
      `Deleting ${postId} failed`,
      { cause: error },
    );
  }

  await deletePostKey(postId);
}

/** Close the connection but keep the data (tests simulate a page reload). */
export async function closeVault(): Promise<void> {
  if (databasePromise === null) {
    return;
  }
  const pending = databasePromise;
  databasePromise = null;
  try {
    (await pending).close();
  } catch {
    // The database never opened; nothing to close.
  }
}

/** Delete the whole vault. */
export async function resetVault(): Promise<void> {
  await closeVault();
  if (typeof indexedDB === "undefined") {
    return;
  }
  await requestToPromise(indexedDB.deleteDatabase(DB_NAME));
}
