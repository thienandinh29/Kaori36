"""Routes for Listening practice (specs/listening-reading/step-4.4b.md, plan CP5)."""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Path, Query
from fastapi.responses import Response
from httpx import HTTPError
from pydantic import BaseModel, ConfigDict, Field

from app.services.listening_practice import ListeningPractice

Slug = Annotated[str, Path(max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
ItemId = Annotated[str, Path(max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]


class ListeningAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    learner_id: str = Field(min_length=1, max_length=200)
    answer: str = Field(max_length=400)


def create_router(practice: ListeningPractice) -> APIRouter:
    router = APIRouter(tags=["listening"])

    @router.get("/listening/texts")
    def texts(learner_id: str = Query(min_length=1, max_length=200)) -> dict[str, Any]:
        return practice.texts(learner_id)

    @router.get("/listening/texts/{slug}")
    def text(slug: Slug, learner_id: str = Query(min_length=1, max_length=200)) -> dict[str, Any]:
        return practice.text(learner_id, slug)

    @router.get("/listening/items/{item_id}/audio", responses={200: {"content": {"audio/wav": {}}}})
    async def audio(item_id: ItemId, pace: Literal["normal", "slow"] = "normal") -> Response:
        try:
            wav = await practice.audio(item_id, pace)
        except HTTPError:
            raise HTTPException(503, "Giọng đọc của máy chủ đang không trả lời.") from None
        return Response(
            wav, media_type="audio/wav", headers={"Cache-Control": "private, max-age=86400"}
        )

    @router.post("/listening/items/{item_id}/answer")
    def answer(body: ListeningAnswer, item_id: ItemId) -> dict[str, Any]:
        return practice.answer(body.learner_id, item_id, body.answer)

    return router
