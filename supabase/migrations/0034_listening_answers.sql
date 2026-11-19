-- Listening practice answers (specs/listening-reading/step-4.4b.md, plan CP5). Additive.
-- Items are built by code from bank texts (no table of their own): `item_id` names one, e.g.
-- `os-astronomy-2e-earth-and-sky-dictation-1`. Each answer also moved the item's Listening competency.
create table listening_answers (
    id           bigint generated always as identity primary key,
    learner_id   uuid not null references learners (id) on delete cascade,
    item_id      text not null,
    kind         text not null check (kind in ('dictation', 'gap')),
    competency   text not null,
    answer       text not null,
    score        real not null check (score between 0 and 1),
    correct      boolean not null,
    p_before     real not null check (p_before between 0 and 1),
    p_after      real not null check (p_after between 0 and 1),
    answered_at  timestamptz not null default now()
);
create index listening_answers_learner_idx on listening_answers (learner_id, competency);
