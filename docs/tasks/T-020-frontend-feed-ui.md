# T-020 · Frontend: feed UI, post card, composer, vote buttons

- status: done
- quest: Q1
- depends: T-015, T-019
- owner: s-20261101-0810
- updated: 2026-11-02 08:15
- files: apps/web/src/app/**, apps/web/src/components/**, apps/web/src/lib/**, apps/web/src/styles/globals.css, apps/web/package.json, apps/web/package-lock.json, apps/web/components.json

## Goal

Make the app look like the product: a feed with four tabs, a post card with a photo, vote buttons that
update immediately, and a composer that lets someone report a problem from their phone in under a minute.

## Done when

- [x] The home page shows the four tabs (For You / Trending / New / Nearby) and switches between them.
- [x] A post card shows: author alias, area name, category, time ago, title, body, photo, vote counts,
      comment count, status badge.
- [x] Upvote/downvote buttons update the count immediately (optimistic) and reconcile with the server
      response; the "my vote" state is shown.
- [x] The composer validates the title/body, requires an area, uploads a photo with a progress state, and
      shows a blurHash placeholder while the image loads.
- [x] Area selection offers the three paths: type a PIN, search by name, "use my location" (browser GPS).
      If the user denies GPS, the PIN/search path still works.
- [x] The app looks acceptable on a 375 px-wide phone screen.
- [x] `npm run lint`, `npm run typecheck`, `npm run build` pass.
- [x] The client only talks to the API through `lib/api/client.ts` — no raw `fetch` in components.

## Notes / gotchas

- Use the typed client from T-006. If a type is missing, fix the API response model, not the component.
- TanStack Query for server state: `useQuery` for feeds, `useMutation` with optimistic updates for votes.
- shadcn/ui is the component library (`npx shadcn@latest init`, then add the components you need: button,
  card, dialog, tabs, input, textarea, avatar, badge, skeleton, toast).
- Images: serve them through the signed-URL route (T-016). Never expose a raw file path in the DOM.
- The composer must work for a ghost user — the ghost key path from T-012 — with no account required.
- Geolocation requires a secure context: `http://localhost` counts as secure, so it works in dev.
- Keep the components small and composable. A task-sized component budget: one file per component.
- Accessibility: real `<button>` elements, labels on inputs, keyboard-usable tabs.

## Research notes

The API this screens consume: `docs/API.md`. The product behaviour: `docs/PLAN.md` §4.

### shadcn setup (reuse in later frontend tasks)

```bash
npx shadcn@4.23.0 init -d
npx shadcn@4.23.0 add card tabs input textarea avatar badge skeleton dialog progress sonner select label -y
```

- The current shadcn is **4.23.0 / `base-nova`**, which uses **`@base-ui/react`**, not Radix, and a small
  `cn` package (`cn@0.5.1`) instead of `clsx` + `tailwind-merge`. Components live in
  `src/components/ui/`; `components.json` uses the `~/*` alias.
- Added components: button, card, tabs, input, textarea, avatar, badge, skeleton, dialog, progress, sonner,
  select, label.
- New runtime deps pinned exactly (the CLI writes `^` ranges): `@tanstack/react-query@5.105.0`,
  `blurhash@2.0.5` (decoder for the placeholder), `@base-ui/react@1.9.0`,
  `class-variance-authority@0.7.1`, `cn@0.5.1`, `lucide-react@1.66.0`, `next-themes@0.4.6`,
  `shadcn@4.23.0`, `sonner@2.0.8`, `tw-animate-css@1.4.0`.
- `npm run api:types` was re-run on the host; `src/lib/api/types.ts` now has FeedPost/PostOut/AreaOut/etc.
- The scaffold puts app code under `apps/web/src/`, so the task's `apps/web/app/**` paths resolve to
  `apps/web/src/app/**`.

### Architecture notes

- The page is client-rendered (`src/app/page.tsx` + `providers.tsx` with TanStack Query). The API client's
  default base URL is relative (`/api/v1`), which goes through the Next rewrite proxy.
- `lib/api/client.ts` gained `requestEnvelope()` so feed pages can read `meta.cursor`; all API calls go
  through `endpoints.ts` and the typed client. The ESLint rule still bans `fetch` elsewhere.
- Identity is **ghost-only for now** (no sign-in UI): `lib/identity.ts` creates the session key + alias,
  per-post keys, and `a:` voter keys from T-012. Google/pseudonymous sign-in remains a later task.
- The composer is **post-first, then upload** because `Media.post_id` is required: create post with
  `alias`/`owner_key`, then `POST /media` with the same owner key. Upload progress is an indeterminate
  staged progress bar; the API has no byte-progress stream.
- "My vote" is stored in `localStorage` (`lib/votes-store.ts`) because `GET /me/votes` is not implemented;
  the server response still corrects the counts.
- The Nearby tab requests browser GPS; denial shows a message and does not block the other tabs.

## Work log

- 2026-11-01 s-20261101-0810: built the shadcn base, typed endpoint wrappers, ghost identity wiring, feed
  tabs/cards/votes, composer with PIN/name/GPS area picker and blurHash images; lint/typecheck/build pass.

## Report

### 2026-11-01 · worker s-20261101-0810

- changed:
  - `apps/web/package.json` / `package-lock.json` — TanStack Query, blurhash, shadcn/Base UI deps (pinned
    exactly), `shadcn` + `tw-animate-css` for the generated theme.
  - `apps/web/components.json`, `src/components/ui/*`, `src/lib/utils.ts`, `src/styles/globals.css` —
    shadcn `base-nova` setup and the 13 components listed above.
  - `src/lib/api/client.ts` — `requestEnvelope()` for cursor meta; `endpoints.ts` — typed feed, area,
    category, post, media and vote calls.
  - `src/lib/identity.ts` — ghost session/post keys and voter keys; `votes-store.ts` — local "my vote";
    `geo.ts`, `time.ts`, `use-debounced-value.ts` helpers.
  - `src/app/providers.tsx`, `layout.tsx`, `page.tsx` — QueryClient + ThemeProvider + Toaster; feed shell.
  - `src/components/` — `app-header`, `feed-board`, `feed-list`, `post-card`, `vote-buttons`,
    `blurhash-image`, `composer`, `area-picker`, `category-icon`, `status-badge`.
  - `src/lib/api/types.ts` — regenerated from the live OpenAPI spec on the host.
- verified (real output):
  - `npm run typecheck` → exit 0.
  - `npm run lint` → `✔ No ESLint warnings or errors`.
  - `npm run build` → `✓ Compiled successfully`; 4 routes generated.
  - `npm run test:ghost` → 17 passed.
  - Rebuilt `postly-web`; compose is healthy and `http://localhost:3000` returns 200 with
    `Postly / For You / Trending / New / Nearby / Report` in the SSR HTML.
  - End-to-end through the Next proxy: ghost post created, PNG uploaded, feed returned the post with
    `media=1` and its blurHash, the signed URL served `200 86 image/png`, a vote returned `up=1`, and the
    post was deleted with `204`. DB/files cleaned afterwards.
- issues / notes:
  - **No sign-in UI**: the app posts as a ghost. The backend supports all three modes; Google/pseudo
    sign-in is a separate task.
  - For You is anonymous (no follows), so it matches Trending in the UI; the backend personalisation is
    ready for a future session-based UI.
  - "My vote" is local-only until `GET /me/votes` exists; clearing site data resets the highlight.
  - Photo upload happens after the post is created; if it fails, the post remains and a toast explains.
  - `npm install` reports 27 upstream advisories (2 low, 21 moderate, 4 high) from the new dependency
    tree; no forced upgrades were applied, and all direct versions are pinned.
  - Responsive behaviour was verified by construction (max-width cards, 4-column tabs, mobile dialog) and
    the SSR smoke, not with a real 375 px browser screenshot.
- next: T-021 (delete flows) is unblocked; it must delete the media files left by the post-first upload.

## Manager review

### 2026-11-01 · manager s-20261101-0813

- verdict: **accepted**. I ran the whole chain myself, rebuilt the web image and drove the app end-to-end
  through the Next proxy — including the multipart upload and the DELETE-with-body that T-012's review
  had flagged as unproven. I also fixed one packaging defect the worker introduced.
- checked (re-run by the manager; nothing taken from the worker's report):
  - `npm run lint` → `✔ No ESLint warnings or errors`; `npm run typecheck` → exit 0; `npm run build` →
    `✓ Compiled successfully` (`/` 96.3 kB, 216 kB First Load JS); `npm run test:ghost` → 17 pass ✓.
  - **The single-fetch-door invariant holds.** The only real `fetch(` under `apps/web/src/` is
    `src/lib/api/client.ts:158`; the second grep hit is `query.refetch()` in `feed-list.tsx`, which the
    ESLint rule correctly allows. Every call goes through `src/lib/api/endpoints.ts` → the typed client ✓.
  - **The types are regenerated and complete.** `src/lib/api/types.ts` now carries all **21** endpoints
    (feeds, posts, comments, votes, media, areas, categories, auth) and every schema the components use
    (`FeedPost`, `PostOut`, `AreaOut`, `CommentOut`, `VoteOut`, `MediaUploadOut`, `SignedUrlOut`,
    `CategoryOut`, `AreaDetection`, `PostCreate`) ✓.
  - **The pins are exact and current.** `npm view <pkg> dist-tags` for all ten new packages → each is the
    current `latest` (`@base-ui/react 1.9.0`, `@tanstack/react-query 5.105.0`, `blurhash 2.0.5`,
    `class-variance-authority 0.7.1`, `cn 0.5.1`, `lucide-react 1.66.0`, `next-themes 0.4.6`,
    `shadcn 4.23.0`, `sonner 2.0.8`, `tw-animate-css 1.4.0`); the `beta` tags are unrelated old
    prereleases. No `^`/`~` anywhere ✓ (`AGENTS.md` rule 5).
  - **The live app.** I rebuilt the `postly-web` image, recreated the container and confirmed the stack is
    healthy; `http://localhost:3000` returns the SSR HTML (19,735 bytes) containing **For You / Trending /
    New / Nearby** and the **Report** button ✓.
  - **End-to-end through the Next proxy** — the check T-012's review had left open:
    `POST /api/v1/posts` → **201**; `POST /api/v1/media` (multipart **with** the `owner_key` field) →
    **201** with the blurHash, so the rewrite proxy **does** forward a multipart body ✓;
    `GET /api/v1/feed/new` → the post with `media=[{…blur_hash…}]`, `author: null`, the alias snapshot,
    the area and the category ✓; `GET /media/{id}/signed` → the URL; fetching it through the proxy →
    **200 `image/png`** with the correct PNG magic bytes ✓; `PUT /votes/POST/{id}` → **200 `up=1`** ✓;
    `DELETE /posts/{id}` **with a JSON body through the proxy** → **204**, then the post is **404** ✓.
    (I also confirmed the negative: a multipart upload *without* the `owner_key` is rejected with
    **403 `not_owner`** — the ownership rule holds on the upload path too.)
  - **The composer** (read): validates the title/body/area/category ✓; creates the ghost identity and the
    per-post key **before** the post ✓; post-first-then-upload, with a toast if the photo fails ✓; a staged
    progress bar ✓; and a best-effort key cleanup when the create fails ✓.
  - **The area picker** (read): PIN/name search through `/areas/search` and GPS through `/areas/detect` ✓;
    the Nearby tab asks for the browser location and, on denial, shows "Try location again" **without**
    blocking the other tabs ✓.
  - **The post card** (read): alias, area + district + PIN, time ago, category, title/body, the photo with
    its blurHash placeholder, the vote counts, the comment count, the status badge and the distance on the
    Nearby tab ✓.
  - **The votes** (read): optimistic update, reconciliation with the server's counters, rollback + toast on
    failure, and the "my vote" state from `localStorage` ✓.
  - **Environment left clean:** 0 posts, 0 media rows, 0 files in the media volume, 1 pre-existing user ✓.
- change I made (manager):
  - **`shadcn` was declared as a runtime dependency.** Nothing under `src/` imports it — it is the scaffold
    CLI — and it dragged `@shadcn/registry` → `deepmerge` (a prototype-pollution advisory) into the
    production dependency set. I moved it to `devDependencies` (`package.json` plus a regenerated lockfile:
    `node_modules/shadcn` is now flagged `dev: true`) and re-ran the whole chain: lint clean, typecheck
    exit 0, build ✓, and `npm audit --omit=dev` dropped from **11 vulnerabilities (2 low, 5 moderate,
    4 high)** to **5 (1 moderate, 4 high)**. The remaining five are pre-existing (`next`/`postcss` and
    `@t3-oss/env-nextjs`/`zod`) and every fix is a major-version bump — pinning them and revisiting at a
    planned upgrade is the right call.
- notes (no action required, carried forward):
  - **No sign-in UI** — the app posts as a ghost. The backend supports all three modes; a session UI is a
    separate task, and until then For You is anonymous (so it shows the same order as Trending).
  - **"My vote" lives in `localStorage`** until `GET /me/votes` exists (marked "not implemented yet" in
    `docs/API.md`); clearing site data resets the highlight, and the server counters still reconcile.
  - **The post card shows the comment count, but there is no comments UI.** T-018's API is live, yet no
    task on the board owns the thread view — it needs one (the board jumps from T-020 to T-021).
  - **The upload is post-first, then the photo** (`Media.post_id` is required). If the upload fails the post
    stays and a toast explains it — T-021 must delete the media **files** when a post is deleted (the rows
    cascade, the files do not).
  - **The Docker runner still ships the dev dependencies**: the `web` Dockerfile runs `npm ci` (with dev
    deps) in the deps stage and copies the whole `node_modules` into the runner, so the `shadcn` CLI is in
    the production image even though it is now a dev dependency. A `npm ci --omit=dev` prod-deps stage
    would fix it — a small, separate Dockerfile change.
  - **The 375 px check is verified by construction, not by a browser.** The layout is `max-w-xl px-4`, the
    tabs are a 4-column grid and the composer dialog is `max-h-[90vh] overflow-y-auto` with `sm:max-w-lg`
    (full width on a phone). I could not take a real 375 px screenshot in this environment, so the
    *visual* result is still unproven — the first person to open the app on a phone should look at it.
  - **The web container must be rebuilt after a dependency change** (`docker compose build web`); the
    running image kept the old `node_modules` until I rebuilt it.
- next: **T-021** (delete flows) is unblocked and must delete the media files; the comments UI and the
  session sign-in still need task files.

### 2026-11-02 · manager s-20261102-0809 — re-verification before the first commit

- verdict: **accepted, unchanged.** The work still holds; nothing in the tree had been committed, so this
  pass re-ran every check from scratch and drove the live app end-to-end again before committing.
- checked (re-run by me; nothing taken from the earlier reports):
  - `npm run lint` → `✔ No ESLint warnings or errors`; `npm run typecheck` → exit 0; `npm run build` →
    `✓ Compiled successfully` (`/` 96.3 kB, 216 kB First Load JS); `npm run test:ghost` → **17 pass, 0 fail**.
  - **The single-fetch-door invariant holds.** The only real `fetch(` under `apps/web/src/` is
    `src/lib/api/client.ts:158` (the default `fetchImpl`); the second hit is `query.refetch()` in
    `feed-list.tsx:91`. The ESLint `no-restricted-syntax` rule covers `src/**` except `client.ts`, so a second
    call site would fail `npm run lint` ✓.
  - **Pins.** `npm view <pkg> dist-tags`: `@base-ui/react 1.9.0`, `blurhash 2.0.5`, `cn 0.5.1`,
    `lucide-react 1.66.0`, `next-themes 0.4.6`, `class-variance-authority 0.7.1`, `tw-animate-css 1.4.0`,
    `sonner 2.0.8`, `shadcn 4.23.0` — all still the current `latest`, none a prerelease, no `^`/`~`
    anywhere ✓. **One drift:** `@tanstack/react-query` `latest` is now **5.105.1** while the tree pins
    **5.105.0** — a patch release. The pin is exact and not a prerelease, so the rule is satisfied; I left
    the lockfile alone rather than bump a dependency during a verification pass. Worth taking at the next
    planned upgrade.
  - **The live stack.** `docker compose ps` → `api`/`db`/`web` all healthy; `docker compose build web` →
    image built (every layer cached → the running image already contains this tree); `GET http://localhost:3000/`
    → **200, 19,734 bytes**, containing **For You / Trending / Nearby** and **Report** ✓.
  - **End-to-end through the Next rewrite proxy** (fresh script, ghost identity, base64url `owner_key`):
    `GET /areas/search?q=110005` → 200 · `GET /categories` → 200 · `POST /posts` → **201** ·
    `POST /media` (multipart **with** the `owner_key` field) → **201** with
    `blur_hash: LIHV0EOr$O3ATbMkEP1{I?wLJ+,F` · `GET /feed/new` → **200**, the post is there with
    `media=1` and the same blurHash, the alias snapshot, the area, the category and `author: null` ·
    `GET /media/{id}/signed` → 200 → the signed file → **200 `image/png`** · `PUT /votes/POST/{id}` → **200,
    `upvote_count: 1`** · `DELETE /posts/{id}` (JSON body with `owner_key`) → **204** · `GET /posts/{id}` →
    **404** ✓.
  - **The components** (read again): `feed-board` (four tabs, GPS on Nearby, a "Try location again" path that
    does not block the other tabs); `vote-buttons` (optimistic update → reconcile with the server counters →
    rollback + toast on failure, `aria-pressed` for the "my vote" state); `composer` (validates
    title/body/area/category, creates the ghost identity and the per-post key **before** the post,
    post-first-then-upload with a toast if the photo fails, staged progress, best-effort key cleanup);
    `area-picker` (one search field for both the PIN and the name, plus GPS; a GPS error leaves the PIN/name
    path usable); `post-card` (alias, area + district + PIN, time ago, category, title/body, the blurHash
    photo, vote counts, comment count, status badge, distance on Nearby); `blurhash-image` (canvas blurHash
    placeholder, skeleton fallback) ✓.
- issues: **none new.** The known gaps from the first review stand unchanged and carry forward: no sign-in
  UI (the app posts as a ghost); "my vote" lives in `localStorage` until `GET /me/votes` exists; no comments
  UI is owned by any task on the board; a deleted post leaves its **media file** on disk (the rows cascade,
  the files do not) → T-021; the `web` image still ships the dev dependencies; the 375 px view is verified
  by construction, not by a browser.
- my own mistakes, logged so the next session does not repeat them: my first smoke script sent
  `direction: "up"` instead of the API's `value: 1` → 422, and a hand-written base64 PNG that Pillow
  rejected → `invalid_image` 422. Both were faults in **my test script**, not in the app; the corrected
  script passed end to end.
- environment left clean: **0 posts, 0 media rows, 0 files in the media volume**, 1 pre-existing user. One
  **orphan vote** from the earlier review session survives (`Vote` has no FK to its target, so deleting a post
  leaves its vote behind) — that is exactly the gap T-021 must sweep; I removed only my own two.
- next: the tree is committed; **T-021 (delete flows)** is the next task and must delete the media **files**,
  the orphaned votes, the comments, the reveals and the views.
