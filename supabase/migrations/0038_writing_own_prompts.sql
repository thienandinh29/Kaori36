-- Step 2.10 (specs/writing/step-2.10.md): the learner's own Task 2 question, and timed exam essays.
alter table essays add column own_prompt text
    check (own_prompt is null or char_length(own_prompt) between 20 and 1000);

create table writing_tests (
    id           uuid primary key default gen_random_uuid(),
    learner_id   uuid not null references learners (id) on delete cascade,
    prompt_id    text not null,
    own_prompt   text check (own_prompt is null or char_length(own_prompt) between 20 and 1000),
    time_limit_s integer not null check (time_limit_s > 0),
    started_at   timestamptz not null
);
create index writing_tests_learner_idx on writing_tests (learner_id, started_at desc);

alter table essays add column test_id uuid references writing_tests (id) on delete set null;
alter table essays add column over_time boolean;
create unique index essays_test_idx on essays (test_id) where test_id is not null;
