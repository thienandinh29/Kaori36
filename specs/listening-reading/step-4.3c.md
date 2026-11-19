# Step 4.3c: the shown order, and checks that reach the laptop (spec, plan, tasks)

A fix inside steps 4.2b–4.3b, found on 19 Nov 2026 by reading the bank of 291 generated questions.

## What was wrong
1. **The order gave answers away.** Questions were shown in the order the generator wrote them.
   - In multiple choice, the key was B in 35 of 68 questions (A 18, C 12, D 3). Always answering B scored about 51%,
     against 25% by chance.
   - In matching headings, the list often followed the paragraphs. In 6 of 18 questions every heading sat at its own
     paragraph's number, and in 3 more most did. Answering 1, 2, 3, … scored 73 of 119 paragraphs (61%).
   - The blind checker was shown the same order. Its agreement on these kinds therefore partly measured the order,
     not the passage. Two "verified" headings questions were fully in order.
2. **The learner's headings key was numbered from 0** while the page numbers paragraphs and headings from 1.
3. **Checks never reached the laptop.** Import added missing rows only. A question imported while waiting for its
   blind check kept `generated` for ever on the owner's laptop, never appeared on `/duyet-doc`, and so could never be
   approved.

## The rules
- **One shown order.** Every surface shows `items.presented(item)`: learners (practice and timed tests), the owner's
  review page, the expert portal and the blind checker.
  - Options and headings are shuffled uniformly, with the order fixed per item id. The same question always looks the
    same, and the key lands in each position equally often.
  - A uniform shuffle is used rather than one that keeps every heading away from its paragraph's number, because that
    rule would itself be a hint.
  - Stored items are unchanged, so item files, labels and approvals stay valid.
- **One stored meaning.** Every recorded answer is kept in the stored order (`items.to_stored`): learner answers in
  `reading_answers`, the checker's answer, and an expert's option letter. Typed answers are kept as typed. Anything
  that is not a valid position stays wrong.
- **Code refuses options that point at other options** ("both A and B", "all of the above"), since they break once
  shuffled. None are in the bank today.
- **Checks are done again in the shown order.**
  - Migration `0033` records which order the checker saw (`check_view`: null for the stored order, `shuffled`).
  - Each pipeline run first re-checks undecided multiple-choice and headings questions whose check saw the stored
    order: 13 and 7 in the bank today, 20 of a day's 50 free checks. Then it checks new questions.
  - An unusable reply leaves the earlier check standing until a usable one replaces it.
  - A question the owner already decided is not re-checked. Its decision stands.
- **Import brings newer checks.** An undecided row (`generated`, `verified`, `needs_review`) on the same passage
  version takes a file's check when the file's is newer. A decided row is never touched, as before.
- **The learner's headings key reads as the page does:** "1: 4, 2: 2, 3: 1" (paragraph: heading, from 1). The owner's
  page numbers both from 0, as before, and so does the checker's prompt.

## Seen, not fixed here
NOT GIVEN is the key in 26 of 123 T/F/NG questions (21%; TRUE 52, FALSE 45). Nothing leaks, but the hardest
judgement is practised least. A balance rule in the generation prompt can follow; it needs new generation.

## Tasks
- [x] T1 `items.presented`, `to_stored`, `to_presented`; the code check on option references.
- [x] T2 Practice, timed tests, review page, expert portal and checker use the shown order. The checker's answer is
  kept in the stored order, and the review page reads it against the shown order.
- [x] T3 Migration `0033_reading_check_view.sql`; the re-check first in `check_pending`; `check_view` in the item file;
  import brings newer checks.
- [x] T4 Tests:
  - the key's spread and chance-level headings on synthetic items;
  - round trips and invalid answers;
  - the checker shown the shuffled order, with stored-order answers kept;
  - the re-check, including unusable replies and decided rows;
  - import of newer checks, never over a decision;
  - practice and timed tests answered in the shown order and kept in the stored order;
  - the review page and the portal;
  - the whole-bank simulation.
- [ ] T5 (the next daily batch) The 20 re-checks run. The owner's laptop imports the batch's file, and the earlier
  verdicts on those questions are replaced.
