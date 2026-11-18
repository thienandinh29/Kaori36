# Step V1: labels and tiers (plan and tasks)

Spec: `spec.md` (approved by the owner 18 Nov 2026, as written). This step stores who said what about which piece of
content, and computes how far it can be trusted. It changes no gate yet (V3 does), and adds no route or page (V2).

## What is built
- **Migration `0026_labels.sql`** (additive):
  - `reviewers`: display name, role (`expert_teacher`, `ielts_rater`, `phonetics_expert`), declared expertise, and
    when they consented;
  - `labels`: what is labelled (content type, id, aspect), the value, the role, the exact source, an independence
    key, the label's own tier, and the reviewer. One label per source per aspect: a later label from the same
    source replaces the earlier one.
- **`app/validation/tiers.py`** (pure, unit-tested):
  - a label's own tier comes from its role, never from the caller:
    - an expert role or an expert-labelled dataset gives Gold;
    - a model, a source, a code check or the owner as developer gives Bronze;
    - the owner as learner gives `feedback`, which never counts as correctness;
  - the effective tier of one aspect of one item:
    1. "unsure" values and feedback are ignored.
    2. **Gold:** at least one Gold label, and the Gold labels agree. If they disagree, the aspect is *disputed* and has
       no tier until an expert settles it.
    3. **Silver:** with no Gold, at least two non-owner labels with **different independence keys** agree, and no
       counted label disagrees. Two models of the same family count once. The owner's own labels never count
       towards Silver, so nothing is promoted by the owner's approval alone.
    4. **Bronze:** any other label, including the owner's. If the labels conflict, the aspect is also marked
       disputed.
    5. No labels: no tier.
  - Silver through "a Gold sample shows the process is reliable" is a property of a process, not of one item. It
    comes with V3.
- **`app/validation/store.py`:** add a reviewer, add a label (validated: an expert role needs a reviewer of that role),
  read the labels for an item, compute the effective tier.
- **`app/validation/cli.py`:**
  - `backfill`: copies existing decisions as labels, and is safe to run again:
    - each owner label on a sound becomes `speech_target` / `phone_ok`, owner, Bronze;
    - each Reading item gets `reading_item` / `item_ok` labels: the code checks (`code_check:reading`), the blind
      checker (`model:<id>`, from its call before any review) and the owner's review (Bronze);
  - `summary`: counts by content type and effective tier;
  - `add-reviewer`.

## Not in this step
- The portal (V2) and gates reading tiers (V3).
- Lesson checkpoint checks: their results live in YAML files, not the database. They are backfilled when V3 needs them.

## Tasks
- [x] T1 Migration `0026_labels.sql`.
- [x] T2 `tiers.py` with unit tests (each rule, independence, owner never promotes, disputes).
- [x] T3 `store.py` with database tests (validation, replace on the same source, effective tier).
- [x] T4 `cli.py`: `backfill` (idempotent, tested on real `speech_labels` and `reading_items` rows), `summary`,
  `add-reviewer`.
- [x] T5 MAP, the master roadmap's status, `dolater.md`.
