# Step 2.8 — A fix must repair the error; errors you repeat across essays

From the owner's deep research (20 Nov 2026, Bronze): in a classroom study of Write & Improve, 12.8% of "fixed"
highlights were cleared by deleting or changing the text without fixing the error; feedback transfers to new essays
mostly through revision across several drafts; learners ask for their recurring errors to be tracked across essays.

## 1. Repair check for "Tự sửa câu này" (`apps/api/app/writing/repair.py`, pure, tested)
The self-correction (step 2.4a) already accepts a sentence only when LanguageTool finds nothing in it and it is closer
to the minimal correction than the original was. That rule mostly refuses deletions, but a learner who deleted the
error was told only "chưa sửa đúng chỗ lỗi". Now the attempt is judged first:
- **deleted:** the sentence lost more than 40% of its other words, or it lost more words than the error had and the
  word before or after the error is gone. Not accepted, counted as a try; the page says to fix the error rather than
  remove it. (Changing the error wrongly, e.g. "go to" → "went", is not a deletion: the usual rule decides.)
- **unchanged:** the error span is still there word for word. Not accepted.
- otherwise the existing rule (LanguageTool clean and closer) decides, as before.
No table changes: the outcome is said in the correction's `feedback_vi` and logged.

## 2. Errors you repeat (`apps/api/app/writing/tracker.py`, pure, tested; `GET /essays/patterns`)
Across the learner's analysed essays in the last 90 days: LanguageTool errors (never AI suggestions) grouped by
grammar node (else ERRANT type). A group is a **pattern** when it appears in 2 or more essays. Per pattern: the number
of essays and errors, the essays it appeared in among the latest 3, the last example sentence, and the node's
practice link when it is a grammar node. At most 5, most essays first. Trend words only from counts ("vẫn còn trong
bài gần nhất" / "không có trong bài gần nhất"), never a judgement of progress: one essay is not evidence of learning.

Web: "Lỗi bạn hay lặp lại" on `/viet` above the essay list (shown from 2 analysed essays).

## Not changed
Mastery, evidence and bands. The tracker reads stored results only (no model call, no new table).

## Checks
pytest for `repair.py`, `tracker.py`, the correction route (deleted, unchanged) and the patterns route (privacy:
another learner's essays never count); Vitest for the decoder; Playwright for the card on `/viet`.
