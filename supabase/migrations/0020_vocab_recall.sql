-- The flashcard test (specs/vocabulary, flashcards): a new item kind, `recall` (type the word from its meaning).
-- Widens the check on the review log only; no data changes, no allowed value is removed.
alter table vocab_reviews drop constraint if exists vocab_reviews_item_kind_check;
alter table vocab_reviews add constraint vocab_reviews_item_kind_check
    check (item_kind in ('meaning', 'gapfill', 'collocation', 'wordform', 'recall'));
