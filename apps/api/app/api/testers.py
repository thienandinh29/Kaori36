"""Tester routes (specs/speaking/step-5.5.md): redeem an invite link, who I am, the research notice.

The session is a token the web proxy keeps in an HttpOnly cookie and forwards in `X-Tester-Session`;
`redeem` returns it once, for the proxy to set, and the browser is never given it.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, ConfigDict, Field

from app.api.speaking import SESSION
from app.testers import store
from app.testers.limits import DailyLimits, used_today


class RedeemIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=20, max_length=80)


class ConsentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str = Field(min_length=1, max_length=20)


def create_router(
    pool: Callable[[], ConnectionPool],
    may_record: bool,
    limits: DailyLimits,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> APIRouter:
    router = APIRouter(tags=["testers"])

    def me(session: str | None) -> tuple[Any, dict[str, Any]]:
        with pool().connection() as conn:
            learner = store.session_learner(conn, session, clock())
            row = None if learner is None else store.info(conn, learner)
        if learner is None or row is None:
            raise HTTPException(401, "Hãy mở lại liên kết mời.")
        return learner, row

    @router.post("/testers/redeem")
    def redeem(body: RedeemIn) -> dict[str, Any]:
        with pool().connection() as conn:
            got = store.redeem(conn, body.token, clock())
            if got is None:
                raise HTTPException(
                    404, "Liên kết không dùng được: đã dùng, hết hạn hoặc đã bị thu hồi."
                )
            learner, session, label = got
            row = store.info(conn, learner)
        assert row is not None
        return {
            "learner_id": str(learner),
            "session": session,
            "label": label,
            "may_record": may_record,
            "research_notice": store.RESEARCH_NOTICE,
            "research_consented": row["research_consented"],
        }

    @router.get("/testers/me")
    def who(session: str | None = SESSION) -> dict[str, Any]:
        learner, row = me(session)
        with pool().connection() as conn:
            mocks, tries = used_today(conn, learner, clock())
        return {
            "learner_id": str(learner),
            "label": row["label"],
            "may_record": may_record,
            "research_notice": store.RESEARCH_NOTICE,
            "research_consented": row["research_consented"],
            "left_today": {
                "mock_tests": max(0, limits.mock_tests_per_day - mocks),
                "practice_tries": max(0, limits.practice_tries_per_day - tries),
            },
        }

    @router.post("/testers/research-consent", status_code=204)
    def consent(body: ConsentIn, session: str | None = SESSION) -> None:
        learner, _ = me(session)
        try:
            with pool().connection() as conn:
                store.research_consent(conn, learner, body.version, clock())
        except ValueError:
            raise HTTPException(422, "Thông báo này không có.") from None

    return router
