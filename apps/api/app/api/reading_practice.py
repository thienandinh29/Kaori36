"""Routes for Reading practice (specs/listening-reading/step-4.3.md, plan CP4)."""

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, ConfigDict, Field

from app.services.reading_practice import ReadingPractice

Slug = Annotated[str, Path(max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]


Answer = str | int | dict[str, int]  # TFNG text, an option index, typed words, paragraph -> heading


class ReadingAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    learner_id: str = Field(min_length=1, max_length=200)
    answer: Answer


class Learner(BaseModel):
    model_config = ConfigDict(extra="forbid")
    learner_id: str = Field(min_length=1, max_length=200)


class TestAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: Answer
    at_seconds: int | None = Field(default=None, ge=0, le=24 * 3600)


class TestSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    learner_id: str = Field(min_length=1, max_length=200)
    answers: dict[Annotated[str, Field(max_length=120)], TestAnswer] = Field(max_length=60)


def normalise(answer: Answer) -> str | int | dict[int, int]:
    """Strings capped; JSON keys are strings, but a headings key uses paragraph numbers."""
    if isinstance(answer, str):
        return answer[:200]
    if isinstance(answer, dict):
        try:
            return {int(k): v for k, v in answer.items()}
        except ValueError:
            raise HTTPException(422, "Mã đoạn không hợp lệ.") from None
    return answer


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
        return practice.answer(body.learner_id, item_id, normalise(body.answer))

    # Timed tests (specs/listening-reading/step-4.3b.md)
    @router.post("/reading/texts/{slug}/tests")
    def start_test(slug: Slug, body: Learner) -> dict[str, Any]:
        return practice.start_test(body.learner_id, slug)

    @router.post("/reading/tests/{test_id}/submit")
    def submit_test(
        body: TestSubmission,
        test_id: Annotated[str, Path(pattern=r"^[0-9a-f-]{36}$")],
    ) -> dict[str, Any]:
        answers = {k: (normalise(v.answer), v.at_seconds) for k, v in body.answers.items()}
        return practice.submit_test(body.learner_id, test_id, answers)

    return router
