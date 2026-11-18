-- FORGET-001: delayed grammar re-checks (specs/forget-001/spec.md). Additive.
-- Evaluation data: a re-check never changes mastery and is not a grammar answer, so it measures the
-- model without feeding it. Only app/services/rechecks.py and app/studies read or write this table.
create table grammar_rechecks (
    id            uuid primary key default gen_random_uuid(),
    learner_id    uuid not null references learners (id) on delete cascade,
    course        text not null,
    node          text not null,
    item_id       text not null,
    p_known       real not null check (p_known between 0 and 1),  -- when planned
    evidence_at   timestamptz not null,  -- the node's last evidence (mastery.updated_at) when planned
    created_at    timestamptz not null default now(),
    answered_at   timestamptz,
    answer        text check (char_length(answer) <= 200),
    correct       boolean,
    check ((answered_at is null) = (correct is null))
);
create index grammar_rechecks_learner_idx on grammar_rechecks (learner_id, course, created_at desc);
create index grammar_rechecks_open_idx on grammar_rechecks (learner_id) where answered_at is null;
