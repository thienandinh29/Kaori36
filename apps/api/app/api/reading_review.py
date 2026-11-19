"""Routes for the owner's Reading review queue (specs/listening-reading/step-4.2c.md)."""

from typing import Annotated, Any

from fastapi import APIRouter, Path, Query

from app.services.reading_review import Decision, ReadingReview


def create_router(review: ReadingReview) -> APIRouter:
    router = APIRouter(tags=["reading"])

    @router.get("/reading/review")
    def queue(
        learner_id: str = Query(min_length=1, max_length=200),
        status: str = Query(default="needs_review", max_length=20),
    ) -> dict[str, Any]:
        return review.queue(learner_id, status)

    @router.get("/reading/review/texts")
    def texts(learner_id: str = Query(min_length=1, max_length=200)) -> dict[str, Any]:
        return review.texts(learner_id)

    @router.get("/reading/review/texts/{slug}")
    def text(
        slug: Annotated[str, Path(max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")],
        learner_id: str = Query(min_length=1, max_length=200),
    ) -> dict[str, Any]:
        return review.text_items(learner_id, slug)

    @router.post("/reading/review/{item_id}")
    def decide(
        item_id: str, body: Decision, learner_id: str = Query(min_length=1, max_length=200)
    ) -> dict[str, str]:
        return review.decide(learner_id, item_id, body)

    return router
