-- Grammar and vocabulary checks on the Speaking test's transcripts (specs/speaking/step-5.3.md, 5.3a). Additive.
-- Made by code on our own machines (LanguageTool, ERRANT, the word list, the memorised-phrase list); nothing is
-- sent to a model provider. `language` holds {skipped, guard, vocabulary, hints} or {failed: reason}. Grammar
-- flags on speech are hints, never evidence: nothing here reaches the mastery model.
alter table speaking_answers
    add column language jsonb,
    add column language_at timestamptz;
create index speaking_answers_unchecked_idx on speaking_answers (recorded_at)
    where transcript_status = 'done' and measures is not null and language is null and audio is not null;
