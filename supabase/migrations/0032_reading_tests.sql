-- Timed Reading tests (specs/listening-reading/step-4.3b.md). Additive.
-- A test fixes its questions when it starts; the server keeps the time; one submission per test.
create table reading_tests (
    id             uuid primary key default gen_random_uuid(),
    learner_id     uuid not null references learners (id) on delete cascade,
    text_slug      text not null,
    item_ids       text[] not null,
    limit_seconds  integer not null check (limit_seconds > 0),
    started_at     timestamptz not null,
    submitted_at   timestamptz,
    correct        integer,
    total          integer,
    over_time      boolean
);
create index reading_tests_learner_idx on reading_tests (learner_id, started_at);
-- An answer given in a test points to it (practice answers have none).
alter table reading_answers add column if not exists test_id uuid references reading_tests (id) on delete set null;
