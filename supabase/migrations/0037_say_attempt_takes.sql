-- One attempt per recording (specs/pronunciation/step-3.7b.md, fixed 20 Nov 2026). Additive.
-- Analysing the same recording again ("Phân tích lại", or a retry after a lost reply) used to add a
-- second attempt, so one recording counted twice in "2 of the last 3". The browser now names each
-- recording; the same name replaces its attempt. Older rows have none and are counted as before.
alter table say_attempts add column take_id uuid;
create unique index say_attempts_take_idx on say_attempts (learner_id, word, take_id)
    where take_id is not null;
