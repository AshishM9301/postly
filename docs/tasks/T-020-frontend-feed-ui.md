# T-020 · Frontend: feed UI, post card, composer, vote buttons

- status: ready
- quest: Q1
- depends: T-015, T-019
- owner: -
- updated: -
- files: apps/web/app/**, apps/web/components/**, apps/web/lib/**

## Goal

Make the app look like the product: a feed with four tabs, a post card with a photo, vote buttons that
update immediately, and a composer that lets someone report a problem from their phone in under a minute.

## Done when

- [ ] The home page shows the four tabs (For You / Trending / New / Nearby) and switches between them.
- [ ] A post card shows: author alias, area name, category, time ago, title, body, photo, vote counts,
      comment count, status badge.
- [ ] Upvote/downvote buttons update the count immediately (optimistic) and reconcile with the server
      response; the "my vote" state is shown.
- [ ] The composer validates the title/body, requires an area, uploads a photo with a progress state, and
      shows a blurHash placeholder while the image loads.
- [ ] Area selection offers the three paths: type a PIN, search by name, "use my location" (browser GPS).
      If the user denies GPS, the PIN/search path still works.
- [ ] The app looks acceptable on a 375 px-wide phone screen.
- [ ] `npm run lint`, `npm run typecheck`, `npm run build` pass.
- [ ] The client only talks to the API through `lib/api/client.ts` — no raw `fetch` in components.

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

Record the shadcn init command and the component list you added to this task's `## Research notes` so later
frontend tasks reuse the same set.

## Work log

## Report

## Manager review
