# NodeTrail ASR

Speech recognition for the Speaking test (`specs/speaking/step-5.1.md`): Whisper `small.en` through faster-whisper,
int8 on CPU, with the settings measured in `docs/v2/asr-candidates.md` (English-only, the verbatim prompt, no
conditioning on the previous window, voice activity detection, words under 50 ms dropped).

- Weights: `Systran/faster-whisper-small.en` (MIT; converted from `openai/whisper-small.en`, Apache-2.0), pinned by
  revision and SHA-256 in `docker-compose.yml`, downloaded once into the `asr-models` volume.
- Run: `COMPOSE_PROFILES=asr ASR_URL=http://asr:8050 docker compose up -d` (with the other profiles you use).
- `POST /transcribe` with a 16 kHz mono 16-bit WAV returns `{text, words: [{word, start, end, probability}]}`;
  `GET /health` answers 200 once the model is loaded.
- Checks: `uv run ruff check . && uv run ruff format --check . && uv run mypy . && uv run pytest -q`.
