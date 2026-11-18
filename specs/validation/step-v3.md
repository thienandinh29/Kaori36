# Step V3: gates read tiers (plan and tasks)

Spec: `spec.md` ("Which gates change"). Builds on V1 (labels, tiers) and V2 (the portal). Every gate report now says
**what its truth is** and refuses to call itself a gate result without enough Gold labels.

## The rule
`app/validation/gate.py` (pure) gives every report a `basis` block:
- `truth`: `gold` (experts), `silver`, `bronze` (one source, for example the owner), `feedback` (the owner as a
  learner), or `construction` (truth known by design: simulations, planted faults);
- `n`: how many labelled cases the truth rests on, and `required`: the gate's own minimum;
- `gate`: `measured` only when the truth is `gold` or `construction` **and** `n ≥ required`; otherwise
  `not_measured`, with the reason in Vietnamese and English;
- `declared`: true when the tier is stated by whoever ran the command (a filled-in sheet) rather than read from the
  `labels` table, so a reader knows it was not checked.

A report with `gate: not_measured` keeps all its numbers; they are labelled as development numbers.

## What changes
| Gate | Truth now | Required |
|---|---|---|
| **Reading agreement (CP3, VER-001)**, `app.reading.agreement` | Gold `item_ok` labels from the portal against the checker's call | 50 |
| **Pronunciation thresholds (3.3b)**, `app.pronunciation.thresholds` | Gold `phone_ok` labels when they exist; otherwise your `speech_labels`, as Bronze | as before (10 flags per group on the check half) |
| **Text levels (CP1)**, `app.texts.levels` | `score-gold`: Gold `cefr_level` labels from the portal | 30 |
| **Writing hand ratings and map check (phase 2)** | The sheet, with `--rated-by owner` (default, Bronze) or `teacher` / `rater` (declared Gold) | as before (50 ratings, 100 errors) |

The details of each row:
- **Reading agreement:**
  - It reports by stratum: among items the checker verified, how often the expert says the item is wrong (**defect
    escape**); among items it sent to review, how often the expert says the item is fine (**false rejection**).
    Each comes with an exact interval, and the total is weighted by each stratum's share of all checked items.
  - **Process rule (Silver by process, `spec.md`):** the report says whether the Gold sample supports serving
    checker-verified items. That holds when the upper 95% bound of defect escape is at most 5%, the VER-001 bar.
  - Your own decisions stay in an `owner` section, labelled Bronze, as a development number.
- **Pronunciation thresholds:** `--apply` is **refused** unless the basis is `measured`. Marks on sounds therefore
  wait for a reviewer's labels. Your labels still run the report, as a development check of the pipeline.
- **Text levels:** `score` on your sheet becomes **learner feedback** ("how hard it felt"), which is never a gate.
- **Writing sheets:** a teacher can fill the same sheet you would. The tier is declared, so the report says so.

Unchanged: the simulated gates in CI (`app.evalkit.gates`, `english_gate`), whose truth is known by construction.

## Tasks
- [x] T1 `gate.py` with unit tests.
- [x] T2 Reading agreement against Gold: strata, weighting, process rule, owner section; tests on the database.
- [x] T3 Pronunciation: Gold labels first, Bronze fallback, `--apply` refused unless measured; tests.
- [x] T4 Text levels `score-gold`; the CSV `score` marked as feedback; tests.
- [x] T5 Writing reports `--rated-by`; tests.
- [x] T6 `dolater.md`, MAP, spec status, plan notes.
