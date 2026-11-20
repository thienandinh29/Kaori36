-- Step 4.4c: Listening to a whole Reading passage and answering its approved questions. The answers
-- are kept with the other Listening answers; `kind` widens to 'passage' (nothing existing changes).
alter table listening_answers drop constraint listening_answers_kind_check;
alter table listening_answers
    add constraint listening_answers_kind_check check (kind in ('dictation', 'gap', 'passage'));
