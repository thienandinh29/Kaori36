-- The progress study's criterion bands (specs/validation/step-v4.md, "Addition (27 Nov 2026)"). Additive.
-- A rated Writing or Speaking sitting also keeps the rater's four criterion bands, as whole bands 0-9:
-- Writing tr, cc, lr, gra; Speaking fc, lr, gra, p. The skill's band stays what the rater gave;
-- NodeTrail never computes it from these. Checked in app/progress/study.py before insert.
alter table progress_tests add column criteria jsonb
    check (criteria is null or (jsonb_typeof(criteria) = 'object' and skill in ('writing', 'speaking')));
