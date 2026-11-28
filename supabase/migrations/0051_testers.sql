-- Opening Speaking to invited testers (specs/speaking/step-5.5.md). Additive.
-- A tester is a learner the owner invited by a one-time link. Only hashes of the link's and the session's
-- tokens are kept; the tokens themselves are shown once. `research_consent` records the optional notice
-- under which a tester's own numbers may appear in the owner's report.
create table testers (
    id                    uuid primary key default gen_random_uuid(),
    learner_id            uuid not null unique references learners (id) on delete cascade,
    label                 text not null check (length(label) between 1 and 60),
    created_at            timestamptz not null default now(),
    revoked_at            timestamptz,
    research_consent      text,
    research_consent_at   timestamptz
);

create table tester_invites (
    token_hash   text primary key,
    tester_id    uuid not null references testers (id) on delete cascade,
    created_at   timestamptz not null default now(),
    expires_at   timestamptz not null,
    used_at      timestamptz
);
create index tester_invites_tester_idx on tester_invites (tester_id);

create table tester_sessions (
    token_hash   text primary key,
    tester_id    uuid not null references testers (id) on delete cascade,
    created_at   timestamptz not null default now(),
    expires_at   timestamptz not null,
    last_seen    timestamptz
);
create index tester_sessions_tester_idx on tester_sessions (tester_id);
