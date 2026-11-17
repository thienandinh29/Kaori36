-- The owner's labels on target sounds (specs/pronunciation/step-3.3.md, 3.3b). Additive.
-- One label per target position of an analysed recording; deleting the recording deletes its labels.
create table speech_labels (
    recording_id  uuid not null references speech_recordings (id) on delete cascade,
    target        integer not null check (target >= 0),
    label         text not null check (label in ('right', 'wrong', 'unsure')),
    labelled_at   timestamptz not null default now(),
    primary key (recording_id, target)
);
