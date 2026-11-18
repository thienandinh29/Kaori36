-- The validation system, step V1 (specs/validation/step-v1.md). Additive.
-- Who said what about which piece of content. A label's own tier is set by code from its role
-- (gold for experts and expert-labelled datasets, bronze for one source, feedback for the owner as
-- learner); silver is never stored, only computed from independent labels that agree.
create table reviewers (
    id            uuid primary key default gen_random_uuid(),
    display_name  text not null check (length(display_name) between 1 and 80),
    role          text not null check (role in ('expert_teacher', 'ielts_rater', 'phonetics_expert')),
    expertise     text not null default '',  -- as the reviewer declares it, e.g. "8 years teaching IELTS"
    consented_at  timestamptz not null,      -- agreed to how their labels are used
    created_at    timestamptz not null default now()
);

create table labels (
    id            bigserial primary key,
    content_type  text not null,   -- checked in code (app/validation/tiers.py), so new kinds need no migration
    content_id    text not null,
    aspect        text not null,   -- what is judged, e.g. item_ok, phone_ok, cefr_level
    value         text not null,
    role          text not null check (role in (
                      'expert_teacher', 'ielts_rater', 'phonetics_expert', 'dataset',
                      'model', 'source', 'code_check', 'owner_developer', 'owner_learner')),
    source        text not null,   -- exactly who: reviewer:<id>, model:<id>, dataset:<name>, owner, ...
    independence  text not null,   -- labels with the same key count once (one model family, one reviewer)
    tier          text not null check (tier in ('gold', 'bronze', 'feedback')),
    reviewer_id   uuid references reviewers (id) on delete restrict,
    labelled_at   timestamptz not null default now(),
    note          text,
    unique (content_type, content_id, aspect, source),
    check ((role in ('expert_teacher', 'ielts_rater', 'phonetics_expert')) = (reviewer_id is not null))
);
create index labels_content_idx on labels (content_type, content_id, aspect);
