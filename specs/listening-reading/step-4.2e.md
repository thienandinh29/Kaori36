# Step 4.2e: the Reading bank at IELTS size (spec, plan, tasks)

Plan: `plan.md` (CP1, CP2a). The first bank (10 short texts, 49 questions) proved the path; the owner's target (7.0)
needs passages of exam length and enough questions to practise every day.

## What changes
- **Texts.** OpenStax passages of 500-900 words: whole paragraphs joined across a page's prose sections, author-date
  citations removed (an adaptation the ShareAlike licence allows). A chapter that already has a text in the bank is
  passed over, so a run never rewrites a text whose questions exist. `texts` in `data/english/text-picks.yaml` is
  the number of new texts a run adds.
- **Questions.** A passage of 450 words or more asks for 5 T/F/NG (one or two NOT GIVEN), 3 multiple choice,
  3 completion and headings with a different heading per paragraph: about an exam's worth. Short passages keep the
  first prompt. A run of underscores is one gap. A dropped item keeps what the model wrote.
- **Cost, measured.** Every model call of the offline pipeline is an `llm_calls` row (`app/reading/calls.py`); a run
  stops generating once its recorded cost reaches `--max-cost` (default US$0.50).
- **One fingerprint.** Generation, the review queue, the reviewer portal and practice hash the passage's NFC form.
- **Speed.** Text files are cached until they change; an answer checks only its own item. Found by the simulation.

## The simulation (`tests/reading/test_bank_simulation.py`)
Every bank text through fake generation (questions from the passage's own sentences, with deliberate defects), the
code checks, a fallible blind checker (wrong or unusable replies), the item file round trip, the owner's review, the
labels, the practice routes and "Hôm nay". It asserts: API and web number paragraphs alike; nothing is lost in the
item file; owner labels are not counted twice; no key reaches the learner; every served item grades right and wrong
answers correctly; items the owner approved alone, or approved against the checker, are never served. Weakening
the serving rule makes it fail.

## Results (19 Nov)
20 new texts (30 in the bank). 242 questions: 212 kept, 30 dropped by code (14 completion blanks, 8 repeated
headings, 7 without evidence, 1 answer not in the passage; the first two causes fixed for later runs). 30 model
calls, US$0.14 at the configured prices. The blind check runs about 45 a day (the free checker's limit), so the
rest are checked over the next days and the item files updated.

## Tasks
- [x] T1 Call log and cost cap; NFC fingerprint everywhere.
- [x] T2 Long passages, chapter skip, citations; the scaled prompt; blanks; drafts of drops kept.
- [x] T3 The simulation; the speed fixes it found; the missing Bronze test.
- [x] T4 Fetch and generate the 20 texts.
- [ ] T5 Blind-check the rest in daily batches; export after each.

## Cleaned passages (20 Nov 2026, found in the owner's review)
The owner rejected a headings question because two OpenStax "Link to Learning" captions ("PBS provides an
evolution series excerpt…", "This … simulator lets you examine…") had been kept as paragraphs, shifting the
paragraph numbers. A sweep of every class in the 30 source modules found **9 of 30 passages** carrying text that is
not part of the passage: link captions (`link-to-learning` notes; "Visit…", "Read the article…") and end-of-section
matter (summaries that repeat the body, "further research" links).
- `parse_module(..., drop_classes=...)` leaves out notes and sections by class; only the Reading fetch passes
  `NOT_PASSAGE` (link-to-learning, summaries, quizzes, questions, further research, references). Titled prose boxes
  ("Beyond the Book", "Sociology in the Real World") stay. Other callers keep everything, as before.
- `python -m app.texts.fetch clean [--write]` rereads each bank text's module at its pinned commit and removes only
  the paragraphs that come from those boxes and sections; nothing else in a passage moves (checked: removals only,
  in order, metadata unchanged). 9 texts, 2–4 paragraphs each, 15–116 words.
- **Question ids per passage version.** Ids were `{slug}-{kind}-{n}` with `on conflict do nothing`, so a changed
  passage's new questions were silently not stored and every run paid to generate them again. A text's first version
  keeps its ids; a later one is `{slug}-v{n}-{kind}-{n}` (tested).
- The old versions' questions stay in the files, never served or queued (their passage changed): 16 verified, 76
  unchecked, 17 dropped, and the owner's 1 rejection. New questions for the 9 cleaned passages: 106 kept, 5 dropped
  by code, waiting for the daily blind check (US$0.08 for 12 calls: 9 passages, 3 malformed replies retried).

