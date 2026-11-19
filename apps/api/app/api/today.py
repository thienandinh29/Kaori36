"""Route for today's list (specs/two-layer-map/spec.md, M3)."""

from typing import Any

from fastapi import APIRouter, Query

from app.services.today import TodayService


def create_router(service: TodayService) -> APIRouter:
    router = APIRouter(tags=["today"])

    @router.get("/today")
    def today(
        learner_id: str = Query(min_length=1, max_length=200),
        minutes: int = Query(default=40, ge=10, le=180),
    ) -> dict[str, Any]:
        return service.today(learner_id, minutes)

    @router.get("/maps")
    def maps(learner_id: str = Query(min_length=1, max_length=200)) -> dict[str, Any]:
        return service.maps(learner_id)

    return router
