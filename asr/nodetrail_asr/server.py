"""HTTP for the recogniser (specs/speaking/step-5.1.md): `POST /transcribe` (a WAV), `GET /health`.

The model loads in the background at start-up; until it is ready, both routes answer 503. One
transcription runs at a time: the model is the slow part, and the worker sends one answer at a time.
"""

import os
import threading
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any, Protocol

from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from nodetrail_asr.model import BadAudio, Recogniser, Settings

MAX_BYTES = 5_000_000  # a two-minute answer is about 3.9 MB


class Transcriber(Protocol):
    def transcribe(self, data: bytes) -> dict[str, Any]: ...


def create_app(load: Callable[[], Transcriber]) -> FastAPI:
    state: dict[str, Any] = {"model": None, "error": None}
    lock = threading.Lock()

    def _load() -> None:
        try:
            state["model"] = load()
        except Exception as exc:  # reported on /health; the container's health check fails
            state["error"] = f"{type(exc).__name__}: {exc}"

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        threading.Thread(target=_load, daemon=True).start()
        yield

    app = FastAPI(title="NodeTrail ASR", lifespan=lifespan)

    @app.get("/health")
    def health() -> dict[str, Any]:
        if state["model"] is None:
            raise HTTPException(503, state["error"] or "loading")
        return {"ready": True}

    @app.post("/transcribe")
    async def transcribe(request: Request) -> dict[str, Any]:
        model = state["model"]
        if model is None:
            raise HTTPException(503, state["error"] or "loading")
        data = bytearray()
        async for chunk in request.stream():
            data += chunk
            if len(data) > MAX_BYTES:
                raise HTTPException(413, "too long")

        def run() -> dict[str, Any]:
            with lock:
                return model.transcribe(bytes(data))  # type: ignore[no-any-return]

        try:
            return await run_in_threadpool(run)
        except BadAudio as exc:
            raise HTTPException(422, str(exc)) from None

    return app


def main() -> None:  # pragma: no cover - the container's entry point
    import uvicorn

    settings = Settings.from_env()
    app = create_app(lambda: Recogniser(settings))
    uvicorn.run(app, host=os.environ.get("ASR_HOST", "127.0.0.1"), port=8050)


if __name__ == "__main__":  # pragma: no cover
    main()
