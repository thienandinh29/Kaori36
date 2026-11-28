-- The model's written feedback on a Speaking answer (specs/speaking/step-5.3b.md). Additive.
-- Only the transcript and the question are sent to a model provider, and only after the learner presses the
-- button having ticked the notice `feedback_consent` (a draft wording until the owner sets it). `feedback` holds
-- {points: [{kind, area, point_vi, quote, better}], dropped, quotes_checked, model} (every quote checked to be an
-- exact substring of the transcript) or {failed: reason}. Never evidence, never mastery.
alter table speaking_answers
    add column feedback_status text check (feedback_status in ('queued', 'working', 'done', 'failed')),
    add column feedback jsonb,
    add column feedback_consent text,
    add column feedback_requested_at timestamptz,
    add column feedback_at timestamptz,
    add column feedback_tries int not null default 0;
create index speaking_answers_feedback_queue_idx on speaking_answers (feedback_requested_at)
    where feedback_status = 'queued';
