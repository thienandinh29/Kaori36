-- Step 4.3d part 2 (specs/listening-reading/step-4.3d.md, "Position and pacing"). Additive.
-- The passage's place in the test (1-3) and the learner's own mark on an answer ("đoán" guessed,
-- "không kịp" ran out of time). Blank and marked answers now get a row too (no evidence, p_before
-- and p_after null), so the summary sees them; the first paste of a test is the one counted.
alter table reading_own_tests
    add column if not exists position smallint check (position between 1 and 3);
alter table reading_own_answers
    add column if not exists position smallint check (position between 1 and 3),
    add column if not exists mark text check (mark in ('guessed', 'no_time')),
    add column if not exists blank boolean not null default false;
