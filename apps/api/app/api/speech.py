"""Hearing English (specs/speech, S2): the API forwards text to the self-hosted voice service.

`GET /speech/status` says whether a server voice is configured, so the web can choose it over the
browser's voice; `POST /speech {text, pace}` returns `audio/wav`. Without `TTS_URL` the status is
unavailable and speaking answers 503: the web then uses the browser's own voice (S1).
"""

import unicodedata
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_CHARS = 300  # the same limit as the web button and the tts service


class SpeechIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=MAX_CHARS)
    pace: Literal["normal", "slow"] = "normal"

    @field_validator("text")
    @classmethod
    def _clean(cls, value: str) -> str:
        text = " ".join(unicodedata.normalize("NFC", value).split())
        if not any(c.isascii() and c.isalpha() for c in text):
            raise ValueError("nothing to speak")
        return text


class SpeechStatus(BaseModel):
    available: bool
    voice: str | None


class SpeechClient:
    """Talks to the tts service; `transport` lets tests replace the network."""

    def __init__(
        self, url: str, *, timeout: float = 10.0, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self.url = url.rstrip("/")
        self.timeout = timeout
        self.transport = transport

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self.timeout, trust_env=False, transport=self.transport)

    async def voice(self) -> str | None:
        try:
            async with self._client() as client:
                r = await client.get(f"{self.url}/health")
            r.raise_for_status()
            return str(r.json()["voice"])
        except (httpx.HTTPError, KeyError, ValueError):
            return None

    async def speak(self, text: str, pace: str) -> bytes:
        async with self._client() as client:
            r = await client.post(f"{self.url}/speak", json={"text": text, "pace": pace})
        r.raise_for_status()
        if r.headers.get("content-type") != "audio/wav":
            raise httpx.HTTPError("the tts service did not return audio/wav")
        return r.content


def create_router(client: SpeechClient | None) -> APIRouter:
    router = APIRouter(tags=["speech"])

    @router.get("/speech/status")
    async def status() -> SpeechStatus:
        voice = await client.voice() if client else None
        return SpeechStatus(available=voice is not None, voice=voice)

    @router.post("/speech", responses={200: {"content": {"audio/wav": {}}}})
    async def speech(body: SpeechIn) -> Response:
        if client is None:
            raise HTTPException(503, "no server voice is configured")
        try:
            audio = await client.speak(body.text, body.pace)
        except httpx.HTTPError as exc:
            raise HTTPException(502, "the voice service did not answer") from exc
        return Response(
            content=audio,
            media_type="audio/wav",
            headers={"Cache-Control": "private, max-age=86400"},
        )

    return router
