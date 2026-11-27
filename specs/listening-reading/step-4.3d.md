# Step 4.3d (plan CP4b first): feedback on a Reading test you took outside the app

Owner's idea and decision, 22 Nov 2026: the learner takes a real Reading test outside the app (a Cambridge IELTS book, an
official sample test), pastes it with the official answer key and their own answers, and gets feedback on every wrong answer and
vocabulary cards from the passage. The owner judged this more useful for exam preparation than the generated bank, so it comes
**first** in CP4b, before explanations for the bank's own questions. The bank stays, as the source of drills by question type and of
Listening's passages; reviewing it becomes optional (when more drills are wanted), not daily work.

## What the learner does (`/doc/bai-cua-ban`, from a card on `/doc`)
1. Pastes three blocks: **the passage** (one passage; a full test is pasted passage by passage), **the questions**, and **the answer
   key** (as printed, e.g. `1 TRUE 2 NOT GIVEN 3 C 4 river`), then types or pastes **their own answers** the same way.
2. Checks the questions the app read back: number, type, wording, options, key. Fixes or removes any it read wrongly. Nothing is
   marked until the learner confirms the list.
3. Sees the result: their score n/N, then each question with their answer, the key, and for a wrong answer the explanation.
4. Picks the words to keep from the passage's vocabulary list; they become review cards.

## Scope of the first version (owner's decision)
- **Question types:** True/False/Not Given and Yes/No/Not Given; multiple choice (one answer); short answer and sentence/summary/note
  completion (typed words). **Later:** matching headings, matching information/features, multiple answers, diagram labels. A pasted
  question of a later type is listed as "chưa hỗ trợ" and left out of the score, never guessed.
- One passage at a time, up to about 1,500 words and 14 questions.

## How it works
- **Reading the paste (one model call, then code):** the model turns the questions and the key into a structured list (number,
  type, wording, options, key, the word limit of a completion such as "NO MORE THAN TWO WORDS"). Code then checks it: numbers
  run in order and match the key's; each key is valid for its type (TRUE/FALSE/NOT GIVEN, an option letter that exists, a completion
  key within its word limit); every question's wording appears in the pasted questions. Anything that fails is shown to the learner
  as "không đọc được, sửa giúp" instead of being guessed. The learner's answers are parsed by **code**, not the model.
- **Marking (code, the official key is the truth):** T/F/NG exact; multiple choice by letter; completion exact after the same
  normalisation as the bank (case, spacing, accepted spellings the key lists with "/"), and over the word limit is wrong, as in the
  exam. The official key is Gold; no model decides right or wrong.
- **Explanations (one model call per wrong answer, budgeted):** the deciding sentence quoted from the passage, why the key is
  right, and the trap the learner's answer fell into, from **CP4b's closed list** (`spec.md`: T/F/NG pairs named by code;
  multiple-choice traps such as `word_match`, `partly_true`, `wrong_part`, `opposite`, `not_stated`, `outside_knowledge`,
  `extreme`; completion traps named by code). Code checks every quote is in the passage, the trap is on the list and allowed for the
  type, and the text is Vietnamese apart from quotes. Labelled **"Giải thích tự động, chưa kiểm chứng"**: the blind check by another
  family (Gemini, as decided for Writing 2.11c) comes later, after its planted test.
- **The summary across tests:** per question type and per trap, how many wrong out of how many, over the learner's pasted tests,
  with exact intervals once there are enough; "Hôm nay" may later suggest bank drills of the weakest type.
- **Vocabulary:** from the passage, the words in NGSL/NAWL above the learner's level (from the level test, else B1), plus the words of
  the deciding sentences of wrong answers; each shown with its passage sentence. Kept words become FSRS cards with that sentence as
  the example (a gap-fill on the sentence). Words outside our lists are listed with no definition, or with a model gloss marked
  "bản nháp", never presented as checked.
- **Evidence (owner's decision):** each marked answer is one BKT observation on its Reading competency (the same mapping as the bank's
  question types), counted once per question, never again if the same test is pasted twice (a fingerprint of the passage and the
  key). A blank gives no evidence.

## Rules
- **Copyright and privacy:** a pasted test is the learner's own material for personal study. It is stored only with that
  learner's submission (`reading_own_tests`, migration in the build step), deletable, never in the shared bank, the item files or any
  other learner's view, and never committed. The passage is sent to the model provider, so the consent notice applies, as for essays.
- **Progress study apart:** a test used for the 4-weekly progress study is recorded there as a score only (`app.progress.cli`).
  Pasting it here as well gives feedback, but the app's evidence and the progress study's measurement stay separate; the page says
  so when the learner marks a test as a progress test.
