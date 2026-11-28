# Step 5.2: fluency measures from the audio and the word timings

Spec: `spec.md` ("Pipeline": "Pauses come from the raw audio", "Measures by code", "Where the pauses fall"). Owner's go-ahead:
28 Nov 2026. This step turns each transcribed answer of the examiner test into numbers about how it was spoken. **Numbers,
never a verdict:** no band, no "good" or "bad", no mastery, no model call.

## What the learner sees
On the result page (`/noi/thi/{id}`), under each answer's transcript, one line: speech rate (words a minute), pauses (how many,
how many between clauses and how many inside a clause, how many were long), filler words, and the longest run of words with no
pause. Above the answers, the same numbers pooled over the whole test. A note says the machine only counts: it does not know why
anyone paused, and a short answer gives shaky rates. Where an answer has no transcript, no line.

## The measures (by code, `app/speaking/measures.py`, pure and tested)
- **Pauses come from the raw audio**, found before any voice-activity filtering (the recogniser's filter removes the very
  silences these numbers need). A pause is a stretch of at least **0.5 s** of non-speech between speech, a long pause **2 s**
  (both assumptions, one constant each). Speech frames use the recording-quality check's own rule (30 ms frames, louder than
  the noise floor by 10 dB). Leading and trailing silence is not a pause.
- **Speaking time** runs from the first word's start to the last word's end (the transcript's timings). **Speech rate** is words
  over speaking time, a minute's worth. **Articulation rate** leaves the pauses out of the time.
- **Where a pause falls:** each pause is placed on the gap between two words (the last word that starts before the pause's
  middle), then called **between clauses** when a clause ends there or **inside a clause** when not. A new clause starts at a
  sentence start, a coordinating
  conjunction or subordinator that joins clauses, a relative or wh-word, or the left edge of a separate finite clause (a verb
  with its own subject, attached to another clause), all from a spaCy parse of the words. **The recogniser's punctuation is not
  used** (see "Built"). Approximate on purpose: Bronze until the owner has listened to a few answers and compared (`dolater.md`). Studies link inside-clause pauses
  to searching for a word or structure (Tavakoli 2011; de Jong and colleagues; to check), but the app shows two counts and
  never says why anyone paused.
- **Fillers:** um, umm, uh, uhm, er, erm, hmm, mm, counted from the transcript. "Like" and "you know" as fillers cannot be
  told by code and are not claimed. The recogniser may drop fillers: its counts are a floor.
- **Longest fluent run:** the most words between two pauses, with its length in seconds.
- **Answer length against the time asked:** speaking time over the question's time limit.
- **Short answers:** under 15 s of speaking is flagged `short`; its rates are shown with that warning (the spec's proposed
  minimum answer length).

## How it is built
- **Migration 0047 (additive):** `speaking_answers.measures jsonb`, `measured_at`.
- **Worker:** the audio is cleared after 24 hours, so the measures are made while it is there: in the same step as the
  transcript (the audio, the word timings, a spaCy parse), and by the same step for a transcript made before this step
  existed. `app/speaking/clauses.py` finds the clause boundaries; `app/speaking/measures.py` does the rest.
- **API:** each answer's `measures`, and a pooled `summary` over the answers that have them (total words over total speaking
  time; pauses summed). Owner only, as the rest.
- **Web:** decoders (strict), the line under each transcript, the summary, Vietnamese texts.

## What is measured
Unit tests on synthetic audio with known silences (tone bursts and gaps) and on word lists with known clause structure; the
worker step and the API against a real database; the page's decoders; a run on the real recogniser and speech here.
**Not claimed:** that a pause is a hesitation; that the clause boundaries match a linguist's; any number on the owner's voice
(the owner listens to five answers and checks); a score of any kind.

## Tasks
- [x] T1 `measures.py` (pauses from raw audio, rates, runs, fillers, placement) with tests
- [x] T2 `clauses.py` (boundaries from a spaCy parse of the words) with tests
- [x] T3 Migration 0047; the worker step; the API result and pooled summary; tests
- [x] T4 The page: decoders, the line, the summary, texts; Vitest; a Playwright test on a mocked result
- [x] T5 Run for real; docs

## Built (28 Nov 2026)
- `app/speaking/measures.py`, `clauses.py`; migration `0047_speaking_measures.sql`; `transcribe.process_next` measures in the
  same step as the transcript (or alone, for a transcript made earlier while its audio is still there); the result's
  per-answer `measures` and pooled `summary` (the time asked and the share of it come from the question, not the audio);
  web `lib/speaking/exam.ts` (decoders), `components/speaking/exam-result.tsx`.
- **Found on the real recogniser, and changed:** Whisper puts a full stop at a long pause ("I usually go to her. Mark it on
  Saturday…"), so counting punctuation as a clause end made a hesitation inside a clause look like a boundary: a pause
  decided its own class. The first version used punctuation; it was replaced by a parse of the words alone (no punctuation,
  fillers skipped). The cost: spaCy segments run-on speech poorly, so sentence ends without a conjunction are found only by
  the "separate finite clause" rule, and boundaries are missed.
- **Run for real** (Whisper small.en with the pinned weights, espeak speech, 1.4–1.6 s planted pauses, through the worker and
  the API): a pause after a sentence was "between clauses" and a pause in "go to the | market" was "inside a clause"; the
  fillers (Umm, uh) were counted; the pooled summary summed two answers. Synthetic speech, one voice, a handful of cases.
- **Checks:** 15 new Python tests (synthetic audio with known silences, placement, rates, clause rules, the worker step, the
  API), 4 Vitest, 1 Playwright on a mocked result.
- **Not measured:** the pause detector's thresholds on the owner's microphone and room; the clause split on spontaneous
  speech (the owner listens to five answers and compares: `dolater.md`); speed of the parse in the worker.
