# Step 4.2b: generated Reading questions, code checks and the blind check (plan CP2a)

Part of `specs/listening-reading/` (`plan.md`, CP2). It fills the 4.2a schema with generated questions. Nothing is served:
every item waits for the owner's review (CP3). The planted-error test that decides whether the checker can be trusted on
Reading items is CP2b.

## Pipeline, run offline (CLI, never in a request)
`uv run python -m app.reading.pipeline [bank folder] [--only <slug>] [--max-checks N]`
1. **Texts.** Only texts the bank admits are used, so their source is verified. During development the private folder is
   read with `--unverified`, and nothing from it is committed.
2. **Generation** (gateway task `reading_items`, DeepSeek). Per text:
   - two T/F/NG statements, one of them `not_given`;
   - one multiple-choice item;
   - one completion item;
   - one headings item when the text has 3 or more paragraphs.

   Every item quotes the passage sentences it rests on, and is tagged with a skill. The output is JSON validated
   against the 4.2a schema; ids are assigned by code, never by the model.
3. **Code checks** (`items.check`): evidence quoted exactly, completion answers in the passage, no key leaked into the
   stem, valid paragraphs. A failing item is stored as `dropped`, with its problems, and never spends a check.
4. **Blind check** (gateway task `reading_check`: free Ernie, dots as backup). It runs inside a `verification_scope`
   naming DeepSeek, so the checker is never the generator's family.
   - **What it sees:** only the passage and the learner's view of the question. No key and no evidence.
   - **How it is graded:** its answer goes through `items.grade`, the same function that will grade learners.
   - **Outcome:** full marks gives `verified`. A wrong answer or an unusable reply gives `needs_review`, with its answer
     kept for the review page.
5. **Budget.** The free checker allows 50 requests a day. `--max-checks` (default 40) stops the run before that limit;
   items not yet checked stay `generated` and the next run continues with them.

## Storage (migration `0024_reading_items.sql`, additive)
`reading_items`:
- the item id, the text slug, and the SHA-256 of the passage, so an edited text invalidates its items;
- the kind, the item JSON and the status (`generated`, `dropped`, `needs_review`, `verified`, `approved`, `rejected`);
- the problems, the checker's answer and model, and timestamps.

`approved` and `rejected` are set only by the owner (CP3).

## Gateway
`reading_check` joins `lesson_check` as a verification task and a task allowed on free models, for the same reason: it
sees only public, openly licensed passages and generated questions, never learner data. `reading_items` is routed to
DeepSeek in both tiers.

## Not in this step
The planted-error test (CP2b), the review page (CP3), serving anything to a learner.
