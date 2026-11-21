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
- **The question's parts:** authored prompts store their parts in `prompts.yaml`. For an own question (step 2.10) the model
  proposes the parts and **the learner confirms them by ticking** before writing; nothing is inferred silently, and no
  extra Bronze label layer is added.

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
