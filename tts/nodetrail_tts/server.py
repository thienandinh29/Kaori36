"""POST /speak {text, pace} -> audio/wav; POST /phonemize {words} -> {ipa}; GET /health.

    TTS_VOICE=en_GB-cori-high TTS_PATH=en/en_GB/cori/high TTS_REVISION=<commit> \
    TTS_MODEL_SHA256=... TTS_CONFIG_SHA256=... python -m nodetrail_tts.server

The voice is downloaded once into TTS_CACHE (a volume) and checked against the pin. Reachable only
inside the compose network; the API forwards learners' requests (specs/speech, S2).
"""

import os
import threading
import unicodedata
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from nodetrail_tts.phonemes import VOICE, Phonemize, espeak
from nodetrail_tts.voice import Pace, Pin, Speaker, fetch

MAX_CHARS = 300  # a word, a phrase or a sentence; the web hides the button above this
# At most this many sentences are synthesised at once; others wait. A lesson skipped quickly sends a
# burst of requests, and unbounded parallel synthesis exceeded the container's memory (17 Nov 2026).
PARALLEL = int(os.environ.get("TTS_PARALLEL", "2"))
Word = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z' -]{0,39}$")]


class SpeakIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=MAX_CHARS)
    pace: Pace = "normal"

    @field_validator("text")
    @classmethod
    def _clean(cls, value: str) -> str:
        text = " ".join(unicodedata.normalize("NFC", value).split())
        if not any(c.isascii() and c.isalpha() for c in text):
            raise ValueError("nothing to speak")
        return text


class PhonemizeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    words: list[Word] = Field(min_length=1, max_length=100)


def create_app(
    pin: Pin, speak: Callable[[str, Pace], bytes], phonemize: Phonemize | None = None
) -> FastAPI:
    app = FastAPI(title="NodeTrail tts", docs_url=None, redoc_url=None)
    slots = threading.BoundedSemaphore(max(1, PARALLEL))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "voice": pin.voice, "revision": pin.revision}

    @app.post("/speak")
    def speak_text(body: SpeakIn) -> Response:
        with slots:
            audio = speak(body.text, body.pace)
        return Response(
            content=audio,
            media_type="audio/wav",
            headers={"X-Voice": pin.voice},
        )

    @app.post("/phonemize")
    def phonemize_words(body: PhonemizeIn) -> dict[str, object]:
        nonlocal phonemize
        if phonemize is None:
            phonemize = espeak()
        return {"voice": VOICE, "ipa": {w: phonemize(w) for w in body.words}}

    return app


def main() -> None:
    import uvicorn

    pin = Pin.from_env()
    speaker = Speaker(fetch(pin, Path(os.environ.get("TTS_CACHE", "/models"))))
    uvicorn.run(create_app(pin, speaker), host=os.environ.get("TTS_HOST", "127.0.0.1"),
                port=int(os.environ.get("TTS_PORT", "8030")))  # fmt: skip


if __name__ == "__main__":
    main()
