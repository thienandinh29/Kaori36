-- Which order the blind checker saw (specs/listening-reading/step-4.3c.md). Additive.
-- null: the stored (generator's) order, as every check before 19 Nov 2026 did; that order gave
-- multiple-choice and headings answers away, so those checks are done again in the shown order.
-- 'shuffled': the order learners see (`items.presented`).
alter table reading_items add column if not exists check_view text
    check (check_view in ('shuffled'));
