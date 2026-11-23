-- Step 4.3d (specs/listening-reading/step-4.3d.md, CP4b first): a Reading test the learner took
-- outside the app, pasted for feedback. Additive.
-- The pasted test is the learner's own material: kept only here, with that learner, deletable,
-- never in the shared bank or the item files.
create table reading_own_tests (
    id              uuid primary key default gen_random_uuid(),
    learner_id      uuid not null references learners (id) on delete cascade,
    consent         text not null,
    passage         text not null check (char_length(passage) between 1 and 14000),
    questions_text  text not null check (char_length(questions_text) between 1 and 8000),
    key_text        text not null check (char_length(key_text) between 1 and 2000),
    answers_text    text not null check (char_length(answers_text) <= 2000),
    fingerprint     text not null,              -- sha256 of the passage and the key's answers
    progress_test   boolean not null default false,
    -- queued -> parsing -> parsed (the learner confirms) -> marked -> explaining -> done; or failed
    status          text not null default 'queued'
                    check (status in ('queued','parsing','parsed','marked','explaining','done','failed')),
    questions       jsonb,                      -- as read and checked, then as confirmed
    result          jsonb,                      -- marks, score, explanations
    failure_vi      text,
    submitted_at    timestamptz not null default now(),
    confirmed_at    timestamptz
);
create index reading_own_tests_learner_idx on reading_own_tests (learner_id, submitted_at desc);
create index reading_own_tests_status_idx on reading_own_tests (status, submitted_at)
    where status in ('queued','marked');

-- One row per marked answer: what the summary across tests (part 2) counts, and the evidence
-- guard. No passage text and no answer text, so it may outlive a deleted test; a test pasted
-- again (same fingerprint) never gives evidence twice for a question.
create table reading_own_answers (
    id           bigint generated always as identity primary key,
    learner_id   uuid not null references learners (id) on delete cascade,
    test_id      uuid references reading_own_tests (id) on delete set null,
    fingerprint  text not null,
    number       integer not null check (number between 1 and 60),
    kind         text not null check (kind in ('tfng','ynng','mcq','completion')),
    competency   text not null,
    correct      boolean not null,
    trap         text,
    p_before     real check (p_before between 0 and 1),
    p_after      real check (p_after between 0 and 1),
    answered_at  timestamptz not null default now()
);
create unique index reading_own_answers_once_idx
    on reading_own_answers (learner_id, fingerprint, number);
