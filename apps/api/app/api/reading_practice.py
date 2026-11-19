"""Routes for Reading practice (specs/listening-reading/step-4.3.md, plan CP4)."""

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, ConfigDict, Field

from app.services.reading_practice import ReadingPractice

Slug = Annotated[str, Path(max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]


class ReadingAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    learner_id: str = Field(min_length=1, max_length=200)
    # TFNG text, an option index, typed words, or paragraph -> heading index
    answer: str | int | dict[str, int]


def create_router(practice: ReadingPractice) -> APIRouter:
    router = APIRouter(tags=["reading"])

    @router.get("/reading/texts")
    def texts(learner_id: str = Query(min_length=1, max_length=200)) -> dict[str, Any]:
        return practice.texts(learner_id)

    @router.get("/reading/texts/{slug}")
    def text(slug: Slug, learner_id: str = Query(min_length=1, max_length=200)) -> dict[str, Any]:
        return practice.text(learner_id, slug)

    @router.post("/reading/items/{item_id}/answer")
    def answer(
        body: ReadingAnswer, item_id: Annotated[str, Path(max_length=120)]
    ) -> dict[str, Any]:
        answer: str | int | dict[int, int] = body.answer  # type: ignore[assignment]
        if isinstance(body.answer, str):
            answer = body.answer[:200]
        elif isinstance(body.answer, dict):  # JSON keys are strings; the key uses paragraph ints
            try:
                answer = {int(k): v for k, v in body.answer.items()}
            except ValueError:
                raise HTTPException(422, "Mã đoạn không hợp lệ.") from None
        return practice.answer(body.learner_id, item_id, answer)

    return router
