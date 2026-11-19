"""Routes for saying a vocabulary word (specs/pronunciation/step-3.7.md)."""

from typing import Any

from fastapi import APIRouter, Query, Request

from app.services.word_say import WordSay

MAX_BYTES = 600_000  # 15 s of 16 kHz mono 16-bit WAV, as recordings


def create_router(service: WordSay) -> APIRouter:
    router = APIRouter(tags=["pronunciation"])

    @router.get("/vocab/say/status")
    def status(learner_id: str = Query(min_length=1, max_length=200)) -> dict[str, Any]:
        return service.status(learner_id)

    @router.get("/vocab/say/focus")
    def focus(learner_id: str = Query(min_length=1, max_length=200)) -> dict[str, Any]:
        return service.focus(learner_id)

    @router.post("/vocab/say")
    async def say(
        request: Request,
        learner_id: str = Query(min_length=1, max_length=200),
        word: str = Query(min_length=1, max_length=120),
        consent: str = Query(min_length=1, max_length=40),
    ) -> dict[str, Any]:
        audio = await request.body()
        if len(audio) > MAX_BYTES:
            return {"ok": False, "problems": ["too_long"], "phones": []}
        return await service.say(learner_id, word, consent, audio)

    return router
