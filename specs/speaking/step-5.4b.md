# Step 5.4b: guided practice (idea building, and the same question again)

Spec: `spec.md` ("Two modes", "Inside guided mode"). Owner's go-ahead: 28 Nov 2026 ("build 5.4"). The strict mock test is
step 5.4a; this is the other mode, `/noi/luyen`, owner only. **No model call, no band, no script written for the learner.**

## What the learner does
1. Picks a question from an authored test: a Part 1 question, the Part 2 cue card, or a Part 3 question.
2. **Idea building (Part 2 and Part 3 only), before speaking:** a *way to build an answer*, never an answer:
   - the shape: point → reason → example → link back to the question (Part 3 adds: compare, give the other side, say why it
     matters);
   - three questions that open the topic up (who, why, what changed, what if);
   - topic words from NodeTrail's word list, authored per cue card and per Part 3 theme.
   Then the learner speaks in their own words. Nothing is written for them to memorise.
3. Speaks (the question read aloud as in the strict test; Part 2 has a notes box and an optional minute to prepare on the first
   try), with a timer and nothing else on the screen.
4. Sees the answer's transcript, fluency numbers and language checks (steps 5.1–5.3a), and **the same question again**, up to
   three tries in all, with **the time shrinking**: 100% → 75% → 50% of the question's time (Part 2: 2:00, 1:30, 1:00; Part 3:
   60, 45, 30 s; Part 1: 40, 30, 20 s; the factors are assumptions, one constant each).
5. Each try's numbers sit **next to the others'** (speech rate, pauses per minute, longest fluent run, share of the time
   asked), as numbers, never arrows or a verdict.

## Rules
- **Only the first try counts as evidence of fluency** (`counts_as_evidence`); repeats are practice, because a rehearsed answer
  is not spontaneous speech. Nothing here moves mastery in any case (no consumer exists yet; the flag is for the owner's later
  N-of-1 report).
- The memorised-phrase check of Writing step 2.7 runs on every try's transcript (5.3a), so a learned script is named.
- Strict mode is unchanged: no hint while recording; guided practice shows its help *before* speaking, never during.
- Same voice policy: owner only, consent `speaking-v1`, audio cleared after 24 hours unless kept.

## How it is built
- **Migration 0050 (additive):** `speaking_tests.mode` (`exam` or `guided`), `question_id`, `try_no`, `practice_of` (the first
  try's sitting), `asked_seconds`. A try is a sitting with one answer, so the worker, the answer route and the pipeline are the
  existing ones; the strict test's list shows only `exam` sittings.
- **Authored words:** `words` on a cue card and on a Part 3 theme in `data/speaking/tests/*.yaml`; a test checks every word is in
  the word list.
- **API:** `POST /speaking/practice` starts a try (the question; optionally the previous try, to repeat), refusing a fourth;
  `GET /speaking/practice/{id}` returns the question, its tries with their answers (transcript, numbers, checks), the time
  allowed for the next one and the topic words. Answers and finishing use `/speaking/tests/{id}/answers` and `/finish`; an
  answer must be for the try's own question and within its shrunk time.
- **Web:** `/noi/luyen` (pick, ideas, speak, results with the side-by-side numbers, repeat); decoders; texts.

## What is measured
Unit tests: the shrink rule, the refusal of a fourth try and of a different question, the first-try flag, the numbers side by
side, the words in the word list. The browser: a whole try with the fake microphone, then a repeat with less time. The
technique's effect (answers reach the time asked, pauses fall between the first and third try) is an N-of-1 check on the owner's
own data, **not claimed** here.

## Not claimed
That repeating raises fluency or any band (Bronze until measured); that the idea shape or the words suit every question; a score.

## Tasks
- [x] T1 Migration 0050; authored words; the service (start, answer limits, practice view, overview); tests
- [x] T2 API routes; the proxy; tests
- [x] T3 `/noi/luyen`: pick, ideas, speak, results with numbers side by side, repeat; decoders; Vitest; Playwright
- [x] T4 Run for real; docs

## Built (28 Nov 2026)
- Migration `0050_speaking_guided.sql`; `try_seconds` and `MAX_TRIES` in `app/speaking/tests.py`; `words` on every cue card and Part 3
  theme in the five tests (each in the word list: a test checks); `start_practice`, `practice` and the guided limits in
  `app/services/speaking_tests.py`; `POST /speaking/practice`, `GET /speaking/practice/{id}`; web `lib/speaking/practice.ts`,
  `components/speaking/practice-page.tsx` and `practice-view.tsx`, `/noi/luyen` and `/noi/luyen/{id}`, a nav link.
- **Choices made in building:** a try is a sitting of mode `guided`, so nothing in the worker changed; a repeat needs the previous
  try to have an answer; the repeats keep the first try's "keep" choice; the Part 2 minute to prepare is only before the first try
  (skippable); the idea shape and the three opening questions are one text for all questions (Part 3 adds three steps), only the
  topic words are authored per cue card and theme; the strict test's list shows only strict sittings; the page polls up to two
  minutes for the transcript and numbers because the worker is a separate process.
- **Run for real** (Whisper small.en, worker, API): three tries of one Part 3 question with 60, 45 and 30 s, a fourth refused, the
  numbers per try side by side. **The three clips were unrelated synthetic speech, so the numbers show the plumbing, not any
  effect of repeating.** A browser test with the fake microphone ran a whole session (ideas, speaking with no help on screen,
  two repeats, delete) and another checked the side-by-side table on a mocked response.
- **Checks:** 14 new Python tests (the shrink rule, the words in the word list, three tries and never a fourth, a try takes only
  its question within its shrunk time, Part 2 and Part 1 content, the lists and deletion), 8 Vitest, 3 Playwright.
- **Not measured:** whether repeating raises fluency (the owner's N-of-1 data over weeks); whether the shape, the opening
  questions and the words help (the owner's use); the 100/75/50% shrink and the minute of preparation against the real test.
