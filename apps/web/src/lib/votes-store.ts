"use client";

export type VoteValue = 1 | -1;

const STORAGE_KEY = "postly.votes";
const memory = new Map<string, VoteValue>();

function readStore(): Record<string, VoteValue> {
  if (typeof localStorage === "undefined") {
    return {};
  }
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return {};
    }
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null) {
      return {};
    }
    const votes: Record<string, VoteValue> = {};
    for (const [key, value] of Object.entries(parsed as Record<string, unknown>)) {
      if (value === 1) {
        votes[key] = 1;
      } else if (value === -1) {
        votes[key] = -1;
      }
    }
    return votes;
  } catch {
    return {};
  }
}

function writeStore(votes: Record<string, VoteValue>): void {
  if (typeof localStorage !== "undefined") {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(votes));
    } catch {
      // Storage full/blocked: the in-memory map still works for this tab.
    }
  }
}

/** "My vote" is client-side UI state (the server has no /me/votes route yet). */
export function getMyVote(targetId: string): VoteValue | null {
  return memory.get(targetId) ?? readStore()[targetId] ?? null;
}

export function setMyVote(targetId: string, value: VoteValue | null): void {
  if (value === null) {
    memory.delete(targetId);
  } else {
    memory.set(targetId, value);
  }

  const votes = readStore();
  if (value === null) {
    delete votes[targetId];
  } else {
    votes[targetId] = value;
  }
  writeStore(votes);
}

/** Clear every remembered vote after an account/ghost-session deletion. */
export function clearMyVotes(): void {
  memory.clear();
  if (typeof localStorage !== "undefined") {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // Storage full/blocked: the in-memory map is already clear.
    }
  }
}
