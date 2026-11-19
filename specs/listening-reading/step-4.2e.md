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
