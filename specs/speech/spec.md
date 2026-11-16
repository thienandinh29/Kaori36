# Spec: hearing English (text to speech)

The owner's request (15 Nov 2026): a button that speaks a word, a phrase or a sentence. Two steps: the browser's own voice now,
a self-hosted model later. The button stays the same; only where the audio comes from changes.

## S1: the browser's voice (built in this step)
- A "Nghe" button (and "Nghe chậm", rate 0.7) next to English text: a word card's word and example; a saved phrase when it is
  shown as new, and the answer after grading. **Never on text the learner must produce** (a gap-fill's hidden answer, a question
  that is still open), so hearing it never gives the answer away.
- Uses the browser's `speechSynthesis`. Voice choice (`lib/english/speech.ts`, pure, tested): English only; British first, then
  American, then any English; on-device voices before network ones.
- **Privacy:** some browser voices are network services that receive the text. Word-list content (public) may use them; text
  from the learner's own essays (saved phrases) uses **on-device voices only**, and the button is hidden when there is none.
- No English voice, no `speechSynthesis`, or text over 300 characters: no button (nothing broken, nothing promised).
- Labelled "Giọng đọc máy" in the button's title: a machine voice, not a model of pronunciation.
- No route, no API change, no dependency, no migration.

## S2: a self-hosted voice (built 16 Nov 2026; choice in `docs/v2/tts-candidates.md`)
- **Choice (the owner asked the agent to choose):** Piper with `en_GB-cori-high`. Public-domain training audio
  (LibriVox, about 24 h), a light CPU runtime (onnxruntime; Kokoro would need PyTorch, Transformers and spaCy), fits the
  laptop. Measured: "important" in 0.18 s, a 10-word sentence in 0.46 s, about 200 MB in the container.
- **Service `tts/`** (compose profile `speech`, GPL-3.0-or-later because `piper-tts` is): `POST /speak {text, pace}` →
  `audio/wav`; the voice is pinned to one commit of `rhasspy/piper-voices` and both files by SHA-256 (refuses to start on a
  mismatch); the last 512 results are cached in memory.
- **API:** `GET /speech/status` (`{available, voice}`) and `POST /speech {text, pace}` forward to `TTS_URL`; without it the
  status is unavailable and speaking answers 503. The same text rules as the service (1–300 characters, some letters, NFC).
- **Web:** the button asks the status once per page; with a server voice it plays the server's audio (and keeps the last 100
  as object URLs), falling back to the browser's voice if a request fails; without one, S1 as before. The learner's own
  text may use the server voice: it never leaves NodeTrail.
- **Labelled** "Giọng đọc máy (Piper, giọng Anh)".

## Acceptance
Vitest: voice ranking (British, American, other English, on-device first, network refused for private text, none), text
preparation (NFC, whitespace, quotes, empty, too long). The button renders nothing without `speechSynthesis` (unit-tested
helper), and the existing browser tests still pass.
S2: the service's tests (validation, pin, download and checksum, cache, and the real voice when `TTS_TEST_MODEL` is set);
the API route with a fake service (status, audio, 422, 503, 502, a non-audio answer); the web's status and audio helpers;
the stack smoke check (WAV through the web proxy, or the browser-voice status without the service).
