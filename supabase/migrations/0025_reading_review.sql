-- The owner's review keeps the checker's call it overrode (specs/listening-reading/step-4.2c.md). Additive.
-- `review_was` is the status before the decision (`verified` or `needs_review`), for the agreement report.
alter table reading_items add column if not exists review_was text
    check (review_was in ('verified', 'needs_review'));
