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

## Not in this PR
The evaluation tool on speechocean762 (3.2b: ARPAbet to the model's phones, sentence-level correlation with the experts,
phone-level detection), the API's client and the canonical phones per prompt (3.3).
