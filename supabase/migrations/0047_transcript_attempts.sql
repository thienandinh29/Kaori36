-- A Speaking answer that cannot be transcribed is tried at most three times. Additive.
-- `transcript_attempts` counts service failures (not refusals, which fail at once); the third marks the
-- answer `failed` so one bad recording never holds up the ones after it. `transcript_error` keeps the reason.
alter table speaking_answers
    add column transcript_attempts int not null default 0,
    add column transcript_error text;
drop index speaking_answers_untranscribed_idx;
create index speaking_answers_untranscribed_idx on speaking_answers (transcript_attempts, recorded_at)
    where transcript_status is null and audio is not null;
