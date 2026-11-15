# Spec: Pronunciation (phase 3 of `docs/v2/plan-english-pack.md`)

Document only: nothing here is built. The learner reads an authored sentence aloud; tools find which of a few target sounds were
probably mispronounced; the roadmap learns from it. The principle of the pack holds: **tools measure, the LLM never judges a
sound**, and nothing is shown as red until its false alarms have been measured on real recordings (the phase gate).

## What the learner sees
1. A short sentence to read (authored by the project, built around the target sounds), a record button, a retry.
2. A recording-quality check first ("quá ồn", "quá nhỏ", "quá ngắn"): a bad recording gets advice, never a judgement of the sound.
3. After analysis: the sentence with only the sounds the tools are *confident* about marked, each with a Vietnamese tip and a
   model recording to compare. A sound the tools are unsure about is not marked. No total score, no "accent" score.
4. Until the gate is met, marks are shown **only to the owner and labelled "chưa kiểm chứng"**.

## Pipeline (worker or a service; never inside a request)
audio (16 kHz mono WAV) → quality gate → phoneme recognition (a CTC model) → forced alignment of the prompt's canonical phones
→ goodness of pronunciation (GOP) per phone → thresholds per target sound → marks. Everything after recognition is plain code and
unit-tested on recorded outputs; only recognition needs a model.
- **Recognition model (candidate, the owner decides after reading it):** `facebook/wav2vec2-xlsr-53-espeak-cv-ft` (Apache-2.0 on its
  card; fine-tuned on Common Voice; weights 1.26 GB; revision `2c733782…`, 2021). A phoneme recogniser trained mostly on native
  speech may mis-hear non-native speech: that is exactly what the false-alarm measurement is for.
- **Canonical phones for a prompt:** authored once into the prompt file (reviewed by the owner), so the product needs no
  grapheme-to-phoneme tool at run time. espeak-ng (GPL-3.0) is therefore not a dependency.
- **GOP:** the usual log-posterior ratio of the canonical phone against its best competitor over the aligned segment, from the CTC
  posteriors; alignment with a CTC forced aligner. `torchaudio` is a new dependency (owner approval).
- **Target sounds:** 8–10 sounds Vietnamese speakers often miss. A starting list **from general knowledge of first-language
  transfer, not from a checked source; the owner, a native speaker, confirms or changes it:** final consonants (/t/ /k/ /p/ /s/ /z/
  dropped or changed), /θ/ and /ð/ (th → t, d, s), /ʃ/ against /s/, /tʃ/ against /dʒ/, consonant clusters (str-, -sts, -ngths),
  /r/ against /l/, vowel length (/iː/ against /ɪ/, /uː/ against /ʊ/), /æ/ against /e/.
- **Thresholds:** one per target sound, chosen on a development half of the owner's recordings, deliberately lenient, and checked on
  the other half. A mark needs both a GOP below the threshold and a recognised competing phone.

## Recording data and the owner's voice policy (decision needed before any recording)
A voice is personal data and may count as biometric data under Vietnam's personal data rules; this needs a privacy review before
anyone but the owner records (the same rule as essays). Proposed: audio is processed on our own machines (no third-party model API),
deleted after analysis by default, kept only if the learner opts in for evaluation, with its own consent notice and version, a
delete button, and no sharing. The first recordings are the owner's own.

## Evaluation and the gate
- **Public data, to test the machinery (not Vietnamese learners):** `mispeech/speechocean762` (Apache-2.0 on its card; 5,000
  sentences, 2,500 train and 2,500 test, 250 speakers half children; **all speakers' first language is Mandarin**; phone, word and
  sentence scores from five experts, with the pronounced phone where it differs). Report sentence-level PCC of the tools' score with
  the experts' accuracy score, and phone-level detection of the annotated mispronunciations (precision, recall, AUC). Fine-tuning on
  its train half is a later option (a GPU notebook), evaluated on its test half.
- **The gate (from the plan):** on **50–100 of the owner's own recordings**, listened to and labelled by the owner, the share of
  marked phones the owner judges correctly pronounced (the **false-alarm rate**) is **≤ 10%**, reported with an exact interval and per
  target sound; also the share of real mistakes marked (recall), which may be low. Until met, nothing is red for anyone else.
- A mismatch to remember: Mandarin-speaking children and adults are not Vietnamese adults, so a good PCC there says the code works,
  not that it works for the product's learners. The owner's recordings are the evidence that matters.

## The roadmap link
Each target sound is a hidden node (new nodes under a pronunciation milestone, in `data/courses/english-ielts.yaml`; the owner's
roadmap work). The observation model comes from the measured rates, not from guesses: **slip = the false-alarm rate** of that sound
(the tools say "wrong" though the learner said it right), **guess = the miss rate** (the tools say "right" though it was wrong).
Evidence moves a node only after the gate, and only for confident marks.

## Steps (each a PR with its own short spec)
| Step | Work | New pieces |
|---|---|---|
| 3.1 | Recording in the browser (resampled to 16 kHz mono WAV there, so the server needs no `ffmpeg`), the quality gate, consent, storage and deletion | migration; routes; web `/phat-am` |
| 3.2 | Recognition service, alignment, GOP; the evaluation tool on speechocean762 (PCC, detection) | `pronunciation/` service (compose profile), `torchaudio`; `evalkit/pronunciation_gate.py` |
| 3.3 | Target sounds, authored prompts with canonical phones, thresholds on the owner's recordings, the false-alarm measurement | `data/pronunciation/`; the owner's labelling sheet and scorer (like `writing_review`) |
| 3.4 | The roadmap nodes, observation parameters from the measured rates, marks in the UI (owner only until the gate) | course nodes; web feedback |
| 3.5 | Optional: fine-tune on speechocean762 train on a GPU notebook; compare on its test half | notebook; weights kept out of git |

## Limits and risks
Native-speech training data and non-native speakers; background noise and phone microphones; children; thresholds that depend on the
speaker; discouraging false marks (hence lenient thresholds and the unsure state); memory: the owner's Docker VM measured about 4 GB,
and this service plus LanguageTool plus the scorer will not all fit, so profiles run one at a time or on a GPU notebook until measured.
Not in this step: stress, intonation, fluency (phase 5), an accent or "native-like" score, any score shown as a number.
