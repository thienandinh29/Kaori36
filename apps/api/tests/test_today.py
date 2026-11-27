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
from app.vocabulary.wordlist import load_wordlist

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


# --- step M5: the day's plan is fixed, ticked off from today's answers; the week's study days ---


def _service(pool: ConnectionPool, clock: list[datetime]) -> TestClient:
    grammar = GrammarService(
        lambda: pool, ROOT / "courses", ROOT / "items", ROOT / "vocabulary", ""
    )
    app = FastAPI()
    app.include_router(routes.create_router(TodayService(grammar, clock=lambda: clock[0])))
    return TestClient(app)


def _review(
    pool: ConnectionPool,
    learner: str,
    at: datetime,
    n: int,
    lst: str = "core-seed",
    keys: list[str] | None = None,
) -> None:
    with pool.connection() as conn:
        for i in range(n):
            conn.execute(
                "insert into vocab_reviews(learner_id,list_slug,word_key,item_kind,correct,answer,"
                "due_at,answered_at) values (%s,%s,%s,'meaning',true,'x',%s,%s)",
                (learner, lst, keys[i] if keys else f"w{i}:noun", at + timedelta(days=1), at),
            )


def test_the_plan_is_fixed_for_the_day_and_ticked_off(env) -> None:  # type: ignore[no-untyped-def]
    _, learner, pool = env
    clock = [NOW]  # 15:00 in Vietnam
    client = _service(pool, clock)
    with pool.connection() as conn:
        for i in range(3):
            conn.execute(
                "insert into vocab_cards(learner_id,list_slug,word_key,fsrs_state,due_at) "
                "values (%s,'core-seed',%s,%s,%s)",
                (learner, f"w{i}:noun", Jsonb({"stability": 2.0}), NOW - timedelta(days=1)),
            )
    first = client.get("/today", params={"learner_id": learner}).json()
    acts = first["activities"]
    assert first["day"] == "2026-12-01" and first["done_count"] == 0
    assert (acts[0]["kind"], acts[0]["target"], acts[0]["done"]) == ("review", "vocab", False)
    assert acts[0]["minutes"] == 2 and all(a["minutes"] > 0 for a in acts)
    assert "due" not in first

    # The cards are answered: the engine would now drop the review, but the plan keeps it, done.
    clock[0] = NOW + timedelta(hours=1)
    _review(pool, learner, clock[0], 3)
    with pool.connection() as conn:
        conn.execute(
            "update vocab_cards set due_at=%s where learner_id=%s",
            (NOW + timedelta(days=3), learner),
        )
    again = client.get("/today", params={"learner_id": learner, "minutes": 90}).json()
    assert [a["target"] for a in again["activities"]] == [a["target"] for a in acts]
    assert again["activities"][0]["done"] is True
    assert again["done_count"] >= 1

    # Answers from yesterday do not count, and the next day gets a new plan.
    clock[0] = NOW + timedelta(days=1)
    nxt = client.get("/today", params={"learner_id": learner}).json()
    assert nxt["day"] == "2026-12-02" and nxt["done_count"] == 0
    assert nxt["activities"][0]["kind"] != "review"  # nothing is due any more
    with pool.connection() as conn:
        assert conn.execute(
            "select count(*) from today_plans where learner_id=%s", (learner,)
        ).fetchone() == (2,)


def test_a_new_learners_plan_turns_done_with_an_essay_and_word_answers(env) -> None:  # type: ignore[no-untyped-def]
    _, learner, pool = env
    client = _service(pool, [NOW])
    acts = client.get("/today", params={"learner_id": learner}).json()["activities"]
    assert acts[0]["kind"] == "diagnostic"
    assert acts[0]["minutes"] == (20 if acts[0]["target"] == "writing-task1" else 40)
    band = next(a for a in acts if a["target"] == "vocab-b2")
    assert band["minutes"] == 5
    with pool.connection() as conn:
        conn.execute(
            "insert into essays(learner_id,prompt_id,text,consent,submitted_at) "
            "values (%s,'p','Some text.','writing-v1',%s)",
            (learner, NOW),
        )
    words = load_wordlist(ROOT / "vocabulary" / "core-seed.yaml").words
    b2 = [w.key for w in words if w.level == "B2"]
    _review(pool, learner, NOW, 9, keys=b2)
    out = client.get("/today", params={"learner_id": learner}).json()
    assert {a["target"]: a["done"] for a in out["activities"]}["vocab-b2"] is False
    _review(pool, learner, NOW, 1, keys=b2[9:])
    out = client.get("/today", params={"learner_id": learner}).json()
    done = {a["target"]: a["done"] for a in out["activities"]}
    assert done[acts[0]["target"]] is True and done["vocab-b2"] is True
    assert done.get("vocab-b1", False) is False  # B2 words do not tick the B1 band


def test_the_week_counts_saved_answers_per_day(env) -> None:  # type: ignore[no-untyped-def]
    _, learner, pool = env
    client = _service(pool, [NOW])  # Tuesday 1 Dec 2026
    _review(pool, learner, datetime(2026, 11, 30, 2, 0, tzinfo=UTC), 2)  # Monday
    _review(pool, learner, datetime(2026, 11, 29, 2, 0, tzinfo=UTC), 5)  # last week's Sunday
    with pool.connection() as conn:
        conn.execute(
            "insert into grammar_answers(learner_id,course,node,item_id,correct,context,"
            "answered_at) values (%s,'english-ielts','n','i',true,'practice',%s)",
            (learner, NOW),
        )
        conn.execute(
            "insert into say_attempts(learner_id,word,phones,said_at) values (%s,'cat','[]',%s)",
            (learner, NOW),
        )
    week = client.get("/today/week", params={"learner_id": learner}).json()
    assert week["days"][0]["date"] == "2026-11-30"
    assert [d["answers"] for d in week["days"]] == [2, 2, 0, 0, 0, 0, 0]
    assert week["days"][1]["today"] is True
    assert [d["future"] for d in week["days"]] == [False, False] + [True] * 5
    assert week["studied_days"] == 2
    assert "streak" not in str(week)
    assert (
        client.get(
            "/today/week", params={"learner_id": "00000000-0000-4000-8000-000000000999"}
        ).status_code
        == 404
    )
