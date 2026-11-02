# T-026 · App shell refinement: centred rail, user / night mode / Report on the left, no app name

- status: ready
- quest: Q1
- depends: T-022
- owner: -
- updated: 2026-11-02 09:05
- files: apps/web/src/app/**, apps/web/src/components/**, apps/web/src/lib/**

## Goal

T-022 builds the shell (left rail that expands on hover, mobile tab bar, black/red/white theme). This task
fixes **where things sit**:

1. The **nav items are in the middle** of the left rail — vertically centred, not pinned to the top.
2. The **user (alias) chip, the night-mode switch and the Report button live in the left rail**, not in the
   top bar of the page.
3. The **"Postly" app name is gone** — no wordmark in the header, no title above the nav. The brand is
   carried by the red mark alone; the document title may keep the name.

On a phone there is no rail, so the same three controls need a home: the alias and the night-mode switch in
the mobile top bar, the Report action in the bottom tab bar (Instagram style).

## Done when

- [ ] At ≥ 768 px the four destinations sit **vertically centred** in the rail (the block is centred in the
      rail's height, not below the logo), and the user / night-mode / Report controls sit **in the rail**.
- [ ] The desktop page has **no top bar**: no alias chip, no night-mode switch and no Report button above
      the feed.
- [ ] The word **"Postly"** appears **nowhere in the visible UI** — no wordmark in the header, no label
      next to the mark, no caption in the rail (the `<title>` in `layout.tsx` may keep it).
- [ ] Below 768 px the alias chip and the night-mode switch are in the mobile top bar and the Report action
      is in the bottom tab bar; the rail is hidden.
- [ ] The night-mode switch really toggles the theme (the `.dark` class on `<html>` flips and the palette
      follows) and the choice survives a reload.
- [ ] The alias chip still rotates the anonymous alias (the existing behaviour from T-020).
- [ ] The Report action still opens the **one** composer dialog (no duplicate dialogs).
- [ ] `npm run lint` → `✔ No ESLint warnings or errors`; `npm run typecheck` → exit 0; `npm run build` →
      `✓ Compiled successfully`.
- [ ] The only `fetch(` under `apps/web/src/` is in `src/lib/api/client.ts`.

## Notes / gotchas

- This task runs **after T-022** and edits the same files — do not start it while T-022 is in progress.
- The rail expands on hover: the controls that move into it must be reachable in **both** states (the
  collapsed 64 px rail and the expanded ≥ 240 px rail). Icon-only when collapsed, icon + label when
  expanded — the same pattern as the nav items.
- The night-mode switch must not flicker on hydration: `next-themes` resolves the theme after mount, so
  render a placeholder until `mounted` is true (the standard `useTheme` guard).
- The alias chip calls `ensureGhostIdentity()` / `rotateGhostAlias()` from `~/lib/identity` — keep using
  them; the secret never leaves the device.
- "Remove the app name" means the **visible UI**, not the document title, the package name or the repo.
- `cn` is a tailwind-merge clone: a later class wins over an earlier conflicting one, so `className`
  overrides on the shadcn components behave as expected.

## Research notes

- The shell T-022 builds is described in `docs/tasks/T-022-frontend-shell-nav-and-theme.md`; read it first.
- The identity helpers: `apps/web/src/lib/identity.ts` and `apps/web/src/lib/ghost/` (T-012, T-020).
- The theme tokens live in `apps/web/src/styles/globals.css`.

## Work log

## Report

## Manager review
