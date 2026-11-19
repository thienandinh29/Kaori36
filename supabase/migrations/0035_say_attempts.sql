-- Saying a vocabulary word (specs/pronunciation/step-3.7b.md). Additive.
-- One row per analysed attempt: the per-sound scores only, never the audio. Used for repeated-mistake guidance and
-- the learner's "sounds to focus on"; never as evidence (no mastery moves until the pronunciation gate).
create table say_attempts (
    id          bigint generated always as identity primary key,
    learner_id  uuid not null references learners (id) on delete cascade,
    word        text not null,
    phones      jsonb not null,
    said_at     timestamptz not null default now()
);
create index say_attempts_learner_idx on say_attempts (learner_id, word, said_at desc);