- **Budget:** owner-only while it uses the model (like Writing's feedback); the parse is one call and each wrong answer one call, all
  in `llm_calls` and under the daily limits.

## Not claimed
Whether naming the trap raises later accuracy is a hypothesis (CP4b), not a promise. The model's parse can be wrong; the learner's
confirmation is what makes the list usable. Explanations are unchecked until the blind check exists.

## Position and pacing (part 2; owner's approval, 27 Nov 2026)
A wrong answer late in a test may mean the learner ran out of time, not that a skill is weak (from the owner's research on
cognitive diagnosis, Bronze). Code only, no model call:
- **On the check step**, the learner gives the passage's place in the test (1, 2 or 3) and may mark any question **"đoán"**
  (guessed) or **"không kịp"** (ran out of time). Both marks are optional. The question's number is already known.
- **Evidence:** an answer marked "không kịp" gives **no BKT observation**, like a blank (a rule added to `SPEC.md`,
  "Evidence"). An answer marked "đoán" still counts, because a guess is how the exam is answered too. Its trap is shown, but left
  out of the trap counts in the summary.
- **The pacing line in the summary across tests:** from 3 pasted tests with passage 3 among them, code compares the share wrong
  on passage 3 and on the last third of each passage's questions against the rest. When it is at least 20 points higher **and**
  at least half of those wrong answers are blank or carry a mark, the summary says "Có thể do thời gian, chưa chắc là yếu kỹ năng (n/N câu
  cuối sai, m đánh dấu không kịp/đoán)". Otherwise it shows the counts only.
- **Not claimed:** passage 3 is also the hardest passage in IELTS, so late errors mix difficulty and time. The learner's marks are
  what separate them, and they are self-report (Bronze). The 20-point and "half marked" thresholds are assumptions, labelled so.
- `reading_own_answers` gains nullable `position` (the passage's place), `mark` (`guessed` | `no_time`) and `blank` in an additive
  migration (`0041`).
- **Built 27 Nov 2026 (pacing and the summary; vocabulary cards still to come):** `app/reading/own_summary.py` (pure: per type,
  the share right with an exact 95% interval from 5 answers, the top trap; the pacing status `not_enough` | `maybe_time` |
  `counts_only`), `GET /reading/own-tests/summary`, the position and mark choices on the check step, the summary panel on
  `/doc/bai-cua-ban`. One choice made while building: **every marked question now gets a row the first time its test is
  pasted**, blank and "không kịp" ones too (with no evidence), so the summary sees them. A test pasted again therefore counts
  nothing new, even for a question left blank the first time; the learner saw the key after the first paste, so a second answer
  is not an unseen one. Measured: unit and API tests, Vitest, a Playwright test with a mocked API. Not measured: whether the
  thresholds suit real tests (there are none yet).

## Build order
1. **Paste, parse, confirm, mark, explain** (API, page, migration, tests; Playwright with a fake model).
2. **Vocabulary cards and the summary across tests**, with position and pacing (above), and the per-skill lines once
   `step-4.3e.md` part 1 has tags.
3. Later: headings and matching types; the blind check of explanations (Gemini, planted test first); "Hôm nay" drills from the
   weakest type.

## Part 1 built (23 Nov 2026)
`app/reading/own_test.py` (pure), `app/services/reading_own.py`, `app/api/reading_own.py` (`/reading/own-tests`), migration
`0040` (`reading_own_tests`, `reading_own_answers`), the worker job, web `/doc/bai-cua-ban` (`components/reading/own-test.tsx`,
`lib/reading/own.ts`) with a card on `/doc`. Owners only; consent `reading-own-v1`. Model tasks `reading_own_parse` and
`reading_own_explain` (DeepSeek, through the gateway and the daily limits). Three choices made while building, for the owner to
confirm or change:
- **The key is read by code, not by the model.** The model only lists the questions (number, type, wording, options, word
  limit); code reads the printed key with the same numbered-list reader as the learner's answers and attaches it by number. A
  key the learner fixes on the check step must appear in the pasted key. Completion keys accept `/` variants and `(optional)`
  words, as Cambridge keys print them.
- **Competency per question type** (an assumption until a teacher maps types): T/F/NG, multiple choice and completion move
  `reading-detail`; Y/N/NG moves `reading-writers-view`. Evidence is guarded by the test's fingerprint (passage and key), so a
  test pasted again, even after deleting the first copy, gives no second observation. `reading_own_answers` keeps no passage or
  answer text.
- **A check step that still finds a problem** keeps the learner's edits and sends them back with the reasons, unmarked, instead
  of refusing; a blank answer is explained too (why the key is right), with no trap.

Measured: unit and API tests with a scripted model (parse, marks, traps, a dropped explanation, the fingerprint guard,
budget and no-model failures). **Not measured:** how often the real model reads a real Cambridge paste correctly, or how many
explanations pass code's checks; the owner's first real tests give that (Bronze). No blind check of explanations yet.

