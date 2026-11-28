-- Guided Speaking practice (specs/speaking/step-5.4b.md). Additive.
-- A try is a sitting with one answer, so the transcript, measures and checks run as for any answer.
-- `practice_of` points at the first try's sitting (null on the first try itself); deleting the first
-- try deletes the repeats. Only the first try counts as evidence of fluency; repeats are practice.
alter table speaking_tests
    add column mode text not null default 'exam' check (mode in ('exam', 'guided')),
    add column question_id text,
    add column try_no int not null default 1 check (try_no between 1 and 3),
    add column practice_of uuid references speaking_tests (id) on delete cascade,
    add column asked_seconds int check (asked_seconds is null or asked_seconds > 0),
    add check ((mode = 'guided') = (question_id is not null));
create index speaking_tests_practice_idx on speaking_tests (practice_of) where practice_of is not null;
