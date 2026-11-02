# T-022 · Frontend shell: left nav rail, mobile tab bar, black/red/white theme

- status: ready
- quest: Q1
- depends: T-020
- owner: -
- updated: 2026-11-02 08:50
- files: apps/web/src/app/**, apps/web/src/components/**, apps/web/src/lib/**, apps/web/src/styles/globals.css

## Goal

The app should look like a real posting app, not a bare page. On the desktop there is a **nav rail on the
left** — collapsed to icons, expanding to labels on hover. On a phone the same destinations move to a
**bottom tab bar**, the way Instagram does it. The whole palette is **black, red and white**: red is the
only accent, the surfaces are black or white, the text is the opposite of its surface.

The nav and the feed tabs must be **one state**: clicking *Trending* in the rail switches the feed to
Trending, and so does clicking the *Trending* tab — no page reload, no second source of truth.

## Done when

- [ ] `curl http://localhost:3000` → the SSR HTML contains the brand and the four destinations
      (For You / Trending / New / Nearby) and the Report action.
- [ ] At ≥ 768 px the rail is **fixed on the left**, collapsed to ≈ 64 px and **expanding to ≥ 240 px on
      hover** (a CSS width transition on the rail itself, labels fading in with it).
- [ ] Below 768 px the rail is **hidden** and a **bottom tab bar** is visible, fixed to the bottom, with
      the same four destinations plus the Report action; the last card in the feed is not covered by it
      (bottom padding on the content column).
- [ ] The rail, the bottom bar and the tab strip read **one** tab state — switching in any of them
      switches the feed everywhere (a single context, not three copies of the state).
- [ ] The palette is black / red / white: `--primary` is the same red in `:root` and `.dark`, the
      background is white in light mode and black in dark mode, and no other hue is introduced
      (`grep` `globals.css` for the colour tokens).
- [ ] A theme toggle switches light/dark and the choice survives a reload.
- [ ] The Report action opens the **same** composer from the rail, the bottom bar and the header (one
      dialog instance, not three).
- [ ] `npm run lint` → `✔ No ESLint warnings or errors`; `npm run typecheck` → exit 0; `npm run build` →
      `✓ Compiled successfully`.
- [ ] The only `fetch(` under `apps/web/src/` is in `src/lib/api/client.ts` (the ESLint rule enforces it).

## Notes / gotchas

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

## Report

## Manager review
