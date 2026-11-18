-- Generated Reading questions and their checks (specs/listening-reading/step-4.2b.md). Additive.
-- `approved` and `rejected` are set only by the owner's review (plan CP3); nothing here is served before that.
create table reading_items (
    id              text primary key,  -- assigned by code: <text slug>-<kind>-<n>
    text_slug       text not null,
    passage_sha256  text not null,     -- an edited text invalidates its items
    kind            text not null check (kind in ('tfng', 'mcq', 'completion', 'headings')),
    item            jsonb not null,    -- the 4.2a schema (app/reading/items.py)
    status          text not null default 'generated'
                    check (status in ('generated', 'dropped', 'needs_review', 'verified', 'approved', 'rejected')),
    problems        jsonb not null default '[]'::jsonb,  -- code checks that failed (status dropped)
    checker_answer  text,              -- what the blind checker answered
    checker_model   text,
    generated_at    timestamptz not null default now(),
    checked_at      timestamptz,
    reviewed_at     timestamptz,
    review_note     text
);
create index reading_items_text_idx on reading_items (text_slug, passage_sha256);
create index reading_items_pending_idx on reading_items (generated_at) where status = 'generated';
