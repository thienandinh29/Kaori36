-- Transcripts of the Speaking test's answers (specs/speaking/step-5.1.md). Additive.
-- Made on NodeTrail's own machine (Whisper small.en); never sent to a model provider in this step. The
-- transcript is personal text kept with the sitting until the learner deletes it (the audio still goes
-- after a day unless kept). `transcript` holds {text, words: [{word, start, end, probability}], model,
-- revision}; a failure keeps its reason in `transcript` as {error}.
alter table speaking_answers
    add column transcript jsonb,
    add column transcript_status text check (transcript_status in ('done', 'failed')),
    add column transcribed_at timestamptz;
create index speaking_answers_untranscribed_idx on speaking_answers (recorded_at)
    where transcript_status is null and audio is not null;
