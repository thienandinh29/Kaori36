# Step 2.6 — Fix first: prioritised feedback, adapted to the learner's level

From the owner's deep research (20 Nov 2026, `IELTS_Writing_Feedback_Tool_Research.md`, not committed: a report with
citations to check, Bronze). The findings this step acts on:
- Marking every error overloads learners: one classroom study of Write & Improve found 11% of highlights led to a real
  fix, 39% were ignored and 12.8% were "fixed" by deleting the text (peer-reviewed, small n). Focused feedback on a few
  systematic error patterns gives more durable gains than comprehensive marking (meta-analyses; the size is contested).
- Vietnamese students ask for every error to be marked (about 70% in one small survey) yet rank word choice and ideas
  above grammar.
- Direct correction (the right form plus a short explanation) suits lower levels; naming the error type and letting the
  learner fix it suits B2 and above (moderate evidence).

## What changes (web only; no route or contract field changes)
1. **"Sửa trước" (fix first)** at the top of an essay's result: at most 5 items, chosen by a pure, tested function
   (`apps/web/lib/english/priorities.ts`):
   1. Task 1 only: a number not found in the chart's data, then a missing overview.
   2. The model's "issue" points, one per criterion, in the order Task Response (Task Achievement), Lexical Resource,
      Coherence and Cohesion, Grammar; at most 3.
   3. Grammar error patterns: LanguageTool errors grouped by grammar node (else ERRANT type); a group seen twice or
      more is a pattern; most frequent first, then the earliest. They fill the remaining slots, at least 2 when there
      are any; otherwise more feedback points fill them.
   Each item links to where it came from; a pattern shows how many times it occurred and its first sentence.
2. **The full error list is folded** under "Tất cả lỗi ngữ pháp (n)", closed by default: nothing is hidden, the learner
   chooses to open it. The feedback by criterion stays as it is.
3. **Correction style by level.** The learner's grammar level from the last level test (`/roadmap`): A1–B1 or no test
   → direct (the suggestion and the Vietnamese explanation); B2–C1 → indirect (the error type and explanation; the
   suggestion behind "Xem cách sửa"). The learner can switch; the choice is kept in this browser only. The style
   applies to "Sửa trước"; the folded full list keeps every suggestion and the existing "Tự sửa câu này" exercise.

## Not changed
No marks, bands or mastery change: which errors count as evidence is still decided by the API (step 2.2). The
ordering is a presentation rule, not a judgement of correctness; whether it helps is a learner-feedback question
(Bronze) until measured.

## Checks
Vitest for `priorities.ts` (order, caps, patterns, Task 1 first, level → style); Playwright on an essay result
(fix-first list, folded list opens, the style switch).
