"""Step 5.3b: asking for the model's feedback, the worker step, and what the page gets back."""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool
from pydantic import BaseModel

from app.api import speaking as routes
from app.services.speaking_tests import CONSENT, SpeakingTests
from app.speaking.feedback import CONSENT as NOTICE
from app.speaking.feedback import FeedbackOut, PointOut
from app.speaking.feedback_job import (
    BUDGET,
    EMPTY,
    NO_MODEL,
    process_next_feedback,
    requeue_stuck,
)
from app.writing.model_calls import BudgetExceeded
from tests.pronunciation.test_recordings import speech_like

FOLDER = Path(__file__).resolve().parents[4] / "data" / "speaking" / "tests"
NOW = datetime(2026, 12, 1, 9, 0, tzinfo=UTC)
TEXT = "I think the city is very crowded and people walk to work every day because it is cheap."
LONG = {"short": False, "speaking_seconds": 24.0}


class Scripted:
    """A model that answers with a fixed feedback, or raises, and remembers what it was sent."""

    last_model = "scripted"

    def __init__(self, out: FeedbackOut | Exception) -> None:
        self.out = out
        self.calls: list[tuple[UUID, str, str, str]] = []

    def complete[T: BaseModel](
        self, learner: UUID, task: str, system: str, user: str, schema: type[T]
    ) -> T:
        self.calls.append((learner, task, system, user))
        if isinstance(self.out, Exception):
            raise self.out
        assert isinstance(self.out, schema)
        return self.out


def good() -> FeedbackOut:
    return FeedbackOut(
        points=[
            PointOut(
                kind="strength",
                area="answer",
                point_vi="Bạn đã đưa ra một lý do rõ ràng cho ý của mình.",
                quote="because it is cheap",
            ),
            PointOut(
                kind="issue",
                area="vocabulary",
                point_vi="Từ này hơi chung chung, có thể chọn từ cụ thể hơn.",
                quote="the city is very crowded",
                better="the city is packed",
            ),
            PointOut(  # a quote the learner never said: dropped by code
                kind="issue",
                area="grammar",
                point_vi="Chia động từ chưa đúng ở chỗ này nhé.",
                quote="she go to school",
                better="she goes to school",
            ),
        ]
    )


@pytest.fixture
def world(database_url: str) -> Iterator[tuple[TestClient, str, ConnectionPool, str, str]]:
    pool = ConnectionPool(database_url, open=True)
    with pool.connection() as conn:
        row = conn.execute(
            "insert into learners(display_name) values ('Owner') returning id"
        ).fetchone()
        assert row is not None
    owner = str(row[0])
    with pool.connection() as conn:
        conn.execute("delete from speaking_answers")  # the test database is shared: start empty
    app = FastAPI()
    app.include_router(
        routes.create_router(
            SpeakingTests(lambda: pool, FOLDER, owner, lambda: NOW, transcripts=True)
        )
    )
    client = TestClient(app)
    sitting = client.post(
        "/speaking/tests", params={"learner_id": owner}, json={"test_id": "t01", "consent": CONSENT}
    ).json()["id"]
    r = client.post(
        f"/speaking/tests/{sitting}/answers",
        params={"learner_id": owner, "question": "p1-1-1"},
        content=speech_like(),
    )
    assert r.status_code == 200, r.text
    answer = str(r.json()["id"])
    yield client, owner, pool, sitting, answer
    pool.close()


def transcribe(pool: ConnectionPool, answer: str, measures: dict[str, Any] | None = LONG) -> None:
    with pool.connection() as conn:
        conn.execute(
            "update speaking_answers set transcript_status='done', transcript=%s, measures=%s "
            "where id=%s",
            (Jsonb({"text": TEXT, "words": []}), Jsonb(measures) if measures else None, answer),
        )


def ask(client: TestClient, owner: str, answer: str, consent: str = NOTICE) -> Any:
    return client.post(
        f"/speaking/answers/{answer}/feedback",
        params={"learner_id": owner},
        json={"consent": consent},
    )


def feedback_of(client: TestClient, owner: str, sitting: str) -> dict[str, Any]:
    out = client.get(f"/speaking/tests/{sitting}", params={"learner_id": owner}).json()
    return next(q["answer"]["feedback"] for q in out["questions"] if q["answer"])


