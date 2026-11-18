"""Routes for FORGET-001's delayed grammar re-checks (specs/forget-001/spec.md)."""

from typing import Any

from fastapi import APIRouter, Path, Query
from pydantic import BaseModel, ConfigDict, Field

from app.services.rechecks import Rechecks


class RecheckAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    learner_id: str = Field(min_length=1, max_length=200)
    answer: str = Field(min_length=1, max_length=200)


def create_router(rechecks: Rechecks) -> APIRouter:
    router = APIRouter(tags=["research"])

    @router.get("/rechecks/next")
    def next_recheck(learner_id: str = Query(min_length=1, max_length=200)) -> dict[str, Any]:
        q = rechecks.next(learner_id)
        if q is None:
            return {"question": None}
        return {
            "question": {
                "id": q.id,
                "node": q.node,
                "node_name_vi": q.node_name_vi,
                "prompt": q.prompt,
                "options": q.options,
                "draft": q.draft,
            }
        }

    @router.post("/rechecks/{recheck_id}/answer")
    def answer(body: RecheckAnswer, recheck_id: str = Path(max_length=36)) -> dict[str, Any]:
        return rechecks.answer(body.learner_id, recheck_id, body.answer)

    return router
