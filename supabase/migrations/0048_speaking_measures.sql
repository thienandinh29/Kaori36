-- Fluency measures of the Speaking test's answers (specs/speaking/step-5.2.md). Additive.
-- Numbers about how an answer was spoken (rates, pauses and where they fall, fillers, the longest fluent
-- run), made while the audio is still there (it goes after a day unless kept) and kept with the sitting.
-- Never a score: nothing here reaches the mastery model or a model call.
alter table speaking_answers
    add column measures jsonb,
    add column measured_at timestamptz;
create index speaking_answers_unmeasured_idx on speaking_answers (recorded_at)
    where transcript_status = 'done' and measures is null and audio is not null;
