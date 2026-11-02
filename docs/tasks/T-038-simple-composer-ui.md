# T-038 · The composer: drop a photo or write 300 words — nothing else

- status: ready
- quest: Q1
- depends: T-028, T-029
- owner: -
- updated: 2026-11-02 10:25
- files: apps/web/src/components/composer.tsx, apps/web/src/components/composer-dropzone.tsx, apps/web/src/components/area-picker.tsx, apps/web/src/components/feed-board.tsx, apps/web/src/lib/api/endpoints.ts, apps/web/src/lib/word-count.ts, docs/API.md

## Goal

The composer today asks for a **title, a body, a category and an area** — four fields, three dropdowns.
That is too much for someone standing on a broken street. It becomes **one box**:

- **Drop a photo** (or tap to pick one, or paste one) — or **write the text** — and post.
- The text is capped at **300 words** with a live counter.
- **No title field**: the server derives it (T-028).
- **No category picker**: the server detects it (T-028) and the app shows the guess as a chip.
- **No area picker**: the area comes from the resolution flow (T-029) and is shown as a chip the user can
  change in one tap.

One action: **post**.

## Done when

- [ ] The composer has **no** title input, **no** category select and **no** area select. The DOM contains
      exactly one text field (the body) plus the file input.
- [ ] A photo can be **dropped** onto the composer, **picked** with the file input and **pasted** from the
      clipboard; the drop target shows a visible "drop it here" state while a file is over it.
- [ ] The body is capped at **300 words**: the counter turns red past 300 and the post button is disabled;
      pasting more than 300 words is truncated (not silently rejected).
- [ ] The composer shows the **resolved area** as a chip (name + PIN) and the **detected category** as a
      chip; each can be changed in one tap (the area chip opens the area prompt, the category chip opens a
      small list of the 9 categories — an *override*, not the default path).
- [ ] Posting with only a photo (no text) works: the server derives the title and the category, the image
      is uploaded, and the post appears in the feed.
- [ ] Posting with only text works, and the same.
- [ ] The upload still happens **after** the post is created (`Media.post_id` is required) with the staged
      progress, and a failed photo upload leaves the post with a toast — unchanged from T-020.
- [ ] `npm run lint` → `✔ No ESLint warnings or errors`; `npm run typecheck` → exit 0; `npm run build` →
      `✓ Compiled successfully`; `npm run test:ghost` → all pass.
- [ ] The only `fetch(` under `apps/web/src/` is in `src/lib/api/client.ts`.

## Notes / gotchas

- **Do not remove `AreaPicker`** — it becomes the *override* behind the area chip, and the area prompt in
  T-029 needs it. It is the default flow that goes away, not the component.
- The word counter must agree with the server's counter (T-028): one shared definition of a "word"
  (whitespace separated). If the two drift, a user hits an unexplained `422 body_too_long`.
- Drag & drop needs `dragover` to be prevented (otherwise the browser opens the file) and the `drop` handler
  must read `event.dataTransfer.files`. Paste needs a `paste` listener on the text area
  (`event.clipboardData.files`).
- The photo types the API accepts: JPEG, PNG, WebP, MP4, MOV, 20 MB max (`docs/API.md` §9). The file
  input must use the same `accept` list.
- The composer is **post-first, then upload**: create the post with the derived/overridden category and the
  resolved area, then upload the photo with the same `owner_key`. Do not reorder this.
- The ghost identity and the per-post key are still created **before** the post (T-020) and the key is
  removed again if the create fails.
- The composer is opened from the rail, the mobile bar and the header — one dialog instance (T-022's
  `composer-provider`). Keep it that way.

## Research notes

- The API: `docs/API.md` §4 (posts) and §9 (media). The new body contract and the classify endpoint are
  **T-028**; the area resolution is **T-029**. This task is only the screen.
- The composer it replaces: `apps/web/src/components/composer.tsx` (T-020) and the provider split
  (T-022).

## Work log

## Report

## Manager review
