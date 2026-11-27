-- Today's plan, fixed for the learner's day (specs/two-layer-map/step-m5.md): the engine's first
-- list of the day (Vietnam time), so the list can be ticked off instead of changing under the
-- learner. Whether an activity is done is computed from today's answers, never stored here.
create table today_plans (
    learner_id  uuid not null references learners (id) on delete cascade,
    day         date not null,       -- the learner's day, midnight to midnight in Vietnam
    minutes     integer not null check (minutes between 10 and 180),
    plan        jsonb not null,      -- activities, notes and due counts as the engine returned them
    created_at  timestamptz not null default now(),
    primary key (learner_id, day)
);
