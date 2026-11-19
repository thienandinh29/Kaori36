# Step 3.6a: pronunciation evidence with three outcomes and two error layers (spec, plan, tasks)

Builds on `step-3.3.md` (3.3b thresholds) and `step-3.4.md` (marks and BKT). Prompted by an outside review
(19 Nov) that the owner shared. Nothing reaches BKT today: no sound group has passed the gate, so `thresholds.json`
does not exist. That makes this the cheap moment to fix two flaws before it does.

## The two flaws
1. **The detector's errors were used as the learner's.** `marks.observation` set BKT's slip to the detector's
   false-positive rate and guess to its miss rate. BKT's slip and guess belong to the learner (a learner who knows
   /θ/ still says /t/ sometimes; one who does not sometimes gets it right). The detector adds its own errors on
   top. One recording then looked more informative than it is.
2. **An unmarked sound counted as said right.** The page says "unmarked = not sure", but `observations` fed it to
   BKT as a correct answer. A sound just above the mark threshold is not evidence of a right sound.

## The change
**Three outcomes per target sound** (pure, `app/pronunciation/evidence.py`):
- `wrong`: GOP below the group's mark `threshold` and the recogniser heard a competing phone (as now);
- `right`: GOP at or above the group's `accept` threshold, a second, higher one;
- `inconclusive`: anything else. No mastery update, and the page says so ("chưa chắc").

**Thresholds (3.3b report).** `threshold` is chosen as now (most catches with a false-alarm share ≤ 10%). `accept`
is chosen on the same tune half: the lowest GOP at or above `threshold` such that, of the sounds it would accept,
at most `MAX_ACCEPTED_WRONG` (10%) are labelled wrong. On the check half the report gives, separately for sounds
labelled right and labelled wrong, how many came out `right`, `wrong` and `inconclusive`, and the conclusive share.
A group passes only if, on the check half, the false-alarm rule holds (as now), the accepted-but-wrong share is
≤ 10% with at least `MIN_ACCEPTED` accepted sounds, and at least `MIN_CONCLUSIVE` (50%) of its sounds are
conclusive. A detector that is rarely sure is not useful even if it is rarely wrong.

**The observation model.** With the detector's rates `P(outcome | said right)` and `P(outcome | said wrong)` from
the check half, and the learner's own slip `s` and guess `g`:

    P(o | knows)     = (1 − s) · P(o | said right) + s · P(o | said wrong)
    P(o | not known) = g · P(o | said right) + (1 − g) · P(o | said wrong)

Inconclusive outcomes are not used, so BKT sees the conclusive ones only:

    slip_eff  = P(wrong | knows) / (P(wrong | knows) + P(right | knows))
    guess_eff = P(right | not known) / (P(right | not known) + P(wrong | not known))

and the existing, tested `bkt.update` runs with `slip_eff` and `guess_eff`. When `slip_eff + guess_eff ≥ 1`
the outcome says nothing about the learner and the group gives no evidence. Dropping inconclusive outcomes loses
a little information (they are slightly more likely for one state than the other); that is the conservative
choice, and it is stated in the trace.

**The learner's own slip and guess** are assumptions until they can be fitted (`bkt_fit.py`, once enough
recordings exist): `s = 0.10`, `g = 0.25` for every group, in one place, named as assumptions in the trace.

**One observation per group per recording, as now:** the group's first target sound in the sentence. If that one is
inconclusive, the group gets no observation from this recording (picking another target would choose the evidence).

## Not in this step
Deletions as their own outcome (3.6b, with the benchmark); the L2-ARCTIC Vietnamese speakers (3.6b, after the
owner reads its licence); calibration on Vietnamese speakers (3.6c); fine-tuning (3.6d, only if 3.6c fails).

## Tasks
- [x] T1 `evidence.py`: `outcome`, `effective` (the two-layer model), the learner assumptions; unit tests including
  the formulas, the degenerate case and that a perfect detector gives back the learner's own slip and guess.
- [x] T2 `thresholds.py`: `accept`, the outcome counts by truth on the check half, the conclusive share, the new
  pass rule; tests.
- [x] T3 `marks.py`: the applied file carries `threshold`, `accept` and the four rates; `observations` returns
  conclusive outcomes only; `analysis.apply_evidence` uses `effective`; the trace explains both layers in Vietnamese;
  `/phat-am` shows inconclusive sounds as "chưa chắc".
