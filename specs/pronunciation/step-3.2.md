# Step 3.2: the recogniser service, alignment and goodness of pronunciation

Part of phase 3 (`spec.md`); the owner approved the model on 17 Nov 2026. This step builds the service and measures it on
the owner-free public data later (3.2b); nothing is shown to learners until step 3.3's thresholds and the gate.

## The service (`pronunciation/`, compose profile `pronunciation`)
- **Model:** `facebook/wav2vec2-xlsr-53-espeak-cv-ft` at commit `2c733782da5604684829819a5eb744c193fe9398` (Apache-2.0 on its
  card; trained on Common Voice; outputs eSpeak-style IPA phones, one frame per 20 ms). Every file is pinned by SHA-256
  (`config.json`, `preprocessor_config.json`, `vocab.json`, `pytorch_model.bin` 1.26 GB) and downloaded once into a volume;
  the service refuses a changed file. The weights are a PyTorch pickle: loaded by transformers with `weights_only`, and the
  pin guarantees it is the file that was read. Same libraries as the scorer service (`torch` CPU, `transformers`).
- **`torchaudio` is not used** although it was approved: its latest release (2.11.1) is behind the project's `torch` 2.15, so
  the two would not install together. CTC forced alignment is written as plain code instead (a Viterbi pass over the CTC
  trellis), with unit tests.
- **`POST /recognise`** (16 kHz mono 16-bit WAV) returns the phones heard. **`POST /score`** `{audio (base64 WAV), phones}`
  aligns the expected phones to the audio and returns, per phone, its time span, its GOP and the best competing phone.
- **GOP:** for each expected phone, the mean over its aligned frames of log P(expected) minus log P(best other phone); 0 or
  above means the expected phone was the most likely. It is a measurement, not a verdict: thresholds per target sound come
  from the owner's labelled recordings (3.3), and marks only after the gate.

## 3.2b: evaluation on speechocean762 (run 17 Nov 2026)
`python -m nodetrail_pron.evaluate <corpus> --model <pinned files> --out evals/baselines/pronunciation-speechocean762.json`
(`nodetrail_pron/evaluate.py`). The corpus is downloaded by hand from OpenSLR SLR101 (CC BY 4.0) and is not committed;
only the metrics are. The experts' ARPAbet phones are mapped to the model's IPA. The run used the test half: 2,500
sentences, none skipped, 29 minutes on 4 CPU cores.

| Measure | Result |
|---|---|
| Sentence level: Pearson r of mean GOP with the experts' accuracy (0–10) | **0.593** (95% CI 0.567–0.617) |
| Phone level: AUC of GOP for the experts' mispronounced phones (accuracy < 1 of 2) | **0.855** |
| Phones scored wrong by the experts | 1,978 of 47,369 (4.2%) |

| Flag when GOP < | Flagged | Precision | Recall | False-alarm share |
|---|---|---|---|---|
| −4 | 5,194 | 0.209 | 0.548 | 0.791 |
| −2 | 10,556 | 0.144 | 0.768 | 0.856 |
| −1 | 13,250 | 0.124 | 0.833 | 0.876 |
| 0 | 15,848 | 0.109 | 0.876 | 0.891 |

**What this says.**
- **The machinery works.** It needs no training on this corpus, and its GOP ranks the experts' mispronounced phones well
  (AUC 0.86). It also tracks their sentence scores (r 0.59).
- **One threshold for every phone is far from the gate.** Even at −4, about 4 in 5 flags fall on phones the experts
  scored as fine. That fits a corpus where only 4% of phones are wrong: a good ranking still gives many false flags.
  The gate (false alarms ≤ 10%) therefore depends on these steps:
  - judging only target sounds;
  - thresholds per sound group;
  - marking only when a competing phone was heard (3.4);
  - and, if needed, fine-tuning (3.5).
- **These speakers are Mandarin-speaking children and adults.** The owner's labelled recordings (3.3b) decide the gate,
  not these numbers.

## Not in this PR
The API's client and the canonical phones per prompt (3.3).
