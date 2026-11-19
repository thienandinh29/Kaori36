-- Reading practice answers (specs/listening-reading/step-4.3.md, plan CP4). Additive.
-- One row per answer; each also moved the item's Reading competency (mastery under `ielts-competencies`).
create table reading_answers (
    id           bigint generated always as identity primary key,
    learner_id   uuid not null references learners (id) on delete cascade,
    item_id      text not null references reading_items (id) on delete cascade,
    competency   text not null,
    answer       jsonb not null,
    score        real not null check (score between 0 and 1),
    correct      boolean not null,
    p_before     real not null check (p_before between 0 and 1),
    p_after      real not null check (p_after between 0 and 1),
    answered_at  timestamptz not null default now()
);
create index reading_answers_learner_idx on reading_answers (learner_id, competency);
