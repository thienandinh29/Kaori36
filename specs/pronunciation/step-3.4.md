# Step 3.4: marks and the observation model

Part of `spec.md` (phase 3). It builds on the thresholds from 3.3b. 3.4a is built here. 3.4b (evidence into the roadmap)
waits for the owner's pronunciation nodes.

## 3.4a: marks (built)
**Applied thresholds** (`data/pronunciation/thresholds.json`) are what the product reads. They are written only by an
explicit owner step after reading the 3.3b report:

`uv run python -m app.pronunciation.thresholds --out ../../evals/baselines/pronunciation-thresholds.json --apply ../../data/pronunciation/thresholds.json`

Only groups whose verdict is `pass` are applied. For each group the file stores:
- the threshold;
- `slip` and `guess`;
- the number of labelled sounds behind the numbers;
- the date.

The file does not exist yet, so **no sound is marked for anyone**. That is the gate.

**The mark rule** (`app/pronunciation/marks.py`, pure). A target sound is marked only when all three hold:
- its group is applied;
- its GOP is below the group's threshold;
- the recogniser heard a competing phone.

Any other sound is unmarked, which means "not sure", never "right". No total score.

**The observation model.** BKT treats an unmarked sound as a correct observation.
- **slip = P(marked | said right)**, the false-positive rate on the check half.
- **guess = P(unmarked | said wrong)**, the miss rate (1 − recall).

A group with slip + guess ≥ 1 gets no BKT parameters and gives no evidence: a mark would then say nothing about the
learner. The marks are still shown.

**What the owner sees.** `GET /recordings/{id}` adds `marks` (target indexes). On `/phat-am`, the sentence is shown
with marked words underlined and the sound named, plus the sound's Vietnamese tip if `sounds.yaml` has one
(`tip_vi`, the owner's work; empty until written). The label says "chưa kiểm chứng". Recording is owner-only, so this is
too. While a recording is being labelled, marks stay hidden with the scores, so they cannot sway the labels.

## 3.4b: evidence into the roadmap (next; needs the owner)
The owner adds one hidden node per target sound (or per group) under a pronunciation milestone in the course file. A
confident mark, or no mark, on a recording then updates that node's mastery with the group's slip and guess. This only
happens for applied groups with valid parameters.

## Not in this step
Red marks for anyone but the owner, a score as a number for learners, stress or intonation.
