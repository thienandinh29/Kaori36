-- Writing step 2.4b (specs/writing/step-2.4.md, points 4 and 5): paragraph rewrites as worker jobs,
-- and phrases the learner saves from a rewrite. Additive only.

create table essay_rewrites (
    id uuid primary key default gen_random_uuid(),
    essay_id uuid not null references essays(id) on delete cascade,
    learner_id uuid not null references learners(id) on delete cascade,
    paragraph integer not null check (paragraph >= 0),
    target_band numeric(3,1) not null check (target_band between 0 and 9),
    status text not null default 'queued'
        check (status in ('queued','working','done','rejected','failed')),
    attempts integer not null default 0 check (attempts between 0 and 2),
    result jsonb,
    reason_vi text,
    created_at timestamptz not null default now(),
    finished_at timestamptz
);
create index essay_rewrites_queue on essay_rewrites (created_at) where status = 'queued';
create index essay_rewrites_essay on essay_rewrites (essay_id);

-- A phrase the learner chose to keep. Its review card lives in vocab_cards under list 'my-phrases'
-- with the phrase id as word_key. The essay may be deleted; the learner's phrase stays.
create table learner_phrases (
    id uuid primary key default gen_random_uuid(),
    learner_id uuid not null references learners(id) on delete cascade,
    essay_id uuid references essays(id) on delete set null,
    phrase text not null check (char_length(phrase) between 2 and 120),
    sentence text not null check (char_length(sentence) between 2 and 600),
    created_at timestamptz not null default now(),
    unique (learner_id, phrase)
);
