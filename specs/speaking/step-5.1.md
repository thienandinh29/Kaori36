# Step 5.1: transcripts of the examiner test's answers, and the word error rate tool

Spec: `spec.md` ("Pipeline", "Recogniser settings"); measurements `docs/v2/asr-candidates.md`. **Owner's decision, 27 Nov 2026:
Whisper small.en**, through faster-whisper (CTranslate2, int8, no PyTorch), with the verbatim prompt. This step turns each
recorded answer of the examiner test (step 5.4a) into a transcript with word timings. Nothing is judged yet: measures come in
5.2, grammar and vocabulary in 5.3.

## What the learner sees
On the result page (`/noi/thi/{id}`), under each answer: the transcript, labelled "Máy chép lại, có thể sai". The label says
why it matters: the recogniser can mishear an accent and can quietly "correct" a learner's error, so the transcript is not
proof of what was said. While the worker has not reached an answer: "Đang chép lời…". Without the service: nothing changes.

## How it is built
- **Service `asr/`** (compose profile `asr`, `ASR_URL=http://asr:8050`): `POST /transcribe` takes the stored 16 kHz mono
  WAV and returns the text and each word with its start, end and probability; `GET /health`. Settings, each from the spec
  and measured on 19 Nov: English-only `small.en`, beam 5, the verbatim prompt, `condition_on_previous_text=False`, voice
  activity detection on (no text invented over silence), words shorter than 50 ms dropped. The weights
  (`Systran/faster-whisper-small.en`, MIT; from `openai/whisper-small.en`, Apache-2.0) are downloaded once into a volume
  at a pinned revision and checked against SHA-256 pins before loading; the service then runs offline.
- **Migration (additive):** on `speaking_answers`, `transcript jsonb` (text, words, model, revision) and
  `transcript_status` (`done` or `failed`), `transcribed_at`.
- **Worker:** when `ASR_URL` is set, one answer at a time: the oldest answer with audio and no transcript, sent to the
  service, the result stored. A failure is stored as `failed` with its reason and not retried in a loop; an unreachable
  service is retried after 30 seconds. Audio cleared after 24 hours before transcription stays untranscribed.
- **Privacy:** audio never leaves NodeTrail's own machines; the transcript is personal text kept with the sitting until the
  learner deletes it (it outlives the 24-hour audio, so the test's notice says so: consent `speaking-v1`). Nothing goes to
  a model provider in this step; 5.3 will need the transcript consent the spec names.
- **Word error rate tool** (`python -m app.speaking.wer`): the owner types what they said, word for word, for about 20
  answers (`data/private/speaking/references.jsonl`, `{"answer_id": "...", "reference": "..."}`, git-ignored). The tool
  reads the transcripts, normalises both sides (case, punctuation, numbers left as typed), and reports the pooled word error
  rate with a 95% bootstrap interval over answers, per-answer rates, and the same with fillers (um, uh, er, erm) removed.
  Only the metrics are committed (`evals/speaking/wer.json`).

## What is measured
- Built: unit tests for the service (settings, short-word drop, weight pins), the worker step and the API (status, owner
  only, deletion with the sitting), the WER maths (known pairs, the interval), the page (decoders).
- Run for real here: the service on CPU against recorded speech; speed and memory reported as this container's.
- The owner's: speed and memory on the laptop; the 20 typed references and the word error rate on them.

## Not claimed
That the transcript is what the learner said; any measure of fluency, grammar or vocabulary (5.2, 5.3); that the word error
rate on read synthetic speech in `asr-candidates.md` holds for the owner's spontaneous answers.

## Tasks
- [x] T1 Service `asr/`: server, settings, weight pins, Dockerfile, tests; compose profile `asr`; CI job `asr`
- [x] T2 Migration `0046` and worker step; API result with transcripts; tests
- [x] T3 The result page shows transcripts with the label; the notice gains the transcript sentence (`speaking-v1`)
- [x] T4 WER tool with tests
- [x] T5 Run the service for real; docs

## Built (27 Nov 2026)
- **Run for real in the cloud container:** the service with the pinned weights (`d1d751a`, four files checked against their
  pins) on 12.1 s of English synthesised by espeak-ng with planted errors and fillers: transcribed in 2.0 s (0.17 × real
  time; this machine, not the laptop), about 0.76 GB resident. Every planted error and filler kept ("I go", "I buy two
  cat", "We was", "Um", "uh"). Eight seconds of room noise gave an empty transcript. Then end to end: Chromium's fake
  microphone playing that speech, a test on `/noi/thi`, the worker, the service, and transcripts on the result page.
- **Choices made in building:** a transcript is kept until the sitting is deleted (personal text, like an essay); a
  refused answer is marked failed once and not retried; "Đang chép lời…" appears only when `ASR_URL` is set; the consent
  becomes `speaking-v1` with its own browser key, so `/phat-am`'s `voice-v1` is untouched; a ninth CI job (`asr`) brings
  CI to 18 checks.
- **Not measured:** the word error rate on real speech (the owner's references), speed and memory on the laptop, the
  service image build (CI builds it; this sandbox cannot reach package registries from inside image builds).
