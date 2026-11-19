# Step 4.2d: the generated item file (spec, plan, tasks)

Plan: `plan.md` (CP2a to CP3). Generation and the blind check run where model calls are possible (a cloud sandbox),
the owner reviews on their laptop, and a sandbox's database is thrown away. So generated questions travel as a
committed file, not as database rows.

## What it does
- `uv run python -m app.reading.itemfile export [--out DIR]`: one YAML file per text in
  `data/english/reading-items/` (default): `text_slug`, `passage_sha256`, and every row of `reading_items` for it
  (id, kind, status, item, problems, checker answer and model, times; the owner's review fields too, so a review
  done on the laptop can be exported back). Sorted by id, so a re-export changes only what changed.
- `uv run python -m app.reading.itemfile import [DIR]`: inserts rows whose id is missing and **never overwrites an
  existing row** (a review already made stays). It reports how many were added, kept, and how many belong to a
  passage that no longer matches its text file (imported anyway; the serving rule and the review queue already refuse
  those). Then it runs the label backfill (`app.validation.cli backfill`, safe to rerun), so code checks and the blind
  checker become labels and approved items can reach Silver.

## Licence
The questions are derived from the texts, so they carry the text's licence (here CC BY-NC-SA 4.0, ShareAlike and
NonCommercial flagged). Each file repeats the text's `source` slug. Only texts in the bank (verified sources) are
exported.

## Tasks
- [x] T1 `app/reading/itemfile.py`: export, import, the CLI.
- [x] T2 Tests on the database: a round trip keeps every field; import never overwrites a reviewed row; a changed
  passage is reported; labels are backfilled.
- [x] T3 Export the first 49 questions (10 OpenStax texts, 19 Nov) and commit them.
