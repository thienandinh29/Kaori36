"""Routes for the reviewer portal (specs/validation/step-v2.md).

The token is a header, never a URL.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Header, Path

from app.services.review_portal import PortalLabel, ReviewPortal

Token = Annotated[str | None, Header(alias="X-Reviewer-Token", max_length=100)]
BatchId = Annotated[str, Path(max_length=36)]


def create_router(portal: ReviewPortal) -> APIRouter:
    router = APIRouter(tags=["validation"])

    @router.get("/review/me")
    def me(token: Token = None) -> dict[str, Any]:
        return portal.me(token)

    @router.get("/review/batches/{batch_id}/next")
    def next_item(batch_id: BatchId, token: Token = None) -> dict[str, Any]:
        return portal.next(token, batch_id)

    @router.post("/review/batches/{batch_id}/items/{content_id}")
    def label(
        batch_id: BatchId,
        content_id: Annotated[str, Path(max_length=200)],
        body: PortalLabel,
        token: Token = None,
    ) -> dict[str, Any]:
        return portal.label(token, batch_id, content_id, body)

    return router
