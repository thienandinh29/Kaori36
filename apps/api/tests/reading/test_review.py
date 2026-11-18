"""Step 4.2c: the owner's review queue and the agreement report."""

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg_pool import ConnectionPool

from app.api import reading_review as routes
from app.reading import blind
from app.reading.agreement import report
from app.reading.pipeline import check_pending, generate_text
from app.services.reading_review import ReadingReview

from .test_generation import PASSAGE, generated

NOW = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)


@pytest.fixture
def stack(
    database_url: str, tmp_path: Path
) -> Iterator[tuple[TestClient, str, str, ConnectionPool, Path]]:
    pool = ConnectionPool(database_url, open=True)
    with pool.connection() as conn:
        ids = []
        for name in ("Owner", "Other"):
            row = conn.execute(
                "insert into learners(display_name) values (%s) returning id", (name,)
            ).fetchone()
            assert row is not None
            ids.append(str(row[0]))

        async def gen(system: str, text: str):  # type: ignore[no-untyped-def]
            return generated()

        async def ask(system: str, text: str) -> blind.Reply | None:
            return blind.Reply(answer="TRUE" if "Statement: A colony" in text else "wrong")

        asyncio.run(generate_text(conn, "bees", PASSAGE, gen, NOW))
        asyncio.run(check_pending(conn, {"bees": PASSAGE}, ask, 10, lambda: "m", NOW))
    texts = tmp_path / "texts"
    texts.mkdir()
    (texts / "bees.yaml").write_text(yaml.safe_dump({"slug": "bees", "text": PASSAGE}), "utf-8")
    app = FastAPI()
    app.include_router(
        routes.create_router(ReadingReview(lambda: pool, texts, ids[0], lambda: NOW))
    )
    yield TestClient(app), ids[0], ids[1], pool, texts
    with pool.connection() as conn:
        conn.execute("delete from reading_items where text_slug='bees'")
    pool.close()


def test_only_the_owner_sees_and_decides(stack) -> None:  # type: ignore[no-untyped-def]
    client, _, other, _, _ = stack
    assert client.get("/reading/review", params={"learner_id": other}).status_code == 403
    body = {"decision": "approve"}
    r = client.post("/reading/review/bees-tfng-1", params={"learner_id": other}, json=body)
    assert r.status_code == 403


def test_the_queue_shows_passage_key_and_checker_answer(stack) -> None:  # type: ignore[no-untyped-def]
    client, owner, _, _, _ = stack
    out = client.get("/reading/review", params={"learner_id": owner}).json()
    assert out["counts"]["verified"] == 1 and out["counts"]["needs_review"] == 4
    first = out["items"][0]
    assert first["passage"] == PASSAGE and first["checker_answer"] == "wrong"
    assert "key" not in first["question"] and first["key"] is not None
    verified = client.get(
        "/reading/review", params={"learner_id": owner, "status": "verified"}
    ).json()
    assert [i["id"] for i in verified["items"]] == ["bees-tfng-1"]


def test_decisions_and_their_refusals(stack) -> None:  # type: ignore[no-untyped-def]
    client, owner, _, pool, texts = stack
    q = {"learner_id": owner}
    assert (
        client.post("/reading/review/bees-mcq-1", params=q, json={"decision": "reject"}).status_code
        == 422
    )
    reject = {"decision": "reject", "reason": "wrong_key", "note": "B is right"}
    r = client.post("/reading/review/bees-mcq-1", params=q, json=reject)
    assert r.json() == {"id": "bees-mcq-1", "status": "rejected"}
    assert (
        client.post(
            "/reading/review/bees-mcq-1", params=q, json={"decision": "approve"}
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/reading/review/bees-tfng-1", params=q, json={"decision": "approve"}
        ).status_code
        == 200
    )
    (texts / "bees.yaml").write_text(
        yaml.safe_dump({"slug": "bees", "text": PASSAGE + " New."}), "utf-8"
    )
    r = client.post("/reading/review/bees-tfng-2", params=q, json={"decision": "approve"})
    assert r.status_code == 422 and "thay đổi" in r.json()["detail"]  # the passage changed
    with pool.connection() as conn:
        rows = conn.execute(
            "select review_was, status, review_note from reading_items "
            "where review_was is not null order by id"
        ).fetchall()
    assert rows == [
        ("needs_review", "rejected", "[wrong_key] B is right"),
        ("verified", "approved", None),
    ]
    out = report(rows)
    assert out["agreement"]["k"] == 2 and out["reject_reasons"] == {"wrong_key": 1}
    assert "note" in out  # fewer than 50 reviewed
    with pool.connection() as conn:
        labels = conn.execute(
            "select content_id, value, tier, detail from labels where role='owner_developer' "
            "order by content_id"
        ).fetchall()
        conn.execute("delete from labels")
    # The owner's decisions are one source, Bronze (specs/validation/step-v2.md).
    assert labels == [
        ("bees-mcq-1", "wrong", "bronze", {"reason": "wrong_key"}),
        ("bees-tfng-1", "right", "bronze", {"reason": None}),
    ]


def test_agreement_and_kappa() -> None:
    rows = [("verified", "approved", None)] * 40 + [
        ("needs_review", "rejected", "[two_answers]")
    ] * 8
    rows += [("verified", "rejected", "[unclear] x")] * 2
    out = report(rows)
    assert out["reviewed"] == 50 and out["agreement"]["k"] == 48 and "note" not in out
    assert 0.8 < out["kappa"] < 0.9
    assert out["confusion"]["checker_good__owner_not_good"] == 2
    assert out["reject_reasons"] == {"two_answers": 8, "unclear": 2}
