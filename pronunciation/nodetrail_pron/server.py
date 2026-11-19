"""POST /recognise (WAV) and POST /score {audio, phones}; GET /health.

    PRON_MODEL=facebook/wav2vec2-xlsr-53-espeak-cv-ft PRON_REVISION=<commit> PRON_SHA256_...=... \
    python -m nodetrail_pron.server

Reachable only inside the compose network: the API forwards the owner's recordings (step 3.3).
Nothing here judges a learner: it returns aligned phones and their scores; thresholds and marks
are decided by the API on measured rates (specs/pronunciation).
"""

import base64
import binascii
import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from nodetrail_pron.align import AlignmentError, align, gop, greedy
from nodetrail_pron.model import BadAudio, Pin, Recogniser, fetch, read_wav

FRAME_MS = 20  # wav2vec2 emits one frame per 20 ms
MAX_BYTES = 600_000
Recognise = Callable[[list[float]], list[list[float]]]


class ScoreIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    audio: str = Field(min_length=1, max_length=900_000)  # base64 WAV
    phones: list[str] = Field(min_length=1, max_length=200)


def create_app(pin: Pin, recognise: Recognise, vocab: Mapping[str, int], blank: int) -> FastAPI:
    app = FastAPI(title="NodeTrail pronunciation", docs_url=None, redoc_url=None)
    names = {i: p for p, i in vocab.items()}

    def samples(data: bytes) -> list[float]:
        if len(data) > MAX_BYTES:
            raise HTTPException(413, "recording too long")
        try:
            return read_wav(data)
        except BadAudio as exc:
            raise HTTPException(422, str(exc)) from None

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "model": pin.repo, "revision": pin.revision}

    @app.post("/recognise")
    async def recognise_phones(request: Request) -> dict[str, Any]:
        lp = recognise(samples(await request.body()))
        return {"phones": [names[t] for t in greedy(lp, blank)], "frames": len(lp)}

    @app.post("/score")
    def score(body: ScoreIn) -> dict[str, Any]:
        unknown = sorted({p for p in body.phones if p not in vocab})
        if unknown:
            raise HTTPException(422, f"phones not in the model's vocabulary: {unknown}")
        try:
            data = base64.b64decode(body.audio, validate=True)
        except (binascii.Error, ValueError):
            raise HTTPException(422, "audio must be base64") from None
        lp = recognise(samples(data))
        try:
            segments = align(lp, [vocab[p] for p in body.phones], blank)
        except AlignmentError as exc:
            raise HTTPException(422, f"cannot align: {exc}") from None
        return {
            "recognised": [names[t] for t in greedy(lp, blank)],
            "phones": [
                {
                    "phone": names[s.token],
                    "start_ms": s.start * FRAME_MS,
                    "end_ms": s.end * FRAME_MS,
                    "gop": s.gop,
                    "competitor": names[s.competitor] if s.competitor is not None else None,
                    "peak": s.peak,
                    "other_peak": s.other_peak,
                }
                for s in gop(lp, segments, blank)
            ],
        }

    return app


def main() -> None:
    import uvicorn

    pin = Pin.from_env()
    folder = fetch(pin, Path(os.environ.get("PRON_CACHE", "/models")))
    model = Recogniser(folder)
    uvicorn.run(
        create_app(pin, model, model.vocab, model.blank),
        host=os.environ.get("PRON_HOST", "127.0.0.1"),
        port=int(os.environ.get("PRON_PORT", "8040")),
    )


if __name__ == "__main__":
    main()
