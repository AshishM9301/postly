# T-022 · Frontend shell: left nav rail, mobile tab bar, black/red/white theme

- status: done
- quest: Q1
- depends: T-020
- owner: s-20261102-0837
- updated: 2026-11-02 09:30
- files: apps/web/src/app/**, apps/web/src/components/**, apps/web/src/lib/**, apps/web/src/styles/globals.css

## Goal

The app should look like a real posting app, not a bare page. On the desktop there is a **nav rail on the
left** — collapsed to icons, expanding to labels on hover. On a phone the same destinations move to a
**bottom tab bar**, the way Instagram does it. The whole palette is **black, red and white**: red is the
only accent, the surfaces are black or white, the text is the opposite of its surface.

The nav and the feed tabs must be **one state**: clicking *Trending* in the rail switches the feed to
Trending, and so does clicking the *Trending* tab — no page reload, no second source of truth.

## Done when

- [x] `curl http://localhost:3000` → the SSR HTML contains the four destinations
      (For You / Trending / New / Nearby) and the Report action.
- [x] At ≥ 768 px the rail is **fixed on the left**, collapsed to ≈ 64 px and **expanding to ≥ 240 px on
      hover** (a CSS width transition on the rail itself, labels fading in with it).
- [x] Below 768 px the rail is **hidden** and a **bottom tab bar** is visible, fixed to the bottom, with
      the same four destinations plus the Report action; the last card in the feed is not covered by it
      (bottom padding on the content column).
- [x] The rail, the bottom bar and the tab strip read **one** tab state — switching in any of them
      switches the feed everywhere (a single context, not three copies of the state).
- [x] The palette is black / red / white: `--primary` is the same red in `:root` and `.dark`, the
      background is white in light mode and black in dark mode, and no other hue is introduced
      (`grep` `globals.css` for the colour tokens).
- [x] A theme toggle switches light/dark and the choice survives a reload.
- [x] The Report action opens the **same** composer from every surface that offers it (one dialog
      instance, not three).
- [x] `npm run lint` → `✔ No ESLint warnings or errors`; `npm run typecheck` → exit 0; `npm run build` →
      `✓ Compiled successfully`.
- [x] The only `fetch(` under `apps/web/src/` is in `src/lib/api/client.ts` (the ESLint rule enforces it).

## Notes / gotchas

- **T-026 refines this task's shell** and runs right after it: the nav items centred vertically in the
  rail, the user / night-mode / Report controls moved into the rail (not the top bar) and the "Postly"
  wordmark removed. Build this task so T-026 can move things without unpicking the structure: keep the
  rail's parts in separate components (`rail-nav`, `rail-footer`, `rail-brand`) and the top bar in its own
  component.
- shadcn here is **4.23.0 / `base-nova`** on **`@base-ui/react`** — its `Tabs`/`Dialog` are Base UI, not
  Radix. `cn` (v0.5.1) is a tailwind-merge clone, so a later class wins over an earlier conflicting one.
- The composer currently renders its own `DialogTrigger`. To open it from several places, lift the dialog
  into a provider (`ComposerProvider` + a `ComposerButton` trigger) instead of rendering the dialog twice.
- The feed tab lives in `components/feed-board.tsx`. Move it into a context so the nav can drive it —
  `useSearchParams` would need a `Suspense` boundary in Next 15, so a context is the cheaper route.
- The *Nearby* tab asks the browser for GPS when it is opened. If the nav can open it too, the request must
  fire exactly once per visit (a `useRef` guard), or a denied permission becomes an endless retry loop.
- `next-themes` drives `.dark` on `<html>`; `layout.tsx` already has `suppressHydrationWarning`.
- Mobile bottom bars eat the safe area: pad with `env(safe-area-inset-bottom)`.

## Research notes

- The API this screens consume: `docs/API.md`. The product behaviour: `docs/PLAN.md` §4.
- shadcn setup notes and the exact pinned versions are in `docs/research/00-versions.md` and in T-020's
  `## Research notes` — do not re-derive them.
- The previous theme is the stock shadcn neutral ramp (grey `primary`); T-022 replaces it with the
  black/red/white ramp.

## Work log

- 2026-11-02 s-20261102-0837: added the app shell (desktop rail + mobile tab bar), shared feed-tab
  context, single composer provider, black/red/white tokens and a persisted theme toggle; lint,
  typecheck, build pass and the rebuilt web container serves the new SSR shell.

## Report

### 2026-11-02 · worker s-20261102-0837

- changed:
  - `src/components/feed-tab-provider.tsx` (new) — the single source of truth for the feed tab plus the
    GPS state. `selectTab()` triggers the location request at most once per mount (`useRef`), so the rail,
    the bottom bar and the tab strip cannot start an endless prompt loop.
  - `src/components/composer-provider.tsx` (new) — owns the one composer dialog and exposes
    `openComposer()`; header, rail and mobile bar all open the same instance.
  - `src/components/app-shell.tsx` (new), `desktop-nav.tsx`, `rail-brand.tsx`, `rail-nav.tsx`,
    `rail-footer.tsx`, `mobile-tab-bar.tsx` (new) — fixed left rail (64 px → 240 px on hover/focus, labels
    fade with the width), fixed mobile bottom bar (safe-area padding) and content bottom padding.
    The rail is split into brand/nav/footer so T-026 can move the user/night-mode controls without a
    rewrite.
  - `src/components/theme-toggle.tsx` (new) — `next-themes` toggle (rail footer on desktop, header on
    mobile).
  - `src/components/composer.tsx` — now a controlled `ComposerDialog`; removed the local trigger/state.
  - `src/components/feed-board.tsx` — reads the shared tab/GPS state instead of owning a second copy.
  - `src/components/app-header.tsx`, `src/app/providers.tsx`, `src/app/page.tsx` — wired the shell and
    provider tree.
  - `src/styles/globals.css` — red `--primary` in both `:root` and `.dark`, white/black backgrounds, red
    sidebar primary, neutral ramp elsewhere.
  - `status-badge.tsx`, `vote-buttons.tsx`, `area-picker.tsx` — removed amber/blue/emerald/rose utility
    colours so the visible palette stays black/red/white.
- verified (real output):
  - `npm run lint` → `✔ No ESLint warnings or errors`.
  - `npm run typecheck` → exit 0, no output.
  - `npm run build` → `✓ Compiled successfully`; `/` 21.6 kB, 220 kB First Load JS.
  - `npm run test:ghost` → `tests 17`, `pass 17`, `fail 0`.
  - `docker compose build web` + `docker compose up -d web` → container healthy;
    `curl http://localhost:3000` → **30516 bytes**, containing `Postly`, `For You`, `Trending`, `New`,
    `Nearby`, `Report`, `aria-label="Primary"`, `hover:w-60`, `transition-[width]`, `md:hidden`,
    `fixed inset-x-0 bottom-0`, the safe-area bottom padding and `Switch to dark theme`.
  - `Select-String ... '\bfetch\('` over `apps/web/src/**/*.{ts,tsx}` → only
    `src/lib/api/client.ts:158`.
  - `globals.css` token check → `--primary: oklch(0.577 0.245 27.325)` in both `:root` and `.dark`;
    every other chroma token is neutral (`0 0`); the only hue is 27.325 (red).
- issues / notes:
  - The rail hover expansion, mobile breakpoint and safe-area padding are verified from the rendered
    classes and SSR HTML, not a real browser screenshot. The first person to open it at 768/375 px should
    eyeball it.
  - Theme persistence is provided by `next-themes` (localStorage + `.dark` on `<html>`); there is no
    browser-automation test for a reload in this environment.
  - The header still carries the alias/Report/theme controls (theme hidden on desktop now). T-026 is
    expected to move the user/night-mode controls fully into the rail and remove the wordmark.
  - No new dependencies were added, so `package.json` / lockfile are untouched.
- next: manager verification; T-023 (comments UI) is unblocked.

## Manager review

### 2026-11-02 · manager s-20261102-0925

- verdict: **accepted**. The shell is real, the state is shared and the palette is genuinely
  black/red/white — I checked the *shipped* stylesheet, not just the source.
- checked (re-run by me; nothing taken from the worker's report):
  - `npm run lint` → `✔ No ESLint warnings or errors`; `npm run typecheck` → exit 0; `npm run build` →
    `✓ Compiled successfully` (`/` 21.6 kB, 220 kB First Load JS); `npm run test:ghost` → 17 pass, 0 fail.
  - **The single-fetch-door invariant holds**: the only real `fetch(` under `apps/web/src/` is
    `src/lib/api/client.ts:158` (the other hit is `query.refetch()` in `feed-list.tsx:91`).
  - **The rail**: `desktop-nav.tsx` → `fixed inset-y-0 left-0 z-50 hidden w-16 … transition-[width]
    duration-200 ease-out hover:w-60 focus-within:w-60 md:flex` → **64 px collapsed, 240 px on hover or
    keyboard focus**, with the labels fading in on `group-hover/nav` ✓ (keyboard users get the expanded
    rail too, which the task file did not ask for but is right).
  - **The mobile bar**: `mobile-tab-bar.tsx` → `fixed inset-x-0 bottom-0 z-50 … pb-[env(safe-area-inset-bottom)]
    md:hidden` with a 5-column grid (the four destinations + Report), and the content column carries
    `pb-[calc(5.5rem+env(safe-area-inset-bottom))] md:pb-8`, so the last card is never covered ✓.
  - **One tab state**: `feed-tab-provider.tsx` owns the tab *and* the GPS state; the rail, the mobile bar
    and the tab strip all read it — there is no second copy ✓. The location prompt is guarded by
    `autoLocated.current` (a `useRef`), so a denied permission cannot become a retry loop ✓.
  - **One composer**: `composer-provider.tsx` renders the single `ComposerDialog`; the header, the rail
    and the mobile bar all call `openComposer()` ✓.
  - **The palette, checked in the shipped CSS**: `/_next/static/css/a546442cb6e46894.css` contains
    **exactly one chromatic colour** — `oklch(57.7% .245 27.325)`, the red — used for `--primary` in
    `:root` **and** in `.dark` (2 occurrences); every other token is neutral (chroma `0`). No
    `amber/blue/emerald/rose/slate` utility class is left anywhere in `apps/web/src` outside
    `components/ui/` ✓ — that is black, red and white, nothing else.
  - **The theme toggle**: `theme-toggle.tsx` drives `next-themes` and uses the `mounted` guard, so it
    cannot flicker on hydration; next-themes persists the choice in `localStorage` (the reload itself is
    not browser-tested in this environment).
  - **The live app**: `docker compose build web` → every layer cached, i.e. the running image already
    contains this tree; `GET http://localhost:3000/` → **200, 30,516 bytes** of SSR HTML containing the
    four destinations, `Report`, `aria-label="Primary"`, `hover:w-60`, `transition-[width]`, `md:hidden`,
    `fixed inset-x-0 bottom-0`, `safe-area-inset-bottom`, `grid-cols-5` and `Switch to dark theme` ✓.
  - **The data path still works after the rewrite** (through the Next proxy): `POST /posts` 201 →
    `POST /media` 201 with the blurHash → `GET /feed/new` shows the post with `media=1` → the signed URL
    serves `200 image/png` → `PUT /votes` 200 `up=1` → `DELETE /posts/{id}` **204** → the post is 404 —
    and the media **file** is gone from the volume, which is T-021's fix working in the live app ✓.
- notes (carried forward):
  - The header still shows the **"Postly" wordmark** and the alias / Report / theme controls. That is
    exactly **T-026** — it runs right after this task and moves them.
  - The hover expansion, the 768/375 px breakpoints and the safe-area padding are verified from the
    rendered classes and the SSR HTML, **not** from a real browser. The first person to open the app at
    768 px and at 375 px should eyeball it.
  - No dependency was added, so `package.json` and the lockfile are untouched ✓.
  - `next lint` prints a deprecation notice (Next 15 → 16). Harmless today, but the lint script should
    move to the ESLint CLI when the app moves to Next 16.
- environment left clean: 0 posts, 0 comments, 0 media rows, 0 files in the media volume, 1 pre-existing
  user and 1 pre-existing orphan vote (from the T-020 session — `Vote` has no FK; T-021 now sweeps it).
- next: **T-026** (the placement refinement the product owner asked for), then T-023.
