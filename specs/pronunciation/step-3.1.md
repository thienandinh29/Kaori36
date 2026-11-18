# Step 3.1: recording, the quality check, consent, deletion

The owner's decisions (17 Nov 2026): the strict voice policy; the recogniser `facebook/wav2vec2-xlsr-53-espeak-cv-ft` with
`torchaudio` (step 3.2, in its own service); **all** target sound groups; one heavy compose profile at a time. The owner's
direction: first help learners pronounce correctly; later a simulated IELTS Speaking test that uses pronunciation and what the
learner says (phase 5, `specs/speaking/`).

## What is built here (no sound is judged yet)
- **Page `/phat-am`.** An authored sentence to read, the model voice to listen to (Piper), record, play back, send. The consent
  notice (version `voice-v1`) must be accepted first; a separate box "Giữ bản ghi để cải thiện hệ thống" is off by default.
- **In the browser:** the recording is mixed to mono, resampled to 16 kHz and written as 16-bit WAV, so the server needs no
  `ffmpeg`. Pure functions, unit-tested.
- **The quality check** (`app/pronunciation/quality.py`, standard library only): a WAV that is not 16 kHz mono 16-bit is refused;
  then length 1-15 s, too quiet (speech level), clipping, too noisy (speech level against the noise floor), no speech. A bad
  recording gets advice in Vietnamese and is **not stored**; it is never a judgement of the sound.
- **Storage and deletion** (migration 0021, `speech_recordings`): a good recording is stored on our own database until it is
  analysed. Until step 3.2 analyses recordings, a recording not marked "keep" is deleted after 24 hours (purged on every
  request and by the worker), and the learner can delete any recording at once. Kept recordings stay until the learner
  deletes them.
- **Who may record:** only the learners in `DRAFT_ITEM_LEARNERS` (the owner) until a privacy review; everyone else gets a
  Vietnamese explanation. No audio is sent to any third party.
- **Prompts:** `data/pronunciation/prompts.yaml`, short sentences written by the agent around the target sounds
  (`data/pronunciation/sounds.yaml`: final consonants, th, s/sh, ch/j, r/l, clusters, long and short vowels, /æ/ and /e/), status
  draft. Canonical phones per prompt come in step 3.3, reviewed by the owner.

## Routes
`GET /pronunciation/prompts`; `POST /recordings?learner_id&prompt_id&consent&keep` (body `audio/wav`, at most 600 KB) returns the
quality result and, when stored, the id and the deletion time; `GET /recordings?learner_id` (metadata only); `DELETE
/recordings/{id}?learner_id`.

## Checks
Unit tests of the WAV reader and every quality rule on synthetic signals; route tests (owner only, consent required, bad audio
not stored, delete, 24-hour purge, kept recordings kept); Vitest for the browser WAV encoder and resampler; a Playwright test
with Chromium's fake microphone.
