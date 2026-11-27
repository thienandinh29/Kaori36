"""Routes for Reading tests taken outside the app (specs/listening-reading/step-4.3d.md)."""

from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Path, Query, Response
from pydantic import BaseModel, ConfigDict, Field

from app.reading import own_test as ot
from app.services.reading_own import OwnTests

TestId = Annotated[str, Path(pattern=r"^[0-9a-f-]{36}$")]
Learner = Query(min_length=1, max_length=200)


class OwnTestIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    learner_id: str = Field(min_length=1, max_length=200)
    consent: str = Field(max_length=40)
    passage: str = Field(max_length=ot.MAX_PASSAGE_CHARS + 2000)  # trimmed, then checked again
    questions: str = Field(max_length=ot.MAX_QUESTIONS_CHARS + 1000)
    key: str = Field(max_length=ot.MAX_KEY_CHARS + 200)
    answers: str = Field(max_length=ot.MAX_KEY_CHARS + 200)
    progress_test: bool = False


class QuestionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    number: int = Field(ge=1, le=60)
    kind: Literal["tfng", "ynng", "mcq", "completion", "unsupported"]
    text: str = Field(max_length=1000)
    options: list[Annotated[str, Field(max_length=400)]] = Field(default_factory=list,
                                                                 max_length=8)  # fmt: skip
    max_words: int | None = Field(default=None, ge=1, le=5)
    key: str | None = Field(default=None, max_length=200)
    mark: Literal["guessed", "no_time"] | None = None  # the learner's own: "đoán", "không kịp"


class ConfirmIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    learner_id: str = Field(min_length=1, max_length=200)
    questions: list[QuestionIn] = Field(max_length=40)
    position: int | None = Field(default=None, ge=1, le=3)  # the passage's place in the test


class KeepWordsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    learner_id: str = Field(min_length=1, max_length=200)
    forms: list[Annotated[str, Field(min_length=1, max_length=60)]] = Field(
        min_length=1, max_length=40
    )


class OwnTestQueued(BaseModel):
    id: str
    status: str


class OwnTestSummary(BaseModel):
    id: str
    status: str
    submitted_at: datetime
    correct: int | None
    total: int | None
    opening: str


def create_router(service: OwnTests) -> APIRouter:
    router = APIRouter(tags=["reading"])

    @router.post("/reading/own-tests", status_code=202)
    def submit(body: OwnTestIn) -> OwnTestQueued:
        tid = service.submit(
            body.learner_id, body.consent, body.passage, body.questions, body.key, body.answers,
            progress_test=body.progress_test,
        )  # fmt: skip
        return OwnTestQueued(id=tid, status="queued")

    @router.get("/reading/own-tests")
    def tests(learner_id: str = Learner) -> list[OwnTestSummary]:
        return [OwnTestSummary(**t) for t in service.listing(learner_id)]

    @router.get("/reading/own-tests/summary")
    def summary(learner_id: str = Learner) -> dict[str, Any]:
        return service.summary(learner_id)

    @router.get("/reading/own-tests/{test_id}")
    def test(test_id: TestId, learner_id: str = Learner) -> dict[str, Any]:
        return service.get(learner_id, test_id)

    @router.post("/reading/own-tests/{test_id}/confirm")
    def confirm(test_id: TestId, body: ConfirmIn) -> dict[str, Any]:
        return service.confirm(
            body.learner_id, test_id, [q.model_dump() for q in body.questions], body.position
        )

    @router.get("/reading/own-tests/{test_id}/words")
    def words(test_id: TestId, learner_id: str = Learner) -> dict[str, Any]:
        return service.words(learner_id, test_id)

    @router.post("/reading/own-tests/{test_id}/words")
    def keep_words(test_id: TestId, body: KeepWordsIn) -> dict[str, Any]:
        return service.keep_words(body.learner_id, test_id, body.forms)

    @router.delete("/reading/own-tests/{test_id}", status_code=204)
    def delete(test_id: TestId, learner_id: str = Learner) -> Response:
        service.delete(learner_id, test_id)
        return Response(status_code=204)

    return router
