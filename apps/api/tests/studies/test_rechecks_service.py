"""FORGET-001: the re-check service with the database. A re-check never changes mastery."""

import re
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg_pool import ConnectionPool

from app.api import rechecks as routes
from app.curriculum.store import sync_course
from app.services.grammar import GrammarService
from app.services.rechecks import Rechecks

ROOT = Path(__file__).resolve().parents[4] / "data"
APP = Path(__file__).resolve().parents[2] / "app"
NOW = datetime(2026, 11, 20, 9, 0, tzinfo=UTC)


@pytest.fixture
def env(database_url: str) -> Iterator[tuple[TestClient, str, ConnectionPool, GrammarService]]:
    pool = ConnectionPool(database_url, open=True)
    with pool.connection() as conn:
        row = conn.execute(
            "insert into learners(display_name) values ('R') returning id"
        ).fetchone()
        assert row
    learner = str(row[0])
    grammar = GrammarService(
        lambda: pool, ROOT / "courses", ROOT / "items", ROOT / "vocabulary", learner
    )
    clock = {"now": NOW}
    app = FastAPI()
    app.include_router(routes.create_router(Rechecks(grammar, lambda: clock["now"])))
    client = TestClient(app)
    yield client, learner, pool, grammar
    with pool.connection() as conn:
        conn.execute("delete from grammar_rechecks")
        conn.execute("delete from learners where id::text=%s", (learner,))
    pool.close()


def seed(pool: ConnectionPool, grammar: GrammarService, learner: str,
         nodes: dict[str, tuple[float, float]]) -> None:  # fmt: skip
    """node -> (p_known, days since its last evidence)."""
    with pool.connection() as conn:
        ids = sync_course(conn, grammar.bundle("english-ielts").course)
        for node, (p, days) in nodes.items():
            conn.execute(
                "insert into mastery(learner_id,concept_id,p_known,updated_at) "
                "values (%s,%s,%s,%s)",
                (learner, ids[node], p, NOW - timedelta(days=days)),
            )


def nodes_with_items(grammar: GrammarService) -> list[str]:
    bank = grammar.bundle("english-ielts").bank
    return sorted({i.node for i in bank.items})


def test_rechecks_are_planned_served_graded_and_never_touch_mastery(env) -> None:  # type: ignore[no-untyped-def]
    client, learner, pool, grammar = env
    n = nodes_with_items(grammar)
    seed(pool, grammar, learner, {n[0]: (0.95, 12), n[1]: (0.95, 8), n[2]: (0.95, 6),
                                  n[3]: (0.95, 9), n[4]: (0.95, 2), n[5]: (0.6, 30)})  # fmt: skip
    with pool.connection() as conn:
        before = conn.execute(
            "select concept_id, p_known, updated_at from mastery order by 1"
        ).fetchall()
    got = client.get("/rechecks/next", params={"learner_id": learner}).json()["question"]
    assert got["node"] == n[0]  # the oldest evidence first
    with pool.connection() as conn:
        planned = conn.execute("select node from grammar_rechecks order by evidence_at").fetchall()
    assert [r[0] for r in planned] == [n[0], n[3], n[1]]  # three this week; not n[2]..n[5]
    bank = grammar.bundle("english-ielts").bank
    item = next(i for i in bank.items if i.prompt == got["prompt"] and i.node == n[0])
    assert sorted(got["options"]) == sorted(o.text for o in item.options)
    wrong = next(o.text for o in item.options if not o.correct)
    r = client.post(f"/rechecks/{got['id']}/answer", json={"learner_id": learner, "answer": wrong})
    assert r.json() == {"correct": False, "key": item.key}
    again = client.post(
        f"/rechecks/{got['id']}/answer", json={"learner_id": learner, "answer": wrong}
    )
    assert again.status_code == 409
    nxt = client.get("/rechecks/next", params={"learner_id": learner}).json()["question"]
    assert nxt["node"] == n[3]
    with pool.connection() as conn:
        after = conn.execute(
            "select concept_id, p_known, updated_at from mastery order by 1"
        ).fetchall()
        assert after == before  # mastery untouched
        assert conn.execute("select count(*) from grammar_answers").fetchone() == (0,)
        assert conn.execute(
            "select count(*) from grammar_rechecks where created_at > %s",
            (NOW - timedelta(days=7),),
        ).fetchone() == (3,)


def test_another_learner_cannot_answer(env) -> None:  # type: ignore[no-untyped-def]
    client, learner, pool, grammar = env
    seed(pool, grammar, learner, {nodes_with_items(grammar)[0]: (0.95, 10)})
    q = client.get("/rechecks/next", params={"learner_id": learner}).json()["question"]
    with pool.connection() as conn:
        other = conn.execute(
            "insert into learners(display_name) values ('X') returning id::text"
        ).fetchone()
    assert other
    r = client.post(f"/rechecks/{q['id']}/answer", json={"learner_id": other[0], "answer": "x"})
    assert r.status_code == 404
    with pool.connection() as conn:
        conn.execute("delete from learners where id::text=%s", (other[0],))


def test_nothing_due_gives_no_question(env) -> None:  # type: ignore[no-untyped-def]
    client, learner, pool, grammar = env
    seed(pool, grammar, learner, {nodes_with_items(grammar)[0]: (0.95, 2)})
    assert client.get("/rechecks/next", params={"learner_id": learner}).json() == {"question": None}


def test_only_the_recheck_code_touches_the_table() -> None:
    allowed = {Path("services/rechecks.py"), Path("studies/forget.py")}
    offenders = [
        str(p.relative_to(APP))
        for p in APP.rglob("*.py")
        if p.relative_to(APP) not in allowed
        and re.search(r"\bgrammar_rechecks\b", p.read_text(encoding="utf-8"))
    ]
    assert offenders == []
