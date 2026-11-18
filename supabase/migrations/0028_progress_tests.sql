-- The progress study, step V4 (specs/validation/step-v4.md). Additive.
-- Evaluation data, kept apart from learner data: only app/progress reads or writes this table, and the
-- learning engine never uses it as evidence. Scores only; never exam questions or answers.
create table progress_tests (
    id           uuid primary key default gen_random_uuid(),
    learner_id   uuid not null references learners (id) on delete cascade,
    taken_on     date not null,
    baseline     boolean not null default false,
    skill        text not null
                 check (skill in ('listening', 'reading', 'writing', 'speaking', 'overall')),
    paper        text not null check (length(paper) between 1 and 200),  -- which sample paper or mock
    timed        boolean not null,      -- under exam conditions
    raw_k        integer check (raw_k >= 0),
    raw_n        integer check (raw_n > 0),
    band         numeric(2, 1) check (band between 0 and 9 and band * 2 = round(band * 2)),
    marked_by    text not null check (marked_by in ('answer_key', 'trained_rater', 'self')),
    snapshot     jsonb not null,        -- NodeTrail's own estimates at entry time
    note         text,
    created_at   timestamptz not null default now(),
    check ((raw_k is null) = (raw_n is null) and (raw_k is null or raw_k <= raw_n)),
    check (raw_k is not null or band is not null)
);
create index progress_tests_learner_idx on progress_tests (learner_id, skill, taken_on);
create unique index progress_tests_one_baseline on progress_tests (learner_id, skill) where baseline;
