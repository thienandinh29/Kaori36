"""POST /speak {text, pace} -> audio/wav; GET /health.

    TTS_VOICE=en_GB-cori-high TTS_PATH=en/en_GB/cori/high TTS_REVISION=<commit> \
    TTS_MODEL_SHA256=... TTS_CONFIG_SHA256=... python -m nodetrail_tts.server

The voice is downloaded once into TTS_CACHE (a volume) and checked against the pin. Reachable only
inside the compose network; the API forwards learners' requests (specs/speech, S2).
"""

import os
import unicodedata
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from nodetrail_tts.voice import Pace, Pin, Speaker, fetch

MAX_CHARS = 300  # a word, a phrase or a sentence; the web hides the button above this


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


def create_app(pin: Pin, speak: Callable[[str, Pace], bytes]) -> FastAPI:
    app = FastAPI(title="NodeTrail tts", docs_url=None, redoc_url=None)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "voice": pin.voice, "revision": pin.revision}

    @app.post("/speak")
    def speak_text(body: SpeakIn) -> Response:
        return Response(
            content=speak(body.text, body.pace),
            media_type="audio/wav",
            headers={"X-Voice": pin.voice},
        )

    return app


def main() -> None:
    import uvicorn

    pin = Pin.from_env()
    speaker = Speaker(fetch(pin, Path(os.environ.get("TTS_CACHE", "/models"))))
    uvicorn.run(create_app(pin, speaker), host=os.environ.get("TTS_HOST", "127.0.0.1"),
                port=int(os.environ.get("TTS_PORT", "8030")))  # fmt: skip


if __name__ == "__main__":
    main()
