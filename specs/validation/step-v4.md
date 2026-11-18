# Step V4: the progress study (plan and tasks)

Spec: `spec.md` ("Progress" row); master roadmap ("N-of-1"). NodeTrail's own mastery estimates are never proof that
the owner improved. Progress is measured by **independent tests**: a baseline first, then one every 4 weeks. The
tests are official sample papers under exam conditions, or a mock rated by a trained rater. NodeTrail's estimates
are snapshotted next to each result, so the two can be compared.

## Rules
- **Evaluation data stays apart from learner data.** Results live in their own table, `progress_tests`. No engine,
  service or route outside `app/progress/` reads it, and a test enforces this. NodeTrail never uses a test result as
  learning evidence, and never grades its own effect.
- **Every result states its truth** (V3's `basis`):
  - Reading or Listening marked with the paper's own answer key, or Writing or Speaking banded by a trained rater:
    Gold, declared by whoever enters it;
  - self-marked Writing or Speaking: Bronze, a development number only.
- **N-of-1, honestly reported.** One learner and a few tests show a trajectory, not a cause. The report gives each
  change, with the test's own uncertainty where there is one (raw scores with an exact interval). It also says
  whether NodeTrail's estimate moved the same way. It draws no conclusion beyond that.
- **No exam-board content in the repository.** Only scores, dates and the name of the paper used are stored, never
  questions or answers. Raw-to-band conversion uses the paper's own table, entered by the owner.

## What is built
- **Migration `0028_progress_tests.sql`:** one row per skill per sitting. It holds:
  - the learner, the date, and whether it is the baseline;
  - the skill (`listening`, `reading`, `writing`, `speaking`, `overall`);
  - the paper's name and the conditions (timed, under exam conditions);
  - the raw score (`k` of `n`) and the band;
  - how it was marked (`answer_key`, `trained_rater`, `self`);
  - NodeTrail's snapshot at that moment, and a note.
- **`app/progress/study.py`** (pure, tested):
  - `schedule`: the baseline date plus every 28 days, the next due date, and how many days it is overdue;
  - `report`: per skill, each sitting's band and raw share with its interval, the change from the baseline and from
    the previous sitting, and the change in NodeTrail's estimate over the same interval, with a note when the two
    moved in opposite directions.
- **`app/progress/cli.py`:**
  - `add` records one result and takes the snapshot automatically;
  - `schedule` shows the next test date;
  - `report` writes the report (to a private file by default, because these are the owner's results).
- **The snapshot** records, for each subject, the number of concepts, the mean `p_known`, and how many are known
  (≥ 0.9). It also records the latest level test (grammar level, vocabulary level). It is read-only: taking it changes
  nothing.

## Not in this step
A page for entering results (the CLI is enough for one learner), any band prediction, and other learners.

## Tasks
- [x] T1 Migration `0028`.
- [x] T2 `study.py`: schedule and report, with unit tests.
- [x] T3 `cli.py`: add (with snapshot), schedule, report; database tests.
- [x] T4 A separation test: only `app/progress/` touches `progress_tests`.
- [x] T5 `dolater.md`, MAP, spec status, FORGET/KT notes in `research/`.
