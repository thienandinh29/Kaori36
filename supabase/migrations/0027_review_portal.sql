-- The reviewer portal, step V2 (specs/validation/step-v2.md). Additive.
-- A reviewer's link carries a token; only its SHA-256 is stored, and it can be revoked.
create table reviewer_tokens (
    token_sha256  text primary key,
    reviewer_id   uuid not null references reviewers (id) on delete cascade,
    created_at    timestamptz not null default now(),
    revoked_at    timestamptz
);
create index reviewer_tokens_reviewer_idx on reviewer_tokens (reviewer_id);

-- A fixed, stratified sample for one role: item ids in a shuffled order, each item's stratum, and the
-- population counts per stratum, so a later report can weight the strata.
create table review_batches (
    id            uuid primary key default gen_random_uuid(),
    name          text not null check (length(name) between 1 and 80),
    content_type  text not null,
    aspect        text not null,
    role          text not null check (role in ('expert_teacher', 'ielts_rater', 'phonetics_expert')),
    item_ids      jsonb not null,   -- ["id", ...] in serving order
    strata        jsonb not null,   -- {"id": "disagreed" | "agreed" | "all"}
    population    jsonb not null,   -- {"disagreed": n, "agreed": n}
    seed          integer not null,
    created_at    timestamptz not null default now(),
    closed_at     timestamptz
);

alter table labels add column if not exists detail jsonb;
