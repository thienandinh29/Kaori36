# Step 5.3b: the model's written feedback on an answer, quotes checked by code

Spec: `spec.md` ("Pipeline", "Limits and privacy"); `step-5.3.md` (5.3a, the checks by code). Owner's go-ahead: 28 Nov 2026
("build 5.3b"). **The consent wording is the owner's decision and is not settled** (`dolater.md`): this step is built with a
**draft** notice, shown as "Bản nháp", and for the owner's own tests only (the owner's question "may the owner's own tests use it
first"; testers are not offered it). Nothing is sent to a model provider unless the learner presses a button after reading the notice.

## What the learner does
On the result page of a sitting, under an answer that has a transcript and at least 15 s of speech, a button **"Nhận xét bằng AI"**.
First use: read the notice (what is sent, to whom, how long it is kept) and tick it. Then the answer's feedback is made by the worker
and appears under the answer, labelled **"gợi ý từ AI, dựa trên bản máy chép lại, có thể sai"**:
- up to 5 short points in Vietnamese, each a **strength** or an **issue**, in one area: the answer (did it answer the question, a
  reason, an example), grammar, vocabulary or linking;
- every point shows **the words quoted from the transcript**, and an issue about grammar or vocabulary also shows a more natural
  way to say it in English;
- nothing about pronunciation, pace or pauses (the model never hears the audio; those are the numbers above), no band, no score.

## Rules
- **The model sees only the transcript** and the question (never the audio, never a name). Its feedback is written to the learner, not
  to a score: **no band, no number, never evidence, never mastery.**
- **Every quote is an exact substring of the transcript** (NFC, whitespace and curly quotes folded), at least 3 words. A point whose
  quote is not found is dropped; if no point survives, the learner is told so and nothing is shown as feedback.
- **The recogniser is not the learner.** Spelling, casing, punctuation and a missing -s/-ed ending (which may be the recogniser or
  the sound) are never points: the prompt says so and code drops an issue whose "better way" only adds an ending. A point that
  talks about a band or a score is dropped.
- **Owner only for now; one call per answer** (the learner may ask again after a failure, at most 3 tries per answer). Every call goes
  through the gateway as task `speaking_feedback`, is checked against the daily cost cap and the learner's call limit and logged in
  `llm_calls`.
- The notice version is stored with the request (`speaking-feedback-v1`). The transcript is sent only on that request.

## How it is built
- **Migration 0052 (additive):** on `speaking_answers`: `feedback_status` (`queued`, `working`, `done`, `failed`), `feedback`,
  `feedback_consent`, `feedback_requested_at`, `feedback_at`, `feedback_tries`.
- `app/speaking/feedback.py` (pure, tested): the prompt, the output schema, the quote check and the other drop rules.
  `app/speaking/feedback_job.py`: the worker step (claims one queued answer, calls the model outside any open transaction, stores
  the checked points or the failure; a stopped worker's `working` rows are queued again at start).
- `routing.yaml`: task `speaking_feedback` on the free tier (DeepSeek, as Writing). No second model family verifies it: like
  Writing's feedback it is explanation, not generated test content; the quote check is the guard.
- **API:** `POST /speaking/answers/{id}/feedback` (body: the notice version) queues it; the result and practice views carry
  `feedback` on each answer. **Web:** the button, the notice, the points with their quotes, the states (waiting, failed, none found).

## What is measured
Unit tests: the quote check (exact, folded, too short, absent), the drop rules (ending-only, band talk, no "better" on a grammar
issue), the prompt carries only the transcript and the question. API and worker against a real database with a scripted model:
queued, done, failed, over budget, no model configured, owner only, wrong notice version, too short, three tries. A run for real with
the real model through the gateway on a synthetic transcript (cost-capped). **Not measured:** whether the points are right or useful
(the owner's judgement of 20 points, `dolater.md`); whether the model misses errors the recogniser hid.

## Not claimed
That a point is correct; that no error was missed; anything about fluency or pronunciation; a score. The draft notice is not legal advice.

## Tasks
- [x] T1 `feedback.py` with tests
- [x] T2 Migration 0052; the worker step; routing; tests
- [x] T3 The service and route; tests
- [x] T4 The page: button, notice, points; decoders; Vitest; Playwright on a mocked result
- [x] T5 Run for real; docs

## Built (28 Nov 2026)
- Migration `0052_speaking_feedback.sql`; `app/speaking/feedback.py` (prompt, schema, quote check, drop rules) and
  `feedback_job.py` (the worker step, `requeue_stuck`); task `speaking_feedback` in `routing.yaml`; `SpeakingTests.request_feedback`,
  `feedback_state` and the `feedback` on every answer of the result and practice views; `POST` and `GET
  /speaking/answers/{id}/feedback`; web `components/speaking/answer-feedback.tsx`, `parseFeedback`, the proxy path, texts.
- **Choices made in building:** the model returns points with one quote each (not up to three); an issue about grammar or vocabulary
  must carry a "better way" and a strength must not; a point that mentions a band (`band`, `/9`) is dropped; a "better way" that
  only adds -s/-ed to the quoted words is dropped; at most 5 points are kept; `can_ask` is false for testers, for answers under 15 s
  of speech and after 3 tries; the worker step is the same worker process (no new service) and reuses the Writing model wrapper
  (budget, per-learner call limit, `llm_calls`); the notice is shown the first time the button is pressed on each answer and its
  version is stored with the request.
- **Run for real** (API, database, the worker step, DeepSeek through the gateway) on a **synthetic transcript** with planted mistakes:
  asked without the notice 422, asked with it 202, the step stored 4 checked points (two real grammar errors with their corrections,
  nothing about pronunciation, no band), one call logged in `llm_calls` (715 tokens in, 329 out, US$0.002 at the deliberately high
  default prices). A separate live test (`test_feedback_live.py`, skipped unless `WRITING_LIVE_LLM=1`) kept 5 of 5 points.
- **Checks:** 10 unit tests (the quote check and each drop rule), 7 flow tests against a real database with a scripted model (owner
  only, notice, 15 s gate, three tries, budget, no model, an unexpected failure, stuck work, no mastery change, the polling read), 3
  Vitest, 1 Playwright on a mocked result (nothing is sent before the notice is ticked).
- **Not measured:** whether the points are right and useful (the owner's judgement of 20 points, `dolater.md`); how many real errors
  it misses, especially those the recogniser hid; the cost on real answers. No blind check by a second model family yet.
