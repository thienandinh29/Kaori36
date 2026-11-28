"""Step 5.5: the tester flow through the routes: the switch, the session, the limits, the report."""

from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg_pool import ConnectionPool

from app.api import speaking as speaking_routes
from app.api import testers as tester_routes
from app.services.speaking_tests import CONSENT, SpeakingTests
from app.testers import store
from app.testers.cli import collect
from app.testers.limits import DailyLimits
from app.testers.report import report
from tests.pronunciation.test_recordings import speech_like

FOLDER = Path(__file__).resolve().parents[4] / "data" / "speaking" / "tests"
NOW = datetime(2026, 12, 1, 9, 0, tzinfo=UTC)
LIMITS = DailyLimits(mock_tests_per_day=2, practice_tries_per_day=3)

Build = Callable[[bool], TestClient]


@pytest.fixture
def world(database_url: str) -> Iterator[tuple[Build, ConnectionPool, str]]:
    pool = ConnectionPool(database_url, open=True)
    with pool.connection() as conn:
        row = conn.execute(
            "insert into learners(display_name) values ('Owner') returning id"
        ).fetchone()
        assert row is not None
    owner = str(row[0])

    def build(may_record: bool) -> TestClient:
        app = FastAPI()
        service = SpeakingTests(
            lambda: pool, FOLDER, owner, lambda: NOW, testers_may_record=may_record, limits=LIMITS
        )
        app.include_router(speaking_routes.create_router(service))
        app.include_router(
            tester_routes.create_router(lambda: pool, may_record, LIMITS, lambda: NOW)
        )
        return TestClient(app)

    yield build, pool, owner
    pool.close()


def join(client: TestClient, pool: ConnectionPool, label: str) -> tuple[str, str]:
    """A tester signed in through an invite link: (learner id, session)."""
    with pool.connection() as conn:
        tester, _ = store.create_tester(conn, label)
        token = store.invite(conn, tester, NOW)
    r = client.post("/testers/redeem", json={"token": token})
    assert r.status_code == 200, r.text
    return r.json()["learner_id"], r.json()["session"]


def H(session: str | None) -> dict[str, str]:
    return {} if session is None else {"X-Tester-Session": session}


def start(client: TestClient, learner: str, session: str | None = None, mode: str = "exam") -> Any:
    if mode == "exam":
        return client.post(
            "/speaking/tests",
            params={"learner_id": learner},
            json={"test_id": "t01", "consent": CONSENT},
            headers=H(session),
        )
    return client.post(
        "/speaking/practice",
        params={"learner_id": learner},
        json={"test_id": "t01", "question_id": "p3-1", "consent": CONSENT},
        headers=H(session),
    )


def test_redeeming_an_invite_gives_a_session_once_and_me_says_what_is_left(world) -> None:  # type: ignore[no-untyped-def]
    build, pool, _ = world
    client = build(True)
    with pool.connection() as conn:
        tester, learner = store.create_tester(conn, "Mai")
        token = store.invite(conn, tester, NOW)
    r = client.post("/testers/redeem", json={"token": token}).json()
    assert r["learner_id"] == str(learner) and r["label"] == "Mai" and r["may_record"] is True
    assert len(r["session"]) >= 40 and r["research_notice"] == "research-v1"
    gone = client.post("/testers/redeem", json={"token": token})
    assert gone.status_code == 404 and "đã dùng" in gone.json()["detail"]
    me = client.get("/testers/me", headers=H(r["session"])).json()
    assert me["left_today"] == {"mock_tests": 2, "practice_tries": 3}
    assert client.get("/testers/me").status_code == 401
    assert client.get("/testers/me", headers=H("x" * 43)).status_code == 401
    assert client.post("/testers/redeem", json={"token": "short"}).status_code == 422


def test_while_the_switch_is_off_a_signed_in_tester_cannot_record_but_can_still_delete(
    world: Any,
) -> None:
    build, pool, owner = world
    on, off = build(True), build(False)
    learner, session = join(on, pool, "Mai")
    made = start(on, learner, session).json()["id"]  # recorded while it was on
    assert start(off, learner, session).status_code == 403  # shut: the owner-only notice
    seen = off.get("/speaking/tests", params={"learner_id": learner}, headers=H(session)).json()
    assert seen["can_record"] is False
    assert off.delete(f"/speaking/tests/{made}", params={"learner_id": learner},
                      headers=H(session)).status_code == 204  # own data can always go  # fmt: skip
    assert start(off, owner).status_code == 200  # the owner is not affected


