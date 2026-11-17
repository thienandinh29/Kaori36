-- Pronunciation recordings (specs/pronunciation/step-3.1.md). Additive.
-- A voice is personal data: kept on our own database only until it is analysed (step 3.2), or for at most a day
-- until then, unless the learner chose to keep it; the learner can delete any recording at once.
create table speech_recordings (
    id            uuid primary key default gen_random_uuid(),
    learner_id    uuid not null references learners (id) on delete cascade,
    prompt_id     text not null,
    consent       text not null,  -- the notice version the learner accepted, e.g. 'voice-v1'
    keep          boolean not null default false,  -- opted in to keep it for improving the tools
    audio         bytea not null check (octet_length(audio) <= 600000),
    seconds       real not null,
    quality       jsonb not null,
    status        text not null default 'stored' check (status in ('stored', 'analysed')),
    created_at    timestamptz not null default now(),
    delete_after  timestamptz  -- null when kept
);
create index speech_recordings_learner_idx on speech_recordings (learner_id, created_at desc);
create index speech_recordings_purge_idx on speech_recordings (delete_after) where delete_after is not null;
