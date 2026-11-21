# Step 2.9: honest labels on the result page, and rewrites that keep the learner's argument

From an outside review of an essay's result (21 Nov 2026, passed on by the owner; Bronze). Five points, each small, each
about the result saying more than it knows.

## What changes
1. **Error kinds.** The full list was titled "Tất cả lỗi ngữ pháp (8)" while all eight were spelling slips. It now reads
   "Tất cả lỗi máy tìm thấy (8): chính tả 8" and is grouped by kind from LanguageTool's category: grammar (GRAMMAR),
   word confusion (CONFUSED_WORDS), spelling (TYPOS, titled "not a grammar error"), punctuation, casing, other, and the
   model's suggestions apart ("chưa được kiểm tra"). A repeated spelling slip in "Sửa trước" is named "Chính tả", not
   "Lỗi khác". Pure: `apps/web/lib/english/issue-kinds.ts`, Vitest. Nothing changes in what moves mastery: spelling
   and punctuation already map to no grammar node.
2. **Word count apart from Task Response.** The length line gives the count, the requirement and the gap ("bài có 244
   từ, đề yêu cầu ít nhất 250 (thiếu 6)") and says that length is a separate requirement, counted exactly by code;
   whether the essay answers the question is the Task Response feedback. The feedback prompts tell the model the tools
   show the word count and not to make it a point.
3. **Sentence complexity is reference, not a target.** Under "Độ phức tạp của câu": more clauses do not make an essay
   better; use a complex sentence when it makes the idea clearer, and keep it correct.
4. **The 0.25 "same" threshold of the owner's raw-score preview** is labelled an assumption, not a measurement. The
   scorer is deterministic, so scoring the same text again gives the same number; what the threshold must cover is how
   far the score moves under changes that keep the content (spacing, paragraph breaks, a fixed typo, a synonym). It is
   to be set from the robustness perturbations of step 2.3 (`app.evalkit.writing_score test`) on the private essays:
   the 95th percentile of the absolute change. Until then the preview says "tạm".
5. **Rewrites must keep the learner's argument** (`meaning_problems` in `apps/api/app/writing/rewrite.py`, pure,
   unit-tested; a new `meaning` check runs after length and before LanguageTool). A rewrite is refused when:
   - it brings in a number, number word, percentage or name the paragraph does not have (`new_facts`);
   - the count of negations changes, so a statement may have been turned around (`negation`);
   - fewer than 40% of the paragraph's content words (crudely stemmed) remain (`content`): a different paragraph.
   The prompt also forbids new examples, figures, names and claims. The panel is now titled "Thử viết lại một đoạn"
   (not "ở band cao hơn") and says the machine has not shown the rewrite is better by the IELTS criteria: higher
   scorer output and no LanguageTool error are necessary, not sufficient.

## Limits, stated
- The meaning checks catch the clear cases only. A rewrite can keep the words and still weaken the reasoning, or add an
  unsupported claim without a number or a name. The 40% bar is Bronze: a synonym-heavy paraphrase in the tests keeps
  60%, a different paragraph keeps under 20%; no real rewrite has been measured yet (none exist in the database).
- **Specified for later, not built:** a blind check by a model of another family that lists the paragraph's claims and
  says, for each, kept / weakened / changed, and names any new claim, with a planted test (rewrites with a planted new
  statistic, flipped stance, dropped reason) before it gates anything; and the owner's ratings of rewrites in the
  writing-review sheet (`docs/v2/writing-eval.md`), by a teacher for Gold.

## Tests
Vitest `lib/english/issue-kinds.test.ts` (kinds, order, eight spelling errors stay spelling); pytest
`tests/writing/test_rewrite.py` (a paraphrase passes; a new statistic, a name, a number word, a flipped negation and a
different paragraph are refused; a number already written may stay) and the service test's checks; Playwright: the full
list groups the agreement error under grammar.
