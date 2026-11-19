"""Step V2: the reviewer portal (tokens, batches, blind views, Gold labels)."""

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml  # type: ignore[import-untyped]
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg_pool import ConnectionPool

from app.api import review_portal as routes
from app.reading import blind
from app.reading.pipeline import check_pending, generate_text
from app.services.review_portal import (
    ReviewPortal,
    create_batch,
    issue_token,
    reading_strata,
    revoke_tokens,
)
from app.validation.sampling import everything, stratified
from app.validation.store import add_reviewer, effective_tier

from ..reading.test_generation import PASSAGE, generated

NOW = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)


@pytest.fixture
def portal(database_url: str, tmp_path: Path) -> Iterator[dict[str, Any]]:
    pool = ConnectionPool(database_url, open=True)
    with pool.connection() as conn:

        async def gen(system: str, text: str):  # type: ignore[no-untyped-def]
            return generated()

        async def ask(system: str, text: str) -> blind.Reply | None:
            return blind.Reply(answer="TRUE" if "Statement: A colony" in text else "wrong")

        asyncio.run(generate_text(conn, "bees", PASSAGE, gen, NOW))
        asyncio.run(check_pending(conn, {"bees": PASSAGE}, ask, 10, lambda: "baidu/ernie", NOW))
        teacher = add_reviewer(conn, "Cô Lan", "expert_teacher", "10 năm", NOW)
        rater = add_reviewer(conn, "Thầy Minh", "ielts_rater", "giám khảo", NOW)
        tokens = {"teacher": issue_token(conn, teacher), "rater": issue_token(conn, rater)}
        disagreed, agreed = reading_strata(conn)
        reading = create_batch(
            conn, "Đọc 1", "reading_item", stratified(disagreed, agreed, 50, 1), 1
        )
        levels = create_batch(conn, "Cấp độ", "text_level", everything(["bees"], 1), 1)
    texts = tmp_path / "texts"
    texts.mkdir()
    (texts / "bees.yaml").write_text(yaml.safe_dump({"slug": "bees", "text": PASSAGE}), "utf-8")
    app = FastAPI()
    app.include_router(routes.create_router(ReviewPortal(lambda: pool, texts, lambda: NOW)))
    yield {
        "client": TestClient(app),
        "pool": pool,
        "tokens": tokens,
        "teacher": teacher,
        "reading": reading,
        "levels": levels,
        "disagreed": disagreed,
        "agreed": agreed,
    }
    with pool.connection() as conn:
        conn.execute("delete from labels")
        conn.execute("delete from review_batches")
        conn.execute("delete from reviewers")
        conn.execute("delete from reading_items where text_slug='bees'")
    pool.close()


def h(token: str) -> dict[str, str]:
    return {"X-Reviewer-Token": token}


def test_a_token_is_required_and_can_be_revoked(portal: dict[str, Any]) -> None:
    c = portal["client"]
    assert c.get("/review/me").status_code == 401
    assert c.get("/review/me", headers=h("x" * 43)).status_code == 401
    me = c.get("/review/me", headers=h(portal["tokens"]["teacher"])).json()
    assert me["name"] == "Cô Lan" and me["role"] == "expert_teacher"
    with portal["pool"].connection() as conn:
        assert revoke_tokens(conn, portal["teacher"]) == 1
    assert c.get("/review/me", headers=h(portal["tokens"]["teacher"])).status_code == 401


def test_only_the_reviewers_role_sees_a_batch(portal: dict[str, Any]) -> None:
    c = portal["client"]
    rater = c.get("/review/me", headers=h(portal["tokens"]["rater"])).json()
    assert rater["batches"] == []
    url = f"/review/batches/{portal['reading']}/next"
    assert c.get(url, headers=h(portal["tokens"]["rater"])).status_code == 404


