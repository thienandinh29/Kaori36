# Step 4.2a: Reading question types, answer-key grading and code checks

Part of `specs/listening-reading/`. The half of step 4.2 that needs none of the owner's open decisions: **no model call, no key,
no dependency, no migration, no route.** Generation and blind verification (4.2b) need a verifier of a different family than
DeepSeek and wait for the owner's choice.

## Question types (`app/reading/items.py`)
One schema for authored and, later, generated items, so 4.2b only has to fill it.
- `tfng`: a statement; key `true | false | not_given`.
- `mcq`: a stem and 3–4 options; key is the option index.
- `completion`: a sentence with one `___`; `accepted` answers; `max_words` 1–3 (IELTS "NO MORE THAN n WORDS").
- `headings`: a list of headings and, per paragraph index, the key heading; more headings than paragraphs.
Common fields: `id`, `text` (bank slug), `skill` (`detail | main_idea | inference | writers_view | skimming`), `evidence` (passage
sentences the answer rests on), `origin` (`authored | generated`), `status` (`draft | needs_review | verified | approved`).

## What code checks against the passage (`check(item, passage)` returns the problems)
- Every evidence quote is an exact substring of the passage after NFC and whitespace normalisation (as for writing feedback).
  `tfng` with key `not_given` may have none (the point is that the text says nothing); every other item needs at least one.
- `completion`: each accepted answer appears word for word in the passage and in an evidence quote, and has at most
  `max_words` words; the stem does not already contain the answer next to the blank.
- `mcq`: options are distinct; the key option's text is not copied verbatim into the stem (a leak).
- `headings`: every paragraph index exists in the passage; key headings are distinct and listed.
An item with any problem is never served. **Only `approved` items are served** (`servable`); `approved` is the owner's mark
after review, and a generated item reaches it only through `verified` (4.2b).

## Grading (`grade(item, answer)`)
From the key only, never from a model: `tfng` accepts `true/false/not given` and the IELTS forms `T/F/NG`; `mcq` the index;
`completion` through `graders/typed.grade_typed` (exact after normalisation, misspelling wrong) and refused if over the word limit;
`headings` per paragraph, returning the share right. `learner_view(item)` strips keys, accepted answers and evidence.

## Acceptance
Unit tests per type: valid items pass `check`; each problem above is reported; grading of right, wrong, IELTS short forms,
word limit; the learner view leaks no key; only approved items are servable.
