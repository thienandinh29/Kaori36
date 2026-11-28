# Step 5.3: grammar and vocabulary checks on the transcript (5.3a, no model call)

Spec: `spec.md` ("Checks before any feedback", "Grammar and vocabulary on the transcript"). Owner's go-ahead: 28 Nov 2026.
**Split in two, and only the first half is built here.** 5.3a is code: the Writing pipeline's own tools run on the transcript, on
our own machines, so nothing leaves NodeTrail and no consent wording is needed. 5.3b (feedback written by a model, with quotes
checked against the transcript) sends the transcript to a model provider and waits on the owner's consent wording
(`PLAN.md`, decisions waiting on the owner). Nothing in 5.3 moves mastery: grammar flags on speech are hints, never evidence.

## What the learner sees
On the result page, under an answer's transcript and numbers, only when the answer has at least 15 s of speech (shorter answers
keep their numbers and get no language feedback, as the spec proposes):
1. **Memorised or repeated text first**, as for essays: phrases from the memorised-phrase list found in the answer, words in a
   repeated run, and a warning when almost none of the question's own words are used. A warning, never a judgement.
2. **Grammar hints**, each with the quoted words, LanguageTool's suggestion and a button that plays the audio at that moment.
   Labelled "gợi ý, có thể sai": spoken grammar is not written grammar, and the recogniser may have mis-heard.
   A missing ending (the suggestion only adds -s, -es, -ed or -d to the word) is shown apart as **"có thể thiếu đuôi -s/-ed"**,
   never as a grammar error: Vietnamese speakers often drop final /s/, /z/, /t/, /d/ as a sound, so it may be pronunciation,
   grammar or the recogniser.
3. **Vocabulary numbers:** lexical diversity (MTLD, only from 50 words), the share of words above B1, words the word list does
   not know, and the content words repeated most.

## How it is built
- `app/speaking/language.py` (pure, tested): hint kinds and the ending rule, offsets to seconds, vocabulary numbers, the guard
  fields, the 15 s gate. It reuses `app/writing/grammar.analyse_grammar` (LanguageTool matches typed by ERRANT; the error map's
  nodes are ignored), `descriptor_features.mtld` and `word_levels`, `guardrails.check`.
- **What is dropped:** spelling, casing and punctuation matches (the recogniser decides those, not the learner), and filler words
  before the vocabulary numbers. Only GRAMMAR and CONFUSED_WORDS matches become hints.
- **Migration 0049 (additive):** `speaking_answers.language jsonb`, `language_at`.
- **Worker:** after the measures, in the same step, with the grammar step the worker already loads (spaCy, ERRANT, LanguageTool);
  an answer measured earlier is checked while its audio is still there. LanguageTool unreachable: retried later. Any other
  failure: stored as failed, not retried in a loop. Without `LANGUAGETOOL_URL` there are no hints (marked "chưa kiểm tra"), and
  the vocabulary numbers and the guard still run.
- **API and web:** the stored `language` on each answer; strict decoders; the three blocks above; Vietnamese texts.

## What is measured
Unit tests: the ending rule, the hint kinds and what is dropped, offsets to seconds, fillers out of the vocabulary numbers,
the 15 s gate, no mastery change. The worker step and the API against a real database with a scripted LanguageTool. A run with
the real spaCy and ERRANT, and (if the image is available here) the real LanguageTool. **Not measured:** how many hints are
false alarms and how many errors the recogniser hid: that is the owner's 20 typed references and a judgement of each flag
(`spec.md`, "Grammar and vocabulary on the transcript"). Until then the hints are labelled as possibly wrong.

## Not claimed
That a hint is an error; that no error was missed (the recogniser "corrects" learner speech about 1 in 5, `docs/v2/asr-candidates.md`);
anything about pronunciation; a score or a band.

## Tasks
- [x] T1 `language.py` with tests
- [x] T2 Migration 0049; the worker step; the API result; tests
- [x] T3 The page: decoders, the three blocks, play-from-here, texts; Vitest; a Playwright test on a mocked result
- [x] T4 Run for real; docs
- [x] 5.3b built 28 Nov in `step-5.3b.md` (owner's go; the consent wording is still a draft the owner must set)

## Built (28 Nov 2026)
- `app/speaking/language.py`; migration `0049_speaking_language.sql`; `transcribe.process_next` takes a `LanguageStep` (the Writing
  grammar step's parser, ERRANT and LanguageTool, the word list, the memorised-phrase list), `worker.transcriber` builds it from
  the grammar step the worker already loads; the result's per-answer `language`; web decoders and `exam-result.tsx`.
- **Choices made in building:** only GRAMMAR and CONFUSED_WORDS matches become hints (spelling, casing and punctuation are the
  recogniser's); the repeated content words use spaCy's function-word list, not Writing's stop list (it contains "people", which
  every IELTS prompt says: found on the real run, where "people" ×6 was missing); a short answer (under 15 s of speech) gets
  `skipped: short`; the guard and the vocabulary run even without LanguageTool, the hints then read "chưa kiểm tra".
- **Run for real** (Whisper small.en, spaCy, the real word list and phrase list, through the worker and API; **LanguageTool not
  run**: its image cannot be built in this sandbox): a 10 s answer was skipped, a 25 s answer found the memorised phrase "in this
  day and age", gave MTLD 34 over 65 words, 0% above B1, 8% unknown, "people" ×6. The hints themselves were tested with a scripted
  LanguageTool and the real parser and ERRANT (20 unit tests, 3 worker tests, 1 Playwright on a mocked result).
- **Not measured:** how many hints are false alarms and how many errors the recogniser hid; the real LanguageTool on speech.
