# Step 4.3b: timed Reading tests (spec, plan, tasks)

Plan: `plan.md` (CP4). Builds on `step-4.3.md`. Practice there is a learning mode: one question at a time, the answer
right after. A 7.0 target also needs exam conditions: a whole passage, all its questions, a clock, and no feedback until
the end. The serving rule is unchanged (approved and Silver, passage unchanged, checks pass).

## What the learner does
On a text page, **Làm bài thi (20 phút)** opens `/doc/{slug}/thi`:
- the passage (paragraphs numbered for headings) and every served question of the text, all on one page;
- a countdown from 20 minutes (IELTS gives about 20 minutes per passage); no right or wrong is shown before submitting;
- **Nộp bài** submits; at 0 the page submits by itself.

The result: **n/N correct**, then each question with the learner's answer, the key, the deciding sentences highlighted and
when it was answered (minutes into the test). No band score: nothing is calibrated against examiner marks (SPEC non-goal),
and the page says so.

## Rules
- **The server keeps the time.** A test records when it started; a submission after 20 minutes plus 30 seconds' grace is
  still graded but marked `over_time`, never refused (the learner's work is not thrown away).
- **Unanswered questions count as wrong in the score**, as in the exam, **but give no evidence**: a blank says nothing
  about the skill. Answered questions update the item's Reading competency exactly as practice does (the same code), once
  per question per test; each answer row records its `test_id`.
- **One submission per test.** A second submission is refused (409); the questions served are fixed when the test starts.

## Routes
- `POST /reading/texts/{slug}/tests` `{learner_id}` → `{test_id, slug, title, passage, items, limit_seconds,
  started_at}` (items in the learner's view, as practice; 404 when the text has no served question).
- `POST /reading/tests/{id}/submit` `{learner_id, answers: {item_id: {answer, at_seconds}}}` → `{correct, total,
  answered, over_time, seconds, items: [{id, answer, correct, key, evidence, at_seconds}]}`.

Migration `0032_reading_tests.sql` (additive): `reading_tests` (id, learner, text, item ids, started, submitted, score,
over time) and `reading_answers.test_id`.

## Tasks
- [x] T1 Migration, service (start, submit; practice's grading and evidence shared, not copied), routes.
- [x] T2 Web: the test page, timer, auto-submit, result; decoder, client, proxy rules, strings.
- [x] T3 Tests: API (one submission, blanks wrong but no evidence, over time flagged, only served items, other learners
  refused), Vitest (decoders, time formatting), Playwright (a mocked test answered, submitted, the result shown).
