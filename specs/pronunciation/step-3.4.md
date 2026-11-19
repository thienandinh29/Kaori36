# Step 3.4: marks and the observation model

Part of `spec.md` (phase 3). It builds on the thresholds from 3.3b. 3.4a and 3.4b are built here.

## 3.4a: marks (built)
**Applied thresholds** (`data/pronunciation/thresholds.json`) are what the product reads. They are written only by an
explicit owner step after reading the 3.3b report:

`uv run python -m app.pronunciation.thresholds --out ../../evals/baselines/pronunciation-thresholds.json --apply ../../data/pronunciation/thresholds.json`

Only groups whose verdict is `pass` are applied. For each group the file stores:
- the threshold;
- `slip` and `guess`;
- the number of labelled sounds behind the numbers;
- the date.

The file does not exist yet, so **no sound is marked for anyone**. That is the gate. The API and the worker read it at
start, so restart both after applying: `docker compose restart api worker`.

**The mark rule** (`app/pronunciation/marks.py`, pure). A target sound is marked only when all three hold:
- its group is applied;
- its GOP is below the group's threshold;
- the recogniser heard a competing phone.

Any other sound is unmarked, which means "not sure", never "right". No total score.

**The observation model.** BKT treats an unmarked sound as a correct observation.
> **Superseded by `step-3.6a.md` (19 Nov):** these were the detector's error rates, not the learner's slip and guess,
> and an unmarked sound counted as right. Now three outcomes (right, wrong, inconclusive) and an observation model
> that combines both layers. Kept below for history.

- **slip = P(marked | said right)**, the false-positive rate on the check half.
- **guess = P(unmarked | said wrong)**, the miss rate (1 − recall).

A group with slip + guess ≥ 1 gets no BKT parameters and gives no evidence: a mark would then say nothing about the
learner. The marks are still shown.

**What the owner sees.** `GET /recordings/{id}` adds `marks` (target indexes). On `/phat-am`, the sentence is shown
with marked words underlined and the sound named, plus the sound's Vietnamese tip if `sounds.yaml` has one
(`tip_vi`, the owner's work; empty until written). The label says "chưa kiểm chứng". Recording is owner-only, so this is
too. While a recording is being labelled, marks stay hidden with the scores, so they cannot sway the labels.

## 3.4b: evidence into the roadmap (built)
**Where the nodes live.** The owner chose (17 Nov) one hidden node per sound group under a new pronunciation milestone.
They sit in **their own course**, `data/courses/english-pronunciation.yaml`: one milestone `pronunciation` and four
nodes `final-consonants`, `th`, `s-sh-ch-j-r-l`, `clusters-vowels`.
- Their slugs are the sound groups. The API and the worker refuse to start if the nodes and the groups differ.
- They are not in the grammar course. There, the level test awards a level only when every milestone at it is known,
  so an untestable pronunciation milestone would cap everyone's level, and grammar answers would be used to guess
  pronunciation.
- A new course modality `speech` (additive) marks objectives that are read aloud.

**One observation per group per recording**, in the worker, in the same transaction as the analysis:
- Which sound: the group's first target sound in the sentence. Not every sound, so a long sentence does not count many
  times. Not the worst one, so the measured per-sound slip and guess still describe it.
- How it is scored: unmarked counts as correct, marked as wrong.
- The update: BKT with that group's applied slip and guess, and `p_transit` 0.05 (reading aloud is a little practice;
  an initial choice until fitted).
- What is recorded:
  - the mastery;
  - a "Vì sao?" trace (`pronunciation.mark`, in Vietnamese, naming the word, the sound and the measured rates);
  - `analysis.evidence` on the recording.

Groups that are not applied, or that have no valid parameters, give no evidence. Until the owner applies thresholds,
**no node moves for anyone**.

**Progress.** `GET /pronunciation/prompts` adds `progress`: per node its name, `p_known` (null until it has evidence),
`known` (at the roadmap's 0.9) and `measured` (its group is applied). `/phat-am` shows "chưa kiểm chứng", "chưa có dữ
liệu", "đang luyện" or "đã vững", never a number.

## Not in this step
Red marks for anyone but the owner, a score as a number for learners, stress or intonation.
