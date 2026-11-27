-- Speaking examiner tests (specs/speaking/step-5.4a.md). Additive.
-- One row per sitting of an authored test, and one per recorded answer. A voice is personal data:
-- an answer's audio is cleared after a day unless the learner chose to keep the test's recordings;
-- the row stays (question, length, quality) so the result page can say what was answered.
create table speaking_tests (
    id           uuid primary key default gen_random_uuid(),
    learner_id   uuid not null references learners (id) on delete cascade,
    test_id      text not null,  -- the authored file's id, e.g. 't01'
    test_sha256  text not null,  -- the file as it was when the test was taken
    consent      text not null,  -- the voice notice the learner accepted, e.g. 'voice-v1'
    keep         boolean not null default false,
    started_at   timestamptz not null default now(),
    finished_at  timestamptz
);
create index speaking_tests_learner_idx on speaking_tests (learner_id, started_at desc);

create table speaking_answers (
    id            uuid primary key default gen_random_uuid(),
    sitting_id    uuid not null references speaking_tests (id) on delete cascade,
    question_id   text not null,  -- p1-<topic>-<n>, p2-long, p2-closing, p3-<n>
    part          smallint not null check (part in (1, 2, 3)),
    question      text not null,  -- the question as asked, should the file change later
    audio         bytea check (audio is null or octet_length(audio) <= 4500000),
    seconds       real not null,
    quality       jsonb not null,
    recorded_at   timestamptz not null default now(),
    delete_after  timestamptz,  -- null when kept; the audio is cleared at this time
    unique (sitting_id, question_id)
);
create index speaking_answers_purge_idx on speaking_answers (delete_after)
    where delete_after is not null and audio is not null;
