"""Two maps, M3: GET /today reads the learner's state and returns the engine's list."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from app.api import today as routes
from app.services.grammar import GrammarService
from app.services.today import TodayService

ROOT = Path(__file__).resolve().parents[3] / "data"
NOW = datetime(2026, 12, 1, 8, 0, tzinfo=UTC)


@pytest.fixture
def env(database_url: str) -> Iterator[tuple[TestClient, str, ConnectionPool]]:
    pool = ConnectionPool(database_url, open=True)
    with pool.connection() as conn:
        row = conn.execute(
            "insert into learners(display_name) values ('T') returning id"
        ).fetchone()
        assert row
    learner = str(row[0])
    grammar = GrammarService(
        lambda: pool, ROOT / "courses", ROOT / "items", ROOT / "vocabulary", ""
    )
    app = FastAPI()
    app.include_router(routes.create_router(TodayService(grammar, clock=lambda: NOW)))
    yield TestClient(app), learner, pool
    with pool.connection() as conn:
        conn.execute("delete from learners where id::text=%s", (learner,))
    pool.close()


def test_a_new_learner_gets_a_diagnostic_then_shared_foundations(env) -> None:  # type: ignore[no-untyped-def]
    client, learner, _ = env
    out = client.get("/today", params={"learner_id": learner, "minutes": 40}).json()
    acts = out["activities"]
    assert acts[0]["kind"] == "diagnostic" and acts[0]["href"] == "/viet"
    assert acts[0]["name_vi"].startswith("Viết")
    assert all(a["kind"] == "learn_foundation" for a in acts[1:])
    assert acts[1]["target"] == "vocab-b2" and acts[1]["name_vi"] == "Từ vựng B2"
    assert acts[1]["href"] == "/tu-vung"
    assert "Từ vựng B2" in acts[1]["trace"]["rule_vi"]  # names, not raw ids
    assert all(a["trace"]["posterior"] is None for a in acts)
    assert out["target"] == {"overall": 7.0, "exam_date": "2027-07-01", "links_status": "proposed"}
    assert out["notes"] == ["nothing measured: shared foundations first"]


def test_due_reviews_come_first(env) -> None:  # type: ignore[no-untyped-def]
    client, learner, pool = env
    with pool.connection() as conn:
        for i in range(3):
            conn.execute(
                "insert into vocab_cards(learner_id,list_slug,word_key,fsrs_state,due_at) "
                "values (%s,'core-seed',%s,%s,%s)",
                (learner, f"w{i}:noun", Jsonb({"stability": 2.0}), NOW - timedelta(days=1)),
            )
    acts = client.get("/today", params={"learner_id": learner}).json()["activities"]
    assert (acts[0]["kind"], acts[0]["target"], acts[0]["href"]) == ("review", "vocab", "/tu-vung")
    assert "Có 3 mục đến hạn ôn (Từ vựng)" in acts[0]["trace"]["rule_vi"]


def test_unknown_learner_and_bad_minutes(env) -> None:  # type: ignore[no-untyped-def]
    client, _, _ = env
    assert (
        client.get(
            "/today", params={"learner_id": "00000000-0000-4000-8000-000000000999"}
        ).status_code
        == 404
    )
    assert client.get("/today", params={"learner_id": "x", "minutes": 5}).status_code == 422


def test_maps_show_every_competency_with_its_foundations(env) -> None:  # type: ignore[no-untyped-def]
    client, learner, _ = env
    out = client.get("/maps", params={"learner_id": learner}).json()
    assert [s["skill"] for s in out["skills"]] == ["reading", "listening", "writing", "speaking"]
    comps = {c["slug"]: c for s in out["skills"] for c in s["competencies"]}
    assert len(comps) == 17
    assert all(c["status"] == "unmeasured" and c["p"] is None for c in comps.values())
    assert comps["writing-grammar"]["available"] is True
    assert comps["reading-detail"]["available"] is False
    links = {link["node"]: link for link in comps["writing-grammar"]["links"]}
    assert links["articles-basic"]["live"] is True
    assert links["articles-basic"]["href"] == "/on-tap/phan/articles-basic"
    assert links["agreement-long-subjects"]["live"] is False  # proposed path only
    assert links["agreement-long-subjects"]["href"] is None
    assert links["agreement-long-subjects"]["name_vi"] != "agreement-long-subjects"  # a real name
    assert links["articles-basic"]["status"] == "unmeasured"  # no answers yet
    assert out["known"] == 0.9 and out["root_cause_below"] == 0.8 and out["min_evidence"] == 3
    assert out["target"]["links_status"] == "proposed"


def test_maps_status_follows_the_evidence(env) -> None:  # type: ignore[no-untyped-def]
    import uuid as _uuid

    from app.services import competency_evidence
    from app.writing.competency import Observation

    client, learner, pool = env
    with pool.connection() as conn:
        rules = competency_evidence.rules(ROOT / "writing")
        for passed in (True, True, True):
            obs = [Observation("writing-coherence", "paragraphs", passed, 4.0, "x")]
            competency_evidence.apply(conn, _uuid.UUID(learner), _uuid.uuid4(), obs,
                                      rules.params(), NOW)  # fmt: skip
        obs = [Observation("writing-grammar", "error_rate", False, 9.0, "x")]
        competency_evidence.apply(
            conn, _uuid.UUID(learner), _uuid.uuid4(), obs, rules.params(), NOW
        )
    comps = {
        c["slug"]: c
        for s in client.get("/maps", params={"learner_id": learner}).json()["skills"]
        for c in s["competencies"]
    }
    coherence = comps["writing-coherence"]
    assert coherence["evidence"] == 3 and coherence["status"] in ("growing", "known", "weak")
    assert coherence["p"] > 0.2
    grammar = comps["writing-grammar"]
    assert grammar["evidence"] == 1 and grammar["status"] == "unmeasured"  # one essay is not enough
    assert grammar["p"] is not None  # the estimate is shown, flagged as unmeasured
