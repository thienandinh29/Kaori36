-- Plans and their daily limits (specs/plans). Additive: every existing learner is on the free plan.
-- "owner" is never stored: the owner is whoever is listed in DRAFT_ITEM_LEARNERS.
alter table learners add column if not exists plan text not null default 'free';
alter table learners add constraint learners_plan_check check (plan in ('free', 'pro'));