def test_a_tester_needs_their_own_session_not_just_their_learner_id(world) -> None:  # type: ignore[no-untyped-def]
    build, pool, _ = world
    client = build(True)
    mai, mai_session = join(client, pool, "Mai")
    an, an_session = join(client, pool, "An")
    assert start(client, mai, mai_session).status_code == 200
    assert start(client, mai).status_code == 403  # the id alone is not enough
    assert start(client, mai, an_session).status_code == 403  # nor another tester's session
    assert start(client, an, mai_session).status_code == 403
    made = start(client, an, an_session).json()["id"]
    q = {"learner_id": an}
    assert client.get(f"/speaking/tests/{made}", params=q).status_code == 403
    assert client.get(f"/speaking/tests/{made}", params=q, headers=H(an_session)).status_code == 200
    assert client.delete(f"/speaking/tests/{made}", params=q).status_code == 403
    assert (
        client.delete(f"/speaking/tests/{made}", params=q, headers=H(mai_session)).status_code
        == 403
    )
    assert client.post("/speaking/mic-check", params=q, content=speech_like()).status_code == 403
    with pool.connection() as conn:  # switched off: the session ends at once
        info = store.info(conn, UUID(an))
        assert info is not None
        store.revoke(conn, info["id"], NOW)
    assert start(client, an, an_session).status_code == 403
    # a learner who is neither the owner nor a tester is refused as before
    nobody = "00000000-0000-4000-8000-000000000bad"
    refused = client.post(
        "/speaking/tests",
        params={"learner_id": nobody},
        json={"test_id": "t01", "consent": CONSENT},
    )
    assert refused.status_code == 403


def test_daily_limits_apply_to_testers_and_not_to_the_owner(world) -> None:  # type: ignore[no-untyped-def]
    build, pool, owner = world
    client = build(True)
    learner, session = join(client, pool, "Mai")
    assert [start(client, learner, session).status_code for _ in range(3)] == [200, 200, 429]
    refused = start(client, learner, session).json()["detail"]
    assert "2 bài" in refused and "Mai quay lại" in refused
    assert [start(client, learner, session, "guided").status_code for _ in range(4)] == [
        200, 200, 200, 429
    ]  # fmt: skip
    me = client.get("/testers/me", headers=H(session)).json()
    assert me["left_today"] == {"mock_tests": 0, "practice_tries": 0}
    left = client.get("/speaking/tests", params={"learner_id": learner}, headers=H(session)).json()
    assert left["left_today"] == {"mock_tests": 0, "practice_tries": 0}
    assert all(start(client, owner).status_code == 200 for _ in range(5))  # the owner is unlimited
    assert client.get("/speaking/tests", params={"learner_id": owner}).json()["left_today"] is None


def test_the_research_notice_and_the_report_from_real_rows(world) -> None:  # type: ignore[no-untyped-def]
    build, pool, _ = world
    client = build(True)
    mai, mai_session = join(client, pool, "Mai")
    an, an_session = join(client, pool, "An")
    assert client.post("/testers/research-consent", json={"version": "research-v9"},
                       headers=H(mai_session)).status_code == 422  # fmt: skip
    assert (
        client.post("/testers/research-consent", json={"version": "research-v1"}).status_code == 401
    )
    assert client.post("/testers/research-consent", json={"version": "research-v1"},
                       headers=H(mai_session)).status_code == 204  # fmt: skip
    for learner, session in ((mai, mai_session), (an, an_session)):
        sitting = start(client, learner, session).json()["id"]
        r = client.post(f"/speaking/tests/{sitting}/answers",
                        params={"learner_id": learner, "question": "p1-1-1"},
                        content=speech_like(), headers=H(session))  # fmt: skip
        assert r.status_code == 200
        with pool.connection() as conn:  # as the worker would have measured it
            conn.execute(
                "update speaking_answers set measures=%s where id=%s",
                (psycopg_json({"words": 30, "speech_rate": 100.0, "pauses": {"per_minute": 8.0}}),
                 r.json()["id"]),
            )  # fmt: skip
    with pool.connection() as conn:
        out = report(*collect(conn), date(2026, 12, 2))
    by = {t["label"]: t for t in out["testers"]}
    assert by["Mai"]["mock_tests"] == 1 and by["An"]["mock_tests"] == 1
    assert by["Mai"]["weekly_numbers"][0]["median_speech_rate"] == 100.0  # consented
    assert "weekly_numbers" not in by["An"]  # did not accept the notice
    assert not {"audio", "transcript", "text", "words"} & keys(out)  # no data of what was said
    assert out["retention"]["eligible"] == 0  # the first day is yesterday: too new


def keys(value: Any) -> set[str]:
    """Every key anywhere in a nested report."""
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in keys(v)}
    return set()


def psycopg_json(value: object) -> Any:
    from psycopg.types.json import Jsonb

    return Jsonb(value)


def test_an_unfinished_day_boundary_does_not_count_yesterday(world) -> None:  # type: ignore[no-untyped-def]
    build, pool, _ = world
    client = build(True)
    learner, session = join(client, pool, "Mai")
    for _ in range(2):
        assert start(client, learner, session).status_code == 200
    with pool.connection() as conn:  # both started yesterday, Vietnam time
        conn.execute(
            "update speaking_tests set started_at=%s where learner_id=%s",
            (NOW - timedelta(days=1), learner),
        )
    assert start(client, learner, session).status_code == 200  # a fresh day, a fresh allowance
