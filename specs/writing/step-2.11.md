# Step 2.11: how good is the feedback? (stability, structure, checked claims, the real measure)

From an outside review of the feedback code (21 Nov 2026, Bronze) and the owner's adjustments the same day. The review found
the division of roles sound (tools find errors, the model finds what they missed and comments; quotes checked by code; AI
corrections never move mastery) and three gaps. This page holds all four items, in the order they are built; each later
item gets its own short build note here when it starts.

## 2.11a: stability of the feedback (built first)
**Question:** sent the same essay three times, does the model say the same things? If not, a learner cannot trust a point.
- **Data:** Task 2 essays published on the web (sample answers on IELTS preparation sites), stored only in git-ignored
  `data/private/writing/stability/essays.jsonl` (`id`, `question`, `text`, `source`). No band is needed, so sample
  essays are enough. Texts never leave `data/private/`; only metrics are committed.
- **Method:** `python -m app.evalkit.feedback_stability` sends each essay to the app's own feedback prompt (`feedback.SYSTEM`,
  the same measures the app sends, without LanguageTool's list) **3 times**, through the gateway, each call recorded in
  `llm_calls` with a cost cap per run. Every reply goes through `feedback.verify`, as in the app.
- **Same point:** two points from different runs are the same when they have the same criterion and kind and their quotes
  overlap (one contains the other after normalisation, or the words of the quotes overlap by at least half). The wording of
  the point is not compared: the quote is the evidence. Limit: two different problems in one quoted sentence count as one.
- **Measures, reported separately for "issue" and "strength" points** (strengths are often generic and repeat more easily):
  - per essay: of all points in the three runs, the share that appear in at least two runs, with an exact 95% interval;
  - per essay: the mean pairwise overlap of the runs' point sets (Jaccard);
  - across essays: the mean of the per-essay shares, with a bootstrap interval over essays; the list of per-essay values is
    in the report, never only the mean.
- **Decision rule, a proposal until the owner has seen a real result (owner, 21 Nov):** if under 60% of issue points appear
  in two of three runs, the app keeps only issues that recur across 2 of 3 runs (three calls per essay; owner use stays
  inside the daily limits); above that, one call. The report labels the bar `"status": "proposed"` and its outcome
  `proposed_decision`; nothing in the app changes until the owner decides.
- **Report:** `evals/writing/feedback-stability.json`, committed: essay ids and numbers only (runs, failed calls, word
  count, the stability figures), the model and the cost. No quote, point text, source URL or essay text; a unit test checks
  that none reaches it.
- **Pairs to check by eye:** a seeded sample of 10 matched pairs (issues first), each with both runs' points and quotes, in
  `data/private/writing/stability/matched-pairs.json`, never committed; the command refuses a path outside
  `data/private/`. The owner reads them to judge whether "same point" really means the same point.
- **Built 21 Nov 2026:** `app/evalkit/feedback_stability.py` (pure matching and scoring, unit-tested; the runner uses the
  gateway and records every call). **Pipeline check, not a measurement:** two short essays written for the check, 3 runs
  each with deepseek-flash: issues recurring in 2 of 3 runs 77% and 67% (exact intervals 55–92% and 38–88%), strengths
  93% and 88%; pairwise overlap of the issue sets only 0.52 and 0.38, so the two measures say different things and both
  are reported. 7 calls (1 retried), US$0.034 at the configured prices. Two essays decide nothing: the measurement needs
  about 20 web sample essays, which the cloud sandbox cannot fetch (its network blocks the sites), so they are collected
  on the owner's laptop (`dolater.md`).

## 2.11b: Task Response and Coherence get structure checks
- The model extracts the structure with quotes: the position (introduction and conclusion), each body paragraph's main idea,
  and which part of the question each paragraph answers. Quotes are checked by code as for feedback.
- Code then checks: **every part of the question is answered** and **the position is consistent** (introduction vs
  conclusion). Both are shown as findings with their quotes.
- **Development, not "an example":** a body paragraph that only asserts is flagged as **"có thể chưa được phát triển"**, a
  hint, never an error: IELTS rewards ideas that are developed and supported, and a band 7+ paragraph may develop its point
  by explanation alone. Development counts as an example **or** an explanation (a reason, a consequence, a contrast).
- **The question's parts:** authored prompts store their parts in `prompts.yaml`. For an own question (step 2.10) **code**
  proposes the parts from the question's wording and **the learner confirms them by ticking** before writing; nothing is
  inferred silently, and no extra Bronze label layer is added. (Owner's decision, 22 Nov 2026: code, not the model, because
  the question is checked inside a request, where a model call is long work and costs money before anything is written.)

