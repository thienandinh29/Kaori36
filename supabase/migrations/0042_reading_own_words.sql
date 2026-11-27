-- Step 4.3d part 2 (specs/listening-reading/step-4.3d.md, "Vocabulary"). Additive.
-- A word kept from a pasted Reading test becomes a saved-phrase card (learner_phrases): the word as
-- written, with the passage sentence it came from as the gap-fill. The card stays the learner's
-- when the test is deleted (they chose to keep it); the link is cleared.
alter table learner_phrases
    add column if not exists own_test_id uuid references reading_own_tests (id) on delete set null;
