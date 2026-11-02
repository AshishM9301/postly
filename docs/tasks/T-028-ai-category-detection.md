# T-028 · AI-assisted posts: the category is detected, the title is derived, 300 words max

- status: ready
- quest: Q1
- depends: T-015, T-019
- owner: -
- updated: 2026-11-02 10:25
- files: backend/app/providers/classifier/**, backend/app/schemas/post.py, backend/app/services/categories.py, backend/app/api/v1/posts.py, backend/app/api/v1/categories.py, backend/app/core/config.py, backend/tests/test_classification.py, .env.example, docs/API.md

## Goal

Today a post needs a **title, a body, a category and an area** — four decisions before anyone can report a
pothole. This task removes the two that a machine can do better:

- **The category is detected** from the text (and later the photo). A small LLM does it when an API key is
  configured; a deterministic keyword heuristic is the always-available fallback, so the feature never
  depends on the network.
- **The title is derived** from the body when the caller does not send one.
- **The body is capped at 300 words**, enforced by the server, not only by the client.

The client may still send `category_id` and `title` — they stay optional, not forbidden.

## Done when

- [ ] `POST /api/v1/posts` **without** `category_id` succeeds and the post lands in the right category.
      Proved offline, with the LLM provider switched off:
      "there has been no water supply since morning" → **Water Supply** ·
      "the streetlight at the corner has been dead for a week" → **Streetlight** ·
      "garbage has not been picked up for three days" → **Garbage** ·
      "a deep pothole in front of the gate" → **Pothole** ·
      anything unclear → **Other**.
- [ ] `POST /api/v1/posts` **without** `title` succeeds and the stored title is derived from the body
      (one line, trimmed).
- [ ] A body of **more than 300 words** is refused with **422 `body_too_long`** (words = whitespace
      separated tokens; the count and the limit come from one shared helper).
- [ ] A post **with** `category_id` and `title` still behaves exactly as before (no behaviour change for
      the existing clients).
- [ ] `POST /api/v1/posts/classify` with `{ "text": "…" }` returns the guessed category
      (`{ category_id, category_name, confidence }`) so the app can show the guess before posting.
- [ ] **The fallback works and is fast.** With `OPENAI_API_KEY` unset the classification is the local
      heuristic; with the provider stubbed to hang, the request still answers within **2 seconds** and the
      post is created. No test may touch the network.
- [ ] The LLM provider is only used when `OPENAI_API_KEY` is set; the key is read from the server
      environment and **never** reaches the client.
- [ ] `docker compose exec -T api python -m pytest -q` → all pass (the new tests included);
      `docker compose exec -T api ruff check app tests` → `All checks passed!`;
      `docker compose exec -T api ruff format --check app tests` → `NN files already formatted`.
- [ ] `docs/API.md` states the new body contract (title optional, category optional, 300-word cap,
      `body_too_long`) and the classify endpoint; `.env.example` lists the new setting with an empty value.

## Notes / gotchas

- The **9 seeded categories** are the whole vocabulary: `pothole`, `water`, `garbage`, `electricity`,
  `roads`, `streetlight`, `noise`, `drainage`, `other` (`backend/scripts/seed_categories.py`). The
  classifier must map to these ids — never invent a category.
- Follow the **provider pattern** the moderation work will use (`app/providers/…` + a registry), but do
  not build the moderation side: this task only classifies. Keep the interface small:
  `classify_category(text: str) -> Classification` with `category_slug`, `confidence` and `source`
  (`"llm" | "heuristic"`).
- The heuristic must cover Hindi/Hinglish words too (`pothole`, `paani`, `ghar`, `saafai`, `bijli`,
  `road`, `lamp`) — the app is Delhi-first and most of the text will not be English.
- The LLM call must have a **hard timeout** (~2 s) and must never make post creation fail: on any error
  or timeout, fall back to the heuristic and record `source: "heuristic"`.
- The prompt must be **English instructions with the category list**, and the model must be asked to
  answer with the slug only — parse it defensively (strip whitespace/quotes, take the first token,
  fall back to `other`).
- `PostCreate` has `extra="forbid"`-style validation? Check `backend/app/schemas/post.py` before making
  `title`/`category_id` optional — the response model must stay an explicit allow-list.
- **Never log the body** of a post in the classification path (it is user content). Log the slug and the
  source only.
- The 300-word cap counts **words**, not characters. Put the counter in one place both the server and the
  client can agree on, and document it.

## Research notes

- The post contract today: `docs/API.md` §4. The category list: `backend/scripts/seed_categories.py`.
- The moderation work (T-030 … T-034) will add its own providers; keep the registry shape compatible so
  the two do not fight later.
- The OpenAI key is already a documented setting (`OPENAI_API_KEY`) for the moderation provider — reuse
  the same variable, do not add a second one.
- **The model to use is not researched yet.** Before coding, pick a small chat model, check that the name
  is a stable (non-preview) id, and record the model name, the date and the reason in this task's
  `## Research notes`. Do not re-derive it later.

## Work log

## Report

## Manager review