def test_asking_needs_the_owner_the_notice_a_transcript_and_enough_speech(world: Any) -> None:
    client, owner, pool, sitting, answer = world
    other = "00000000-0000-4000-8000-000000000bad"
    assert ask(client, other, answer).status_code == 403  # owner only for now
    assert ask(client, owner, answer, "speaking-feedback-v0").status_code == 422
    assert ask(client, owner, answer).status_code == 409  # no transcript yet
    transcribe(pool, answer, {"short": True, "speaking_seconds": 8.0})
    assert ask(client, owner, answer).status_code == 409  # under 15 s
    assert feedback_of(client, owner, sitting)["can_ask"] is False
    transcribe(pool, answer)
    assert feedback_of(client, owner, sitting)["can_ask"] is True
    first = ask(client, owner, answer)
    assert first.status_code == 202 and first.json() == {"status": "queued"}
    assert ask(client, owner, answer).json() == {"status": "queued"}  # not queued twice
    queued = feedback_of(client, owner, sitting)
    assert queued["status"] == "queued" and queued["can_ask"] is False
    assert ask(client, owner, "not-an-id").status_code == 404
    with pool.connection() as conn:
        row = conn.execute(
            "select feedback_consent, feedback_tries from speaking_answers where id=%s", (answer,)
        ).fetchone()
    assert row == (NOTICE, 1)


def test_the_worker_keeps_only_points_whose_quote_is_in_the_transcript(
    world: Any, database_url: str
) -> None:
    client, owner, pool, sitting, answer = world
    transcribe(pool, answer)
    assert process_next_feedback(database_url, Scripted(good())) is False  # nothing asked yet
    ask(client, owner, answer)
    model = Scripted(good())
    assert process_next_feedback(database_url, model) is True
    assert process_next_feedback(database_url, model) is False  # one answer, one call
    [(learner, task, _system, user)] = model.calls
    assert str(learner) == owner and task == "speaking_feedback"
    assert "Do you" in user and "p1-1-1" not in user  # the question text, not its id
    assert TEXT in user and "band" not in user.lower()
    fb = feedback_of(client, owner, sitting)
    assert fb["status"] == "done" and fb["can_ask"] is False
    assert [p["quote"] for p in fb["points"]] == ["because it is cheap", "the city is very crowded"]
    assert fb["points"][1]["better"] == "the city is packed"
    assert ask(client, owner, answer).json() == {"status": "done"}  # not asked again
    polled = client.get(f"/speaking/answers/{answer}/feedback", params={"learner_id": owner}).json()
    assert polled == fb  # what the waiting page reads
    stranger = "00000000-0000-4000-8000-000000000bad"
    assert (
        client.get(
            f"/speaking/answers/{answer}/feedback", params={"learner_id": stranger}
        ).status_code
        == 404
    )  # not another learner's answer
    with pool.connection() as conn:
        stored = conn.execute("select feedback from speaking_answers where id=%s", (answer,))
        data = stored.fetchone()
    assert data is not None and data[0]["dropped"] == 1 and data[0]["model"] == "scripted"


@pytest.mark.parametrize(
    ("model", "message"),
    [
        (None, NO_MODEL),
        (Scripted(BudgetExceeded()), BUDGET),
        (Scripted(FeedbackOut(points=[PointOut(
            kind="strength", area="answer", point_vi="Bạn trả lời đúng ý câu hỏi nhé.",
            quote="she goes to school")])), EMPTY),
    ],
)  # fmt: skip
def test_a_failed_request_says_why_and_may_be_asked_again_three_times(
    world: Any, database_url: str, model: Any, message: str
) -> None:
    client, owner, pool, sitting, answer = world
    transcribe(pool, answer)
    for tries in (1, 2, 3):
        assert ask(client, owner, answer).status_code == 202
        assert process_next_feedback(database_url, model) is True
        fb = feedback_of(client, owner, sitting)
        assert fb["status"] == "failed" and fb["failed"] == message and fb["points"] == []
        assert fb["can_ask"] is (tries < 3)
    assert ask(client, owner, answer).status_code == 409  # three tries spent


def test_an_unexpected_failure_is_stored_not_raised_and_stuck_work_is_queued_again(
    world: Any, database_url: str
) -> None:
    client, owner, pool, sitting, answer = world
    transcribe(pool, answer)
    ask(client, owner, answer)
    assert process_next_feedback(database_url, Scripted(RuntimeError("boom"))) is True
    assert feedback_of(client, owner, sitting)["status"] == "failed"
    ask(client, owner, answer)
    with pool.connection() as conn:  # a worker stopped in the middle of the call
        conn.execute("update speaking_answers set feedback_status='working' where id=%s", (answer,))
    assert requeue_stuck(database_url) == 1
    assert feedback_of(client, owner, sitting)["status"] == "queued"


def test_feedback_never_reaches_mastery_or_evidence(world: Any, database_url: str) -> None:
    client, owner, pool, _sitting, answer = world
    transcribe(pool, answer)
    with pool.connection() as conn:
        before = conn.execute("select count(*) from competency_observations").fetchone()
    ask(client, owner, answer)
    process_next_feedback(database_url, Scripted(good()))
    with pool.connection() as conn:
        after = conn.execute("select count(*) from competency_observations").fetchone()
    assert before == after
