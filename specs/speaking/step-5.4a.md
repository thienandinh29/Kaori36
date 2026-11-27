# Step 5.4a: the examiner test (a full mock with a voice examiner, before transcription)

Spec: `spec.md` (Two modes: "Thi thử"; step 5.4). Owner's go-ahead: 27 Nov 2026, after a Speaking app the owner saw (a full
mock test, then a result page). This step builds the test itself and nothing that needs the recogniser, so it can run before
the recogniser is chosen (5.1). Transcripts, measures and feedback attach to the same answers later (5.1–5.3).

## What the learner does (`/noi/thi`, owner only)
1. Consent (`voice-v1`, as on `/phat-am`), a microphone check (the phase 3 quality check on a 3-second sample), and one
   choice: keep the recordings past 24 hours or not.
2. **Part 1 (about 4–5 minutes):** the examiner's voice greets, then asks three topics of about four questions each. Each
   answer is recorded on its own. The learner taps "Xong" to move on; after 40 seconds the examiner moves on anyway, as real
   examiners cut long Part 1 answers (the limit is an assumption, set in one constant).
3. **Part 2:** the cue card on screen and read aloud; one minute to prepare, with a notes box (kept only in the browser);
   "you have one to two minutes"; recording stops at 2:00; then one closing question.
4. **Part 3 (about 4–5 minutes):** four to six discussion questions on the Part 2 topic, 60 seconds each before the examiner
   moves on.
5. **While speaking:** a timer, a recording dot, nothing else: no hint, no text of the answer, no score (strict mode).
6. **After the test:** each question with its recording to replay, and "Nghe lại cả bài" (all answers in order with the
   examiner's questions between them). Then "Thi lại" (another test) and the list of past tests.

## Why a fixed script, not a chatbot
IELTS examiners follow a set script, so a script is closer to the exam than a model inventing questions. It also needs no
live transcription: on CPU the measured recogniser runs at about 0.46 × real time (`docs/v2/asr-candidates.md`), too slow to
answer within a few seconds. The next question plays at once.

## The questions
- Authored files, `data/speaking/tests/*.yaml`: one test per file, Part 1 topics with their questions, one cue card (the
  topic, the bullet points, the closing question), the Part 3 questions. Each file carries `status: draft` and its author.
- Common topics only (home, study, work, technology, places, people, events). Never questions copied from past papers or
  "forecast" lists (`SPEC.md`, sources).
- First set: the agent drafts five tests for the owner to edit; they stay "Bản nháp" until a teacher reads a sample
  (`specs/validation/`). Part 1 questions within a test do not repeat a topic of another part.

## How it is built
- **Voice:** the existing Piper service through `/speech` (compose profile `speech`). The examiner's lines are cached as
  audio once per test. Without the voice service the page says so and shows the questions as text, with the same timing.
- **Recording:** the browser records 16 kHz mono WAV as on `/phat-am`, one file per answer.
- **Storage (migration, additive):** `speaking_tests` (learner, test file and its hash, started, finished, keep) and
  `speaking_answers` (test, part, question id, question text, audio, seconds, recorded_at, delete_after). Audio follows the
  voice policy: deleted after 24 hours unless kept; owner only; a deletion job clears expired audio as for recordings.
- **API:** `GET /speaking/tests` (the authored tests, the learner's past tests), `POST /speaking/tests` (start),
  `POST /speaking/tests/{id}/answers` (one answer), `POST /speaking/tests/{id}/finish`, `GET /speaking/tests/{id}` and
  `GET /speaking/answers/{id}/audio`. Every route owner-only (`DRAFT_ITEM_LEARNERS`), behind the API key.
- **No model call, no evidence:** nothing in this step moves mastery or calls a model. Measures and feedback come in 5.2–5.3.
- **Texts:** all UI text in `apps/web/messages/` (Vietnamese first); the examiner speaks English.

## What is measured
Only that it runs: a Playwright test at phone size with a fake microphone (the whole flow, timing shortened by a test
setting), API tests against a real database (owner-only, 24-hour deletion, keep), unit tests for the timing rules and the
test file loader. Whether the test feels like the exam is the owner's judgement after two full tests (Bronze).

## Not claimed
That the script, the timing or the cut-offs match the real test exactly; any score or band (`spec.md`, "The band": a level
only after SPK-001); that a machine voice prepares the learner for a human examiner's accent.

## Tasks
- [x] T1 Test file format, loader and checks (unit tests); five draft tests for the owner to edit
- [x] T2 Migration `0043` and the service for sittings and answers; retention and owner-only rules (database tests)
- [x] T3 API routes (API tests)
- [x] T4 The page `/noi/thi` and the result `/noi/thi/{id}`: consent, microphone check, the three parts with timing, replay, past tests (Vitest for the script and timing)
- [x] T5 Playwright test at phone size; `MAP.md`, `PLAN.md`, `SPEC.md` feature 9 status, `dolater.md`

## Built (27 Nov 2026)
- `data/speaking/tests/t01`–`t05` (drafts); `apps/api/app/speaking/tests.py` (format, ids, limits); migration
  `0043_speaking_tests.sql` (`speaking_tests`, `speaking_answers`); `app/services/speaking_tests.py` and
  `app/api/speaking.py`; the worker clears expired audio with the recordings' purge.
- Web: `lib/speaking/exam.ts` (decoders, the examiner's script in NodeTrail's own wording, timing),
  `components/speaking/` (voice, recorder, page, result), `app/noi/thi/`.
- **Choices made in building, for the owner to confirm:** a bad recording (too quiet, no speech) is still stored, since an
  exam answer is what it is, and the result says why it may be hard to hear; the voice falls back from the server voice
  to the browser's English voice to text on screen; Part 3 allows 60 seconds and the closing question 30 (assumptions,
  `PART3_SECONDS`, `CLOSING_SECONDS`); the examiner never repeats a question (one could be added).
- **Checked:** 14 API tests (loader, owner rule, consent, limits, once per question, 24-hour clearing, deletion),
  10 Vitest, 2 Playwright with the fake microphone (a whole test of 18 answers, timing shortened by the test-only speed
  setting `nodetrail_exam_speed`; the owner rule). The browser suite ran on the API, worker and web run natively with
  the database in Docker, because image builds in the cloud sandbox cannot reach the package registries; CI builds the
  images. Not checked: a real test at real speed with a real microphone and the server voice (the owner's two tests).
