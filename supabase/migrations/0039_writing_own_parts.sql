-- Step 2.11b (specs/writing/step-2.11.md): the parts of an own Task 2 question the learner kept.
-- Code proposes the parts from the question's wording; the learner ticks them before writing.
-- Null (essays from before 2.11b) keeps every proposed part.
alter table essays add column own_parts jsonb
    check (own_parts is null or jsonb_typeof(own_parts) = 'array');
alter table writing_tests add column own_parts jsonb
    check (own_parts is null or jsonb_typeof(own_parts) = 'array');
