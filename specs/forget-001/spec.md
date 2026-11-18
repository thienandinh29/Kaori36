# FORGET-001: data collection and analysis (spec, plan, tasks)

Experiment: `research/experiments/FORGET-001.yaml`. The question: what is forgotten after about a week, and does the
model know it? This step builds what the experiment needs, so data collects while the owner studies. **No result is
claimed until the experiment's minimum is reached:** about 4 weeks, at least 200 delayed vocabulary reviews, and enough
grammar re-checks for an interval worth reading.

## 1. Vocabulary: replay and calibration (offline, no new data)
`app/studies/forget.py` (pure, tested) replays every card's answers in `vocab_reviews`, in order, through
`app/engine/srs.py`, exactly as the vocabulary service did:
- a new card at the first answer, then `review(correct)` at each answer;
- **before** each review after the first, FSRS's predicted recall at that moment;
- the outcome: whether the answer was correct.

Its report gives:
- **Calibration by decile** of predicted recall: the mean predicted value against the actual recall share, with an
  exact interval;
- the **expected calibration error**, the Brier score and the log loss, next to a constant baseline. The constant is
  the overall recall share, which is fitted in-sample and said so;
- the same for the **"after a week" subset**: reviews 5 to 10 days after the previous one;
- **retention by category** for delayed reviews: CEFR level, item kind and topic, each with an exact interval;
- the words with the lowest delayed retention (at least 3 delayed reviews each);
- a `minimum_met` flag against the experiment's minimum, so an early report is labelled as such.

Not here: the counterfactual against fixed intervals (question 3). It needs FSRS parameters fitted to the learner,
which is a later step once data exists.

## 2. Grammar: delayed re-checks (new data)
BKT has no forgetting. A node marked "known" (p ≥ 0.9) may have been forgotten a week later, so the app asks.
- **Which nodes:** grammar nodes known at p ≥ 0.9 whose last evidence (`mastery.updated_at`) was at least 5 days
  ago, and which have had no re-check in the last 28 days. The oldest evidence goes first. At most **3 re-checks are
  created per rolling 7 days**, the rate the experiment asked for.
- **Which item:** one for that node that the learner may see (the same draft rule as practice). Items never answered
  come first, then the least recently answered.
- **Stored apart, never as evidence:** the new table `grammar_rechecks` (migration `0029`) holds the node, the item,
  `p_known` when planned, the time of the last evidence, the answer and whether it was correct. A re-check **never
  changes mastery** and is not written to `grammar_answers`, so it measures the model without feeding it. A test
  keeps this table out of every other module.
- **Routes:**
  - `GET /rechecks/next?learner_id=` plans any due re-checks, then returns one open question (prompt and shuffled
    options), or none;
  - `POST /rechecks/{id}/answer` grades from the key and returns whether it was right, and the key.
- **Web:** a card on the home page, "Kiểm tra lại sau một tuần", showing one question when there is one. After the
  answer: right or wrong, and the correct option. Sena says nothing about speed or streaks.
- **Report**, in `app/studies/forget.py`: re-check accuracy with an exact interval, overall and by days since the
  last evidence (5–7, 8–14, 15+), against the hypothesis bar of 80%.

## Commands
```
uv run python -m app.studies.forget --learner <your id> [--out ../../data/private/forget-001.json]
```

## Tasks
- [x] T1 `app/studies/forget.py`: replay, calibration, retention, the re-check report; unit tests with
  hand-checked numbers.
- [x] T2 Migration `0029_grammar_rechecks.sql`; `app/studies/recheck.py` (pure planning) with tests.
- [x] T3 `app/services/rechecks.py`, `app/api/rechecks.py`; database tests: planning, the cap, item choice, grading,
  mastery untouched; a separation test.
- [x] T4 Web: the home card, client, proxy rule, strings; Vitest and Playwright.
- [x] T5 CLI, MAP, `dolater.md`, the experiment's status set to `collecting`.
