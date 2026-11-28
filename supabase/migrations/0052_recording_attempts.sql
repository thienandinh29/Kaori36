-- A recording the pronunciation service cannot score is tried at most three times. Additive.
-- `attempts` counts service failures (a problem with the recording itself fails at once); the third marks
-- the recording `failed` (audio cleared unless kept, as for any failure) so one bad recording never holds
-- up the ones after it. The reason goes to the existing `failure` column.
alter table speech_recordings add column attempts int not null default 0;
drop index if exists speech_recordings_queue_idx;
create index speech_recordings_queue_idx on speech_recordings (attempts, created_at) where status = 'stored';
