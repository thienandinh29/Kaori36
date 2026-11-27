# Step M5: today's plan with progress, and the week's study days

The owner's request (27 Nov 2026), after comparing NodeTrail's home page with another IELTS app: show how much of today's
list is done, roughly how long each activity takes, and which days of this week had any study. The owner asked about a
streak; it stays a non-goal (`SPEC.md`). This step shows **days with study as a calendar, never a count of days in a row**.

## What
1. **Today's plan is fixed for the day.** The first `GET /today` of a learner's day (midnight to midnight, Vietnam time,
   as for new words) runs the engine as before and stores the list in `today_plans` (migration `0043`, one row per
   learner and day). Every later call that day returns the same activities, so the list can be ticked off instead of
   changing under the learner. The next day gets a new list. `minutes` matters only on the first call of the day.
2. **Done, from today's answers only.** Each activity gets `done: true|false`, computed on every call from what the
   learner did since the start of today. Rules (pure function `app/services/today_plan.py`, `is_done`):
   - `review` of words or saved phrases: the learner has answered at least as many reviews of that list today as were
     due when the plan was made, at most one session (20);
   - a vocabulary band: 10 answers today on words of that band (B2 words do not tick B1);
   - a grammar node: 5 answers on the node today; a milestone: 5 answers on its hidden nodes;
   - a pronunciation sound group: one recording today;
   - a Writing competency (diagnostic or practice): one essay submitted today;
   - a Reading or Listening competency: 3 answers in that competency today (the engine's `MIN_EVIDENCE`).
   The thresholds are assumptions ("a short sitting"), not measured. They never touch mastery.
3. **Minutes, an estimate.** Each activity carries `minutes`: reviews about 15 seconds a card (at least 2, at most 10),
   a vocabulary band 5, a grammar node 10, a sound group 5, Writing 20 for Task 1 and 40 otherwise (a Task 2 essay), Reading 20, Listening 15. Shown
   as "khoảng N phút". The response also says `done_count` of the list's length.
4. **The week (`GET /today/week`).** Monday to Sunday of the current week in Vietnam time; for each day, how many answers
   the learner saved (vocabulary and phrase reviews, grammar answers, Reading and Listening answers, pasted
   Reading answers, essays, recordings, said words) and whether it is a study day (at least one). Plus `studied_days`.
   Read-only: no table, from the timestamps already stored. Delayed re-checks (FORGET-001) are left out: only the study
   code reads their table.

## What the learner sees (home page)
- Under the greeting, a row Thứ 2 … CN: a filled mark on days with study, an empty ring on past days without, a dot
  on days still to come, today outlined; "Tuần này: 3/7 ngày có học". Text and shape, never colour alone.
- "Hôm nay": "1/4 đã xong" next to the title; each item shows "khoảng 10 phút" and, when done, "Đã xong".
- **No streak, no praise, no fire.** Nothing says how many days in a row, nothing is lost by missing a day, and Sena
  says nothing about the calendar (the praise rule stays: mastery only).

## What is not claimed
- A study day means "an answer was saved", not "learnt something". Recordings not kept are deleted after 24 hours and a
  deleted essay disappears, so past days may show fewer answers than were given.
- Done is "practised today", not "mastered". Minutes are rough estimates; nobody measured them.

## Tests
Unit tests for `is_done`, `estimate_minutes` and the week's days (Vietnam midnight, Monday start); API tests: the plan is
fixed within the day and new the next day, an activity turns done after enough answers, the week counts answers from
several tables; Vitest for decoding; Playwright: the week row and the plan's count on the home page.
