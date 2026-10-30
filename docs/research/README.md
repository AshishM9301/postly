# RESEARCH CACHE

Read before you search the web. If a topic is not here, research it **once**, write it into a numbered file
here, and cite that file in your task's `## Research notes`. Never make two sessions pay for the same lookup.

| File | Covers |
|---|---|
| [`00-versions.md`](00-versions.md) | Every pinned dependency version, the npm dist-tag rule, prisma-client-py internals, and the model IDs |

## How to add one

Create `docs/research/<n>-<topic>.md` with:

1. **Question** — what was actually being answered.
2. **Answer** — the facts, with the exact versions/URLs/licences.
3. **Verified how** — the command that was run, so the next person can re-check it cheaply.
4. **Gotchas** — the traps (prerelease tags, casing bugs, rate limits, policy limits).

Keep it under ~150 lines. Link it from the task file that needed it.
