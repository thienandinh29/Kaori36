# Pronunciation service

Phone recognition, CTC forced alignment and goodness of pronunciation (`specs/pronunciation/step-3.2.md`). It measures; it
never judges a learner by itself: thresholds and marks are decided by the API from measured rates (step 3.3 and the gate).

- Model: `facebook/wav2vec2-xlsr-53-espeak-cv-ft` at commit `2c733782…` (Apache-2.0 on its card), every file pinned by
  SHA-256 in `docker-compose.yml`; the service refuses to start without the full pin or when a file differs.
- Start: `docker compose --profile pronunciation up -d pronunciation`. The first start downloads about 1.3 GB into the
  `pronunciation-models` volume. On a 4 GB Docker VM, run it without the `writing` and `scoring` profiles.
- `POST /recognise` (WAV body) → `{"phones": [...], "frames": n}`; `POST /score` `{"audio": base64 WAV, "phones": [...]}` →
  per phone: `start_ms`, `end_ms`, `gop`, `competitor`.
- Tests use a fake recogniser and hand-made probability matrices: `uv run pytest -q`. The real model is checked by hand; the
  measurements are below.

## Measured (17 Nov 2026, the agent's sandbox, 4 CPU cores)
- Load 21 s; peak memory about 1.9 GB (hence `mem_limit` 3 GB); 0.4 s for a 2.4 s sentence after the first call, 2.2 s for
  15 s of audio.
- Two Piper (`en_GB-cori-high`) sentences: the phones heard matched the expected ones except where the expected phones were
  wrong for the voice: "at" said with the weak /ə/ (expected /æ/), "shop" with a British vowel (expected the American /ɑː/
  from espeak `en-us`), and "third" heard as /æ/. Lesson for step 3.3: the canonical phones of each prompt must be British
  and allow weak forms, and only the target sounds are judged.