def test_the_view_is_blind_and_labels_are_gold(portal: dict[str, Any]) -> None:
    c, tok = portal["client"], h(portal["tokens"]["teacher"])
    total = len(portal["disagreed"]) + len(portal["agreed"])
    assert total >= 2
    url = f"/review/batches/{portal['reading']}"
    first = c.get(f"{url}/next", headers=tok).json()
    assert (first["total"], first["done"]) == (total, 0)
    item = first["item"]
    assert set(item) == {
        "content_id",
        "content_type",
        "kind",
        "skill",
        "passage",
        "question",
        "key",
    }
    assert "evidence" not in item["question"] and "key" not in item["question"]
    cid = item["content_id"]
    post = f"{url}/items/{cid}"
    assert c.post(post, headers=tok, json={"verdict": "wrong"}).status_code == 422  # no reason
    assert c.post(post, headers=tok, json={"level": "B1"}).status_code == 422
    assert c.post(f"{url}/items/nope", headers=tok, json={"verdict": "right"}).status_code == 404
    ok = c.post(post, headers=tok, json={"answer": "TRUE", "verdict": "right"})
    assert ok.status_code == 200
    with portal["pool"].connection() as conn:
        e = effective_tier(conn, "reading_item", cid, "item_ok")
        assert (e.tier, e.value) == ("gold", "right")
        detail = conn.execute(
            "select detail, tier from labels where content_id=%s and role='expert_teacher'", (cid,)
        ).fetchone()
        assert detail == ({"answer": "TRUE", "reason": None}, "gold")
    second = c.get(f"{url}/next", headers=tok).json()
    assert second["done"] == 1 and second["item"]["content_id"] != cid
    # A second answer from the same reviewer replaces the first.
    c.post(post, headers=tok, json={"verdict": "wrong", "reason": "two_answers"})
    with portal["pool"].connection() as conn:
        assert conn.execute(
            "select count(*) from labels where content_id=%s and role='expert_teacher'", (cid,)
        ).fetchone() == (1,)


def test_text_levels(portal: dict[str, Any]) -> None:
    c, tok = portal["client"], h(portal["tokens"]["teacher"])
    url = f"/review/batches/{portal['levels']}"
    nxt = c.get(f"{url}/next", headers=tok).json()
    assert nxt["item"] == {"content_id": "bees", "content_type": "text_level", "text": PASSAGE}
    assert c.post(f"{url}/items/bees", headers=tok, json={"verdict": "right"}).status_code == 422
    assert c.post(f"{url}/items/bees", headers=tok, json={"level": "B1"}).status_code == 200
    done = c.get(f"{url}/next", headers=tok).json()
    assert done["item"] is None and done["done"] == 1


def test_a_changed_passage_is_not_served(portal: dict[str, Any], tmp_path: Path) -> None:
    (tmp_path / "texts" / "bees.yaml").write_text(
        yaml.safe_dump({"slug": "bees", "text": PASSAGE + " Changed."}), "utf-8"
    )
    got = (
        portal["client"]
        .get(f"/review/batches/{portal['reading']}/next", headers=h(portal["tokens"]["teacher"]))
        .json()
    )
    assert got["item"] is None and got["unavailable"] == got["total"]


def test_an_experts_option_letter_is_kept_in_the_stored_order(portal: dict[str, Any]) -> None:
    """Step 4.3c: the expert answers what the page shows; the record means the stored option."""
    c, tok = portal["client"], h(portal["tokens"]["teacher"])
    assert "bees-mcq-1" in portal["disagreed"] + portal["agreed"]
    url = f"/review/batches/{portal['reading']}/items/bees-mcq-1"
    # On the page "Stored honey" is A; as stored it is B.
    assert c.post(url, headers=tok, json={"answer": "A", "verdict": "right"}).status_code == 200
    with portal["pool"].connection() as conn:
        detail = conn.execute(
            "select detail from labels where content_id='bees-mcq-1' and role='expert_teacher'"
        ).fetchone()
    assert detail == ({"answer": "B", "reason": None},)
