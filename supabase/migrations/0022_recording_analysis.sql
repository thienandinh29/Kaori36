-- Pronunciation analysis results (specs/pronunciation, step 3.3). Additive; the status check is widened, not narrowed.
alter table speech_recordings add column if not exists analysis jsonb;
alter table speech_recordings add column if not exists analysed_at timestamptz;
alter table speech_recordings add column if not exists failure text;
alter table speech_recordings drop constraint if exists speech_recordings_status_check;
alter table speech_recordings add constraint speech_recordings_status_check
    check (status in ('stored', 'analysed', 'failed'));
create index if not exists speech_recordings_queue_idx on speech_recordings (created_at) where status = 'stored';
