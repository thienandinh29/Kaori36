# Step 4.2c: the owner's review queue for Reading questions (plan CP3)

Part of `specs/listening-reading/` (`plan.md`, CP3). Every generated question needs the owner's approval before a
learner sees it. This step gives the owner a page for that and measures how often the owner agrees with the checker.

## The page (`/duyet-doc`, owner only: the ids in `DRAFT_ITEM_LEARNERS`)
- **Filter:** `needs_review` (the default, since the checker disagreed), `verified`, `approved`, `rejected`. Counts per
  status are shown.
- **One question at a time:**
  - the passage, with the item's evidence sentences highlighted;
  - the question as a learner would see it;
  - the key, the checker's answer and the checker model;
  - the skill.
- **Decision:** **Duyệt** (approve) or **Loại** (reject), with an optional note.
  - A reject asks for a reason chosen from a short list: wrong key, not answerable from the passage, two defensible
    answers, unclear wording, other. The reason feeds the gate report.
  - The decision is stored with its time.
  - Approval is refused when the item no longer passes `items.check` or its passage changed (the SHA-256 differs).
- **Editing** is not in this step. A faulty item is rejected and the text is generated again later. An edit page would
  need its own code checks and a new blind check, so it comes with a later step if rejections show it is worth it.

## Routes (owner only; 403 for anyone else)
- `GET /reading/review?learner_id&status=` returns:
  - the counts;
  - up to 50 items of that status, each with its passage. The passage is `null` when the text is not in the folder,
    and approval is then refused.
- `POST /reading/review/{item_id}?learner_id` takes `{decision: approve|reject, reason?, note?}`. It returns 409 when
  the item is not `verified` or `needs_review`, and 422 when approval fails the checks above.

Passages are read from `reading_texts_dir` (default `data/english/texts`, the bank's folder). Serving to learners
(CP4) will also require the text to be admitted by the bank.

## Agreement with the checker (gate 2)
`uv run python -m app.reading.agreement --out ../../evals/baselines/reading-agreement.json`:
- **The pairs:** for every reviewed item, the checker's call (`verified` = good, `needs_review` = not good) against the
  owner's decision (approve = good, reject = not good).
- **The report:**
  - agreement, with an exact interval;
  - Cohen's kappa;
  - the confusion counts;
  - reject reasons.

The plan asks for at least 50 reviewed items; fewer are reported with a note.

## Not in this step
Editing items, serving them to learners (CP4), Listening.
