"""Speaking routes (specs/speaking/step-5.4a.md): the examiner test, owner only."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field

from app.services.speaking_tests import MAX_ANSWER_BYTES, MAX_CHECK_BYTES, SpeakingTests

LEARNER = Query(min_length=1, max_length=200)


class StartIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    test_id: str = Field(pattern=r"^t\d{2}$")
    consent: str = Field(min_length=1, max_length=20)
    keep: bool = False


class PracticeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    test_id: str = Field(pattern=r"^t\d{2}$")
    question_id: str = Field(pattern=r"^p(1-\d-\d|2-long|2-closing|3-\d)$")
    consent: str = Field(min_length=1, max_length=20)
    keep: bool = False
    previous_id: str | None = Field(default=None, max_length=64)  # a try to repeat


async def _body(request: Request, limit: int) -> bytes | None:
    """The request body, or None once it passes the limit (read no further)."""
    data = bytearray()
    async for chunk in request.stream():
        data += chunk
        if len(data) > limit:
            return None
    return bytes(data)


def create_router(service: SpeakingTests) -> APIRouter:
    router = APIRouter(tags=["speaking"])

    @router.get("/speaking/tests")
    def overview(learner_id: str = LEARNER) -> dict[str, Any]:
        return service.overview(learner_id)

    @router.post("/speaking/tests")
    def start(body: StartIn, learner_id: str = LEARNER) -> dict[str, Any]:
        return service.start(learner_id, body.test_id, body.consent, body.keep)

    @router.post("/speaking/practice")
    def start_practice(body: PracticeIn, learner_id: str = LEARNER) -> dict[str, Any]:
        return service.start_practice(
            learner_id, body.test_id, body.question_id, body.consent, body.keep, body.previous_id
        )

    @router.get("/speaking/practice/{sitting_id}")
    def practice(sitting_id: str, learner_id: str = LEARNER) -> dict[str, Any]:
        return service.practice(learner_id, sitting_id)

    @router.post("/speaking/mic-check")
    async def mic_check(request: Request, learner_id: str = LEARNER) -> dict[str, Any]:
        audio = await _body(request, MAX_CHECK_BYTES)
        if audio is None:
            return {"ok": False, "problems": ["too_long"]}
        return await run_in_threadpool(service.mic_check, learner_id, audio)

    @router.post("/speaking/tests/{sitting_id}/answers")
    async def answer(
        sitting_id: str,
        request: Request,
        learner_id: str = LEARNER,
        question: str = Query(pattern=r"^p(1-\d-\d|2-long|2-closing|3-\d)$"),
    ) -> dict[str, Any]:
        audio = await _body(request, MAX_ANSWER_BYTES)
        if audio is None:
            raise HTTPException(413, "Bản ghi quá dài.")
        return await run_in_threadpool(service.answer, learner_id, sitting_id, question, audio)

    @router.post("/speaking/tests/{sitting_id}/finish")
    def finish(sitting_id: str, learner_id: str = LEARNER) -> dict[str, Any]:
        return service.finish(learner_id, sitting_id)

    @router.get("/speaking/tests/{sitting_id}")
    def result(sitting_id: str, learner_id: str = LEARNER) -> dict[str, Any]:
        return service.result(learner_id, sitting_id)

    @router.delete("/speaking/tests/{sitting_id}", status_code=204)
    def delete(sitting_id: str, learner_id: str = LEARNER) -> Response:
        service.delete(learner_id, sitting_id)
        return Response(status_code=204)

    @router.get("/speaking/answers/{answer_id}/audio")
    def audio(answer_id: str, learner_id: str = LEARNER) -> Response:
        return Response(
            service.audio(learner_id, answer_id),
            media_type="audio/wav",
            headers={"Cache-Control": "no-store"},
        )

    return router
