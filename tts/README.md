# tts: hearing English with one pinned voice

Speech step S2 (`specs/speech/spec.md`). `POST /speak {text, pace: normal|slow}` returns `audio/wav`;
`GET /health` names the voice. Only the API calls it, inside the compose network.

- **Engine:** [Piper](https://github.com/OHF-Voice/piper1-gpl) (`piper-tts` 1.8.0), CPU through onnxruntime.
- **Voice:** `en_GB-cori-high` from `rhasspy/piper-voices` at commit `e9ab671f2a0e50a701b34361136ba3e6a3a9eb0c`.
  - A British English female voice, trained on about 24 hours of **public-domain** LibriVox recordings (its model card).
  - Both files are pinned by SHA-256 in `docker-compose.yml`; the service refuses to start on a mismatch.
  - Why this voice: `docs/v2/tts-candidates.md`.
- **Measured:** load 0.7 s; "important" in 0.18 s; a 10-word sentence in 0.46 s (0.62 s slow); peak memory about 280 MB.
- **Cache:** the last 512 (text, pace) results, in memory.

## Licence: GPL-3.0-or-later
`piper-tts` is GPL-3.0-or-later (it includes espeak-ng). This folder imports it, so this service is licensed
GPL-3.0-or-later too. It is a separate program in its own container; the rest of NodeTrail (Apache-2.0) only sends it
HTTP requests and does not link to it. Anyone given this image can get its source from this folder.

## Run
`docker compose --profile speech up -d` and set `TTS_URL=http://tts:8030` in `.env`; without it the browser's own
voice is used (S1). Tests: `uv sync && uv run pytest` (the real-voice test runs with `TTS_TEST_MODEL=/path/to/voice.onnx`).