### Build note (22 Nov 2026)
- **Parts.** `Prompt.parts` (`app/writing/prompts.py`): 1–4 per Task 2 prompt, required in the bank, at most one marked
  `position` (the writer's own view). The five authored Task 2 prompts have theirs (draft, like the prompts).
  `own_prompt.propose_parts` guesses them by type: both views and "your own opinion" (the views quoted from "Some people
  believe… while others think…" when the wording allows), advantages, disadvantages and "whether the advantages outweigh",
  causes or problems and solutions, "how far you agree or disagree", or each direct question ("Why…, and what…?" is two).
  `POST /writing/prompts/check` returns them; the learner unticks any that are wrong. `own_parts` on `POST /essays` and
  `POST /writing/tests` must be a non-empty subset of the proposal (422 otherwise), so only the learner's own question
  reaches the model, never typed text; stored in `essays.own_parts` and `writing_tests.own_parts` (migration 0039); an essay
  from before keeps every proposed part.
- **One more model call, separate from feedback** (owner's decision): task `writing_structure`, same gate as feedback
  (owners only, a model configured, budgeted, one `llm_calls` row per attempt), Task 2 only, and only with at least 3
  paragraphs (otherwise the result says why and nothing is called). The feedback prompt is unchanged, so 2.11a still
  measures the prompt in use. An essay now uses up to 3 calls: the free plan's 6 a day must be revisited before anyone but
  the owner gets model features.
- **What the model returns** (`app/writing/structure.py`): for the introduction and the conclusion a stance (`first`,
  `second`, `balanced`, `none`) with the quote stating it; for each body paragraph its number, the main idea quoted, the
  part numbers it answers, and its development (`example`, `explanation`, `none`) with a quote. Paragraphs are numbered by
  code (blank-line split), so each quote is checked **in its own paragraph**, not just somewhere in the essay.
- **The rules** (code, pure, unit-tested): a description whose quote fails is dropped (main idea) or treated as unknown
  (stance, development). A part is **missing** only when every body paragraph has a checked description and none answers
  it; otherwise it shows "chưa chắc". A position part is answered by a stated stance or a body paragraph; **no position** is
  an issue only when both introduction and conclusion say none. A **flip** is `first` against `second` (balanced against a
  side is not); both quotes are shown. **"Có thể chưa được phát triển"** is a hint for a body paragraph whose development
  is `none`; a claimed example or explanation whose quote fails gives no hint. Findings are Task Response; Coherence gets
  the outline of main ideas per paragraph, no finding yet.
- **Shown** on `/bai-viet/{id}` ("Cấu trúc bài: đã trả lời đủ đề chưa?") after the Task 1 checks: findings first, then the
  parts with answered / not seen / unsure, the two position quotes, and each body paragraph's main idea, parts and
  development. The parts are also listed under the question in the editor. Nothing here is evidence or enters "Sửa trước".
- **Not measured, not claimed.** How often the model's descriptions are right (a missed part that was there, a flip that
  was not) is not known; the findings are worded as things to reread. A precision figure needs essays labelled by a
  teacher, or 2.11c's blind check.
- **Live pipeline check, 22 Nov 2026** (`tests/writing/test_deepseek_live.py`, `WRITING_LIVE_LLM=1`, deepseek-flash, 2
  calls; a check that the pipeline works, not a precision figure): the essay that answers every part got no finding
  (stances first/first, development explanation and example); the essay without solutions got "part missing" for the
  solutions and "có thể chưa được phát triển" on its paragraph that only asserts, with nothing dropped.
- **Known limit (from the review, 22 Nov):** an own question's kept parts are stored as their texts and matched against
  what `propose_parts` proposes *now*. If those rules change later, an older essay's stored parts may no longer match, and
  its structure check is then skipped without a message when it is shown again. Storing each part with its `position` flag
  would remove the dependency; worth doing before `propose_parts` is changed.

## 2.11c: feedback claims checked blind by another model family
- For each "issue" point, a model of another family sees only the quote and the point and answers whether the quote shows
  the problem stated. Disagreement: the point is dropped or shown as "chưa chắc". This also gives a precision figure.
- **Planted test first:** feedback points with planted false claims (a correct sentence quoted as an error, a wrong
  criterion) and true ones; the check is used only when its catch rate and false alarms are measured, as for Reading.
- **Quota, decided here:** the checker is **Gemini** through the gateway's `verify` route (DeepSeek generates, Gemini
  checks: the families differ). The free OpenRouter checker stays reserved for Reading's daily batch (about 45 of its
  50 daily requests). Without a Gemini key the check does not run and the result says so; it never falls back to the
  generator's family.

## 2.11d: "Sửa trước" shows at most 3 items
`MAX_ITEMS` in `apps/web/lib/english/priorities.ts` from 5 to 3, as the review and the owner's research both suggest
focusing on a few errors. The full list stays folded below.

## The real measure for Writing: error rate per opportunity
Whether old errors fall in later essays is the measure that matters, not a band. Counting errors alone has a trap: a learner
can avoid the structure they get wrong (no more passives), and different questions invite different errors. So the tracker
(step 2.8) reports, per error type, **errors per opportunity** (for example article errors per noun phrase, agreement errors
per finite verb, tense errors per finite verb), always next to the essay's sentence complexity (clauses per sentence,
complex-sentence share, already measured). A falling rate with steady or rising complexity is progress; a falling count
with falling complexity is avoidance and is said so. The same idea as `repair.judge` ("deleting is not fixing"), at the
level of the whole essay.
