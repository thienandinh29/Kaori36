# Step 3.5: learning from expert labels (optional)

Part of `spec.md` (phase 3). 3.2b showed that GOP ranks wrong phones well (AUC 0.855 on speechocean762). Even so, any single
threshold flags mostly correct phones (a false-alarm share of 79–89%). This step asks whether learning from expert
labels helps. It starts with the cheapest test.

## 3.5a: a learned detector on the frozen model (built; CPU)
`pronunciation/nodetrail_pron/learn.py`, with the features in `features.py`.

**What it does.** The recogniser stays as pinned. For every phone in speechocean762 it records:
- GOP;
- the mean log-probability of the expected phone;
- the worst frame's margin;
- the share of frames the expected phone wins;
- the log of the duration;
- the phone's identity.

It then fits a class-weighted, L2 logistic regression on the **train** half (2,500 sentences) and compares it with plain
GOP on the **test** half.

**How the comparison is fair.** Both methods get thresholds chosen on the train half, aiming at a recall of 25%, 50%
and 75%. Those thresholds are applied unchanged to the test half, which is never used to tune. The report gives AUC,
precision and the false-alarm share for each method.

**What is committed.** The metrics and the fitted coefficients, in `evals/baselines/pronunciation-learned.json`: a few
hundred numbers derived from the corpus, which is CC BY 4.0 and attributed. The corpus is not committed.

**What it can and cannot show.** It shows whether information beyond GOP separates the experts' wrong phones. It does
not show that the gain carries over to Vietnamese speakers; only the owner's labels (3.3b) can. The product keeps using
GOP and the owner's thresholds unless a later step wires the detector into the service. That later step would:
- add a `p_wrong` field in `/score`;
- choose thresholds on it from the owner's labels, as for GOP;
- run only if the test-half gain is clear.

Wiring it in would be its own PR.

**Result (17 Nov 2026).** Train half: 47,076 phones, 2,564 scored wrong by the experts. Test half: 47,369 phones,
1,978 wrong. The run took 38 minutes on 4 CPU cores. Thresholds were chosen on the train half for a target recall, then
measured on the test half:

| | AUC | Recall ≈ 25%: false-alarm share | Recall ≈ 50% | Recall 75% |
|---|---|---|---|---|
| GOP | 0.855 | 0.631 (recall 0.201) | 0.758 (recall 0.459) | 0.852 |
| Learned detector | **0.893** | **0.461** (recall 0.239) | **0.613** (recall 0.486) | **0.787** |

- **Learning helps.** At the same recall it raises the share of flags that are real mistakes, for example from 37% to
  54% at about a quarter of the mistakes caught. The expected phone's mean log-probability carries most of the weight
  (standardised coefficient −1.32, against −0.05 for GOP).
- **It is still far from the gate.** Even at a quarter of the mistakes, about 46% of flags fall on correct phones. On
  this corpus, no single cut on these features reaches 10% false alarms at a useful recall.
- **What the 10% gate still rests on:**
  - a much lower recall, flagging only the most certain cases;
  - target sounds only, for Vietnamese speakers;
  - the competitor rule;
  - the owner's own labels, which decide.
- **Coefficients.** They are in `evals/baselines/pronunciation-learned.json`. Wiring them into the service as
  `p_wrong` would be its own PR, and only if the owner's labels show the same gain.

## 3.5b: fine-tuning the recogniser (not built; needs a GPU)
Fine-tuning the 300M-parameter model on the train half's audio would take days on the project's 4-core machines. It
belongs on a GPU notebook (Colab or Kaggle), run by the owner.
- **Build when:** 3.5a shows that features of the frozen model cannot separate the cases, for example if the learned
  detector barely beats GOP. The gap would then be in the model itself.
- **What the notebook would hold:** a script that fine-tunes on the train half with the canonical phones as CTC
  targets. It would be evaluated with `evaluate.py` on the test half.
- **Pins and licence:** new weights would be pinned like the current ones, and a fine-tuned model would carry the
  corpus's attribution.
- **Owner approval needed for:** the GPU time, and replacing a pinned model.
