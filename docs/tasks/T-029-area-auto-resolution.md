# T-029 · The area is resolved, not asked for: GPS, PIN at first open, internet fallback

- status: ready
- quest: Q1
- depends: T-014, T-022
- owner: -
- updated: 2026-11-02 10:25
- files: apps/web/src/lib/geo.ts, apps/web/src/lib/area-preference.ts, apps/web/src/components/area-prompt.tsx, apps/web/src/components/app-shell.tsx, apps/web/src/components/composer.tsx, apps/web/src/components/area-picker.tsx, docs/API.md

## Goal

Nobody should have to **pick** an area from a list of 103 PIN codes before reporting a problem. The area is
resolved, in this order:

1. **GPS** — the browser location, when the user allows it (`/areas/detect` already exists).
2. **PIN code** — asked **once, when the website opens**, if there is no location yet. The PIN is typed into
   a one-field prompt, not chosen from a dropdown.
3. **The internet** — if neither is available, the browser asks a **geo-IP** service where it roughly is and
   that point is resolved to the nearest area.

The result is a **device-local preference** (`localStorage`): the area id and PIN only — never the raw GPS
coordinates, never the IP. The user can always change it.

## Done when

- [ ] On the **first visit** (no area stored) the app asks for the PIN **once** — a single input, not a
      picker — and a valid PIN resolves to its area (`GET /api/v1/areas/search?q=110019`).
- [ ] With the location allowed, the app resolves the area through `GET /api/v1/areas/detect?lat=&lng=`
      and **does not** ask for a PIN.
- [ ] With **no** location and **no** PIN, the app falls back to the geo-IP lookup, resolves the returned
      coordinates to the nearest area, and shows it. If the lookup fails, the app asks for the PIN instead —
      the flow never dead-ends.
- [ ] The resolved area is **remembered** (the area id + PIN in `localStorage`) and reused on the next
      visit; the PIN prompt does not appear again.
- [ ] **The IP never reaches our server and is never stored.** The geo-IP call is made by the browser, only
      its coarse coordinates are read, and only the **area id / PIN** are persisted.
- [ ] The raw GPS coordinates are **not** persisted either (only the area id and the PIN).
- [ ] The user can change or clear the area at any time, and the composer shows the area it will post to.
- [ ] `npm run lint` → `✔ No ESLint warnings or errors`; `npm run typecheck` → exit 0; `npm run build` →
      `✓ Compiled successfully`; `npm run test:ghost` → all pass.
- [ ] The only `fetch(` under `apps/web/src/` is in `src/lib/api/client.ts` — **note**: the geo-IP call is
      a browser call to a **third-party** host; the ESLint rule bans `fetch` outside the client, so this
      call needs a documented, explicit exception (a named seam in `lib/geo.ts` with a comment saying
      exactly why) — do not widen the ban.
- [ ] `docs/API.md` §2 or §3 documents the resolution order and the local preference.

## Notes / gotchas

- The ESLint rule in `apps/web/eslint.config.js` bans `fetch` everywhere under `src/**` except
  `lib/api/client.ts`. The geo-IP call is the **only** legitimate exception; if you add one, keep it in
  `lib/geo.ts` with a comment and a `// eslint-disable-next-line` that says why.
- **Privacy (AGENTS.md §2 rule 7):** never store email, phone, IP or User-Agent. A geo-IP lookup is a
  one-shot browser call; the IP must not be sent to our API, logged by us, or written to storage. Only the
  **area id / PIN** is persisted, and that is a coarse locality the user chose, not an identifier.
- The geo-IP service must be picked deliberately: check the terms, the rate limit and whether it needs a
  key, and record the choice, the URL and the licence in this task's `## Research notes`. It must degrade
  gracefully (timeout ~3 s → fall back to the PIN prompt).
- `/areas/detect` always returns the nearest area (no distance cut-off), so a coarse geo-IP coordinate
  still resolves to something sensible. Show the **area name and PIN** to the user so a wrong guess is
  obvious and fixable.
- A PIN that does not exist (Delhi has 103 of them) must show a clear message and keep the input open —
  do not silently fall back to the geo-IP guess.
- The browser location needs a secure context; `http://localhost` counts as one, so it works in dev.
- The Nearby feed tab already asks for GPS (T-022's `feed-tab-provider`): do not ask twice in a row.

## Research notes

- The areas API: `docs/API.md` §3 — `GET /areas/search?q=` (six digits = exact PIN, otherwise a name
  search over the name, its aliases and the district) and `GET /areas/detect?lat=&lng=` (nearest area,
  always, with `distance_meters`).
- The 103 Delhi areas and their quirks: `docs/GEO_DATA.md`.
- **The geo-IP service is not researched yet.** Before coding, pick one, check its terms and limits, and
  record it here — do not re-derive it later.

## Work log

## Report

## Manager review
