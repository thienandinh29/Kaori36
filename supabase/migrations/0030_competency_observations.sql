-- Writing competency evidence (specs/two-layer-map/writing-evidence.md). Additive.
-- Every pass/fail observation an essay gave a Writing competency, with the rule and the measured
-- value; the competency's mastery itself lives in `mastery` under the subject `ielts-competencies`.
create table competency_observations (
    id           bigint generated always as identity primary key,
    learner_id   uuid not null references learners (id) on delete cascade,
    competency   text not null,
    source       text not null check (source in ('essay')),
    source_id    uuid not null,
    rule         text not null,
    passed       boolean not null,
    value        real,
    p_before     real not null check (p_before between 0 and 1),
    p_after      real not null check (p_after between 0 and 1),
    observed_at  timestamptz not null default now(),
    unique (source, source_id, competency, rule)
);
create index competency_observations_learner_idx on competency_observations (learner_id, competency);
