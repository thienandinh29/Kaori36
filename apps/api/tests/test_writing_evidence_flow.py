"""Writing evidence closes the loop (specs/two-layer-map/writing-evidence.md).

Three essays whose grammar checks fail while the rest pass: Writing grammar goes down, the others
go up, and once measured the "Hôm nay" list traces Writing grammar to a weak grammar foundation
instead of asking for a diagnostic again.
"""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg_pool import ConnectionPool

from app.services import competency_evidence
from app.services.grammar import GrammarService
from app.services.today import TodayService
from app.writing.competency import observations

ROOT = Path(__file__).resolve().parents[3] / "data"
NOW = datetime(2026, 12, 1, 8, 0, tzinfo=UTC)
TEXT = "However, the government should invest in public transport. For instance, buses matter."


def essay_result(errors: int) -> dict[str, Any]:
    return {
        "words": 270, "min_words": 250, "long_enough": True, "paragraphs": 4,
        "avg_sentence_words": 17.0, "linking_groups_used": 4,
        "linking": {"contrast": {"however": 1}, "opinion": {"i believe": 1},
                    "example": {"for instance": 1}, "conclusion": {"in conclusion": 1}},
        "grammar": {"counts": {"DET": errors}},
        "complexity": {"sentences": 16, "clauses_per_sentence": 1.1, "complex_sentence_share": 0.1},
    }  # fmt: skip


@pytest.fixture
def env(database_url: str) -> Iterator[tuple[str, ConnectionPool, GrammarService]]:
    pool = ConnectionPool(database_url, open=True)
    with pool.connection() as conn:
        row = conn.execute(
            "insert into learners(display_name) values ('E') returning id"
        ).fetchone()
        assert row
    grammar = GrammarService(
        lambda: pool, ROOT / "courses", ROOT / "items", ROOT / "vocabulary", ""
    )
    yield str(row[0]), pool, grammar
    with pool.connection() as conn:
        conn.execute("delete from learners where id=%s", (row[0],))
    pool.close()


def test_three_essays_measure_writing_and_change_the_list(env) -> None:  # type: ignore[no-untyped-def]
    learner, pool, grammar = env
    rules = competency_evidence.rules(ROOT / "writing")
    known = competency_evidence.known_b1()
    with psycopg.connect(pool.conninfo) as conn:
        for i in range(3):
            found = observations(rules, essay_result(errors=15), TEXT, 2, known)
            competency_evidence.apply(conn, uuid.UUID(learner), uuid.uuid4(), found,
                                      rules.params(), NOW + timedelta(days=i))  # fmt: skip
        p: dict[str, float] = dict(
            conn.execute(
                "select c.slug, m.p_known from mastery m join concepts c on c.id=m.concept_id "
                "join subjects s on s.id=c.subject_id where m.learner_id=%s and s.slug=%s",
                (learner, competency_evidence.SUBJECT),
            ).fetchall()
        )
    init = rules.params().p_init
    assert p["writing-grammar"] < init  # every grammar check failed
    assert p["writing-coherence"] > init and p["writing-task2-response"] > init
    today = TodayService(grammar, clock=lambda: NOW).today(learner, 50)
    kinds = [(a["kind"], a["target"], a["via"]) for a in today["activities"]]
    assert ("diagnostic", "writing-grammar", None) not in kinds  # measured now
    assert ("diagnostic", "writing-task1", None) in kinds  # Task 1 still unmeasured
    grammar_root = [k for k in kinds if k[0] == "learn_foundation" and k[2] == "writing-grammar"]
    assert grammar_root, kinds  # traced to a weak grammar foundation, not "practise"
    assert grammar_root[0][1] in {"present-perfect-vs-past", "articles-basic", "conditionals-1-2",
                                  "passive-present-past"}  # fmt: skip
