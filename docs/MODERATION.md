# MODERATION

Flagged content is **blurred behind a warning**, and the reader decides whether to look. That is the
product promise: the community decides what it wants to see, and the app refuses to shove anything
unseen at anyone.

## 1. Provider chain

One interface, four implementations. `MODERATION_CHAIN` picks the order (`rules,openai,local-hf`).

```python
class ModerationProvider(Protocol):
    async def check_text(self, text: str, *, lang: str | None = None) -> ModerationResult: ...
    async def check_image(self, path: Path) -> ModerationResult: ...
    async def check_video(self, path: Path) -> ModerationResult: ...
```

| Provider | Model / source | Cost | Notes |
|---|---|---|---|
| `rule` | regex + lexicons | free, offline | abuse words (EN + Hindi/Hinglish), PII leaks (phone/email/Aadhaar), spam heuristics, caps, link spam. Always first. |
| `openai` | `omni-moderation-latest` | **free endpoint**, needs `OPENAI_API_KEY` | text **and** image. Categories include `harassment`, `hate` (caste-aware), `illicit`, `self-harm`, `sexual`, `violence`, `violence/graphic`. Images ≤ 20 MB, sent as base64 data URLs because our media is local disk. |
| `local-hf` | `KoalaAI/Text-Moderation` (deberta, trained to mirror OpenAI's category set), `unitary/toxic-bert`, `facebook/roberta-hate-speech-dynabench-r4-target`, `unitary/multilingual-toxic-xlm-roberta` (Hindi/other), `Falconsai/nsfw_image_detection` (ViT, 85M params) | free, offline | runs in a **separate worker process**, never in the request path. Needs `transformers` + `torch` (extra install). |
| `llm` | any OpenAI-compatible endpoint (Ollama local, or a hosted free tier), LangChain chain with structured JSON output | free if self-hosted | slot for the custom AI API the owner will provide later |
| `null` | none | free | local dev without models |

**Language routing:** English → `KoalaAI` / `toxic-bert`. Hindi and other languages →
`unitary/multilingual-toxic-xlm-roberta`. Honest limitation: free local classifiers are weak on Indian
languages, so Hindi leans on the OpenAI endpoint when a key exists; without a key, Hindi hits the local
model + Hindi lexicon with lower confidence, which means **more "send to review", fewer automatic blurs**.

**Video:** sample up to 10 frames (ffmpeg) and run the image model on each; take the max score.

## 2. Normalised result

```python
ModerationResult(
    categories: dict[str, float],   # category → 0..1 score
    severity: Literal["none", "low", "medium", "high"],
    provider: str,
    model: str,
)
```

## 3. Policy matrix

A single "NSFW" boolean is wrong for a civic app: a photo of a burst pipe or an accident is graphic but is
exactly what people need to see. So categories map to different actions.

| Category | Examples here | Severity | Action |
|---|---|---|---|
| `abuse` / `harassment` | abusive language, personal attacks | medium | blur + warning, "Accept & show" |
| `hate` | casteist slurs, communal abuse | medium → high | blur + warning; high ⇒ server-side redaction |
| `threat` | threats of violence | high | server-side redaction + report to moderators |
| `sexual` | explicit imagery | medium | blur + warning + reveal record |
| `graphic` | accident, injury, gore | low ("sensitive") | blur with a mild warning — allowed to be revealed |
| `pii` | phone number, email, Aadhaar, full address in the body | medium | blur the offending span + notify the author |
| `spam` | promo, crypto/ML ads, repeated caps, link farms | low | hide from feeds, throttle the author |
| `self_harm` | self-harm content | high | redaction + moderation queue |

The local `Falconsai` model only outputs `normal`/`nsfw`, so its hits are treated as **sensitive** (route to
review), never as a hard "sexual" verdict. OpenAI's `sexual` vs `violence/graphic` split is what enables
the precise policy above.

Scores are signals, not verdicts. Thresholds live in config and are tuned against a small labelled sample
in Q2 — never auto-delete on a single model's opinion. Everything above `medium` goes to the human queue.

## 4. Blur + reveal flow

1. Server moderates on write (post, comment, media) and stores `moderationState` on the target plus a
   `ModerationRecord` audit row.
2. The API returns `moderation_state` and `flags` with the content.
3. The client renders a **blurred teaser** — CSS blur for text, the stored `blurHash` as the placeholder for
   images — with a warning banner:
   > *This post contains content that may be abusive or inappropriate. Accept & show to continue.*
4. The reader clicks **Accept & show** → `POST /reveals` → the server stores `UserReveal(userId, targetType,
   targetId)`.
5. The reveal is permanent **for that user** (survives reload and other devices). The client also caches it
   locally so the reveal is instant next time.
6. Media originals are only reachable through the signed-URL route, which applies the same reveal check.

## 5. Reports and the admin queue

- `POST /reports` on a post, comment or media. Reason codes + optional details.
- `GET /admin/moderation` lists flagged content and open reports.
- Actions: keep, remove, warn the author, ban the user, unban, restore.
- Every admin action is recorded (`ModerationRecord.reviewedBy`, `reviewedAt`).
- Banning is by `User` — only registered and pseudonymous users can be banned. Ghost content is handled by
  removing the content and tightening limits; there is no ghost to ban, by design.

## 6. Where the checks run

| Target | When | Blocking? |
|---|---|---|
| Post title/body | on create and on edit | yes — the post is created with `moderationState` already set |
| Comment body | on create and on edit | yes |
| Image | on upload | no — the media row is created, then moderated asynchronously; the feed shows a placeholder until it resolves |
| Video | on upload | no — frames sampled asynchronously |

Heavy models run in the worker process. The API stays responsive.

## 7. Configuration

```env
MODERATION_CHAIN=rules,openai,local-hf
OPENAI_API_KEY=
HF_MODEL_TEXT=KoalaAI/Text-Moderation
HF_MODEL_IMAGE=Falconsai/nsfw_image_detection
HF_MODEL_MULTILINGUAL=unitary/multilingual-toxic-xlm-roberta
```
Threshold values live in `backend/app/core/config.py` and are versioned with the code.
