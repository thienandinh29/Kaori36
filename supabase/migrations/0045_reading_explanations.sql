-- CP4b on the bank's own questions, step 1 (specs/listening-reading/spec.md, "Why the wrong answer
-- tempted you"). Additive. One explanation per question version: generated offline (DeepSeek),
-- kept only when code's checks pass. Nothing is shown to a learner until the blind check by
-- another family and its planted test exist (the next step adds their columns).
create table reading_explanations (
    id              bigint generated always as identity primary key,
    item_id         text not null references reading_items (id) on delete cascade,
    passage_sha256  text not null,           -- an edited passage drops the explanation
    item_sha256     text not null,           -- so does an edited question
    status          text not null check (status in ('checked', 'dropped')),
    explanation     jsonb not null,          -- as kept, or as written when dropped
    skills          text[] not null default '{}',  -- step 4.3e's sub-skill tags (Bronze)
    problems        jsonb not null default '[]',
    model           text,
    generated_at    timestamptz not null default now()
);
create unique index reading_explanations_version_idx
    on reading_explanations (item_id, passage_sha256, item_sha256);
