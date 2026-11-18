"""Step V3: Reading agreement, pronunciation and text levels read Gold labels."""

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import psycopg
import pytest
from psycopg.types.json import Jsonb

from app.pronunciation.thresholds import apply_allowed, from_rows, gold_rows, report, with_basis
from app.reading.agreement import expert_pairs, expert_report
from app.texts.levels import gold_levels, score, with_levels
from app.validation.store import LabelIn, add_label, add_reviewer

NOW = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)


@pytest.fixture
def conn(database_url: str) -> Iterator[psycopg.Connection]:
    with psycopg.connect(database_url) as c:
        yield c
        c.rollback()


def test_expert_report_by_stratum_and_weighted() -> None:
    pairs = [("verified", "right")] * 18 + [("verified", "wrong")] * 2
    pairs += [("needs_review", "wrong")] * 6 + [("needs_review", "right")] * 4
    out = expert_report(pairs, {"verified": 90, "needs_review": 10})
    assert out["basis"]["gate"] == "not_measured" and out["basis"]["n"] == 30
    e = out["defect_escape"]
    assert (e["k"], e["n"], e["share"]) == (2, 20, 0.1)
    assert (out["false_rejection"]["k"], out["false_rejection"]["n"]) == (4, 10)
    # 0.9 * (18/20) + 0.1 * (6/10) = 0.87, not the raw 24/30 = 0.8
    assert out["weighted_accuracy"] == 0.87 and out["agreement"]["k"] == 24
    assert out["process"]["supports"] is False
    clean = expert_report([("verified", "right")] * 72, {"verified": 100})
    assert clean["basis"]["gate"] == "measured" and clean["process"]["supports"] is True
    assert clean["weighted_accuracy"] is None  # no needs_review stratum sampled


def _item(conn: psycopg.Connection, item_id: str, status: str, was: str | None = None) -> None:
    conn.execute(
        "insert into reading_items(id,text_slug,passage_sha256,kind,item,status,review_was) "
        "values (%s,'t','h','tfng',%s,%s,%s)",
        (item_id, Jsonb({}), status, was),
    )


def test_expert_pairs_use_gold_agreement_only(conn: psycopg.Connection) -> None:
    a = add_reviewer(conn, "A", "expert_teacher", "", NOW)
    b = add_reviewer(conn, "B", "expert_teacher", "", NOW)
    for i, st, was in [("r1", "verified", None), ("r2", "approved", "needs_review"),
                       ("r3", "verified", None), ("r4", "dropped", None)]:  # fmt: skip
        _item(conn, i, st, was)

    def lab(cid: str, value: str, rid: str, role: str = "expert_teacher") -> None:
        add_label(conn, LabelIn(content_type="reading_item", content_id=cid, aspect="item_ok",
                                value=value, role=role, reviewer_id=rid))  # fmt: skip

    lab("r1", "right", a)
    lab("r2", "wrong", a)
    lab("r3", "right", a)
    lab("r3", "wrong", b)  # experts disagree: left out
    add_label(conn, LabelIn(content_type="reading_item", content_id="r1", aspect="item_ok",
                            value="wrong", role="owner_developer"))  # fmt: skip
    pairs, population = expert_pairs(conn)
    assert sorted(pairs) == [("needs_review", "wrong"), ("verified", "right")]
    assert population == {"verified": 2, "needs_review": 1}


def _analysis() -> dict[str, Any]:
    return {
        "targets": [{"sound": "th-voiceless", "gop": -2.0}, {"sound": "th-voiceless", "gop": 0.0}]
    }


def test_pronunciation_reads_gold_and_refuses_to_apply_bronze(conn: psycopg.Connection) -> None:
    learner = conn.execute(
        "insert into learners(display_name) values ('O') returning id"
    ).fetchone()
    assert learner is not None
    rec = conn.execute(
        "insert into speech_recordings(learner_id,prompt_id,consent,audio,seconds,quality,status,"
        "analysis) values (%s,'p1','voice-v1','\\x00',1,'{}','analysed',%s) returning id::text",
        (learner[0], Jsonb(_analysis())),
    ).fetchone()
    assert rec is not None
    assert gold_rows(conn) == []
    expert = add_reviewer(conn, "P", "phonetics_expert", "", NOW)
    for target, value in ((0, "wrong"), (1, "right")):
        add_label(conn, LabelIn(content_type="speech_target", content_id=f"{rec[0]}:{target}",
                                aspect="phone_ok", value=value, role="phonetics_expert",
                                reviewer_id=expert))  # fmt: skip
    rows = gold_rows(conn)
    assert sorted((r[2], r[3]) for r in rows) == [(0, "wrong"), (1, "right")]
    groups = {"th-voiceless": "th"}
    gold = with_basis(report(from_rows(rows, groups)), "gold", 1)
    assert gold["basis"]["gate"] == "not_measured"  # 1 recording of 50
    assert not apply_allowed(gold)
    assert apply_allowed(with_basis(report(from_rows(rows, groups)), "gold", 50))
    assert not apply_allowed(with_basis(report(from_rows(rows, groups)), "bronze", 500))


def test_text_levels_gold_and_feedback(conn: psycopg.Connection) -> None:
    a = add_reviewer(conn, "A", "expert_teacher", "", NOW)
    b = add_reviewer(conn, "B", "expert_teacher", "", NOW)

    def lab(slug: str, level: str, rid: str) -> None:
        add_label(conn, LabelIn(content_type="text_level", content_id=slug, aspect="cefr_level",
                                value=level, role="expert_teacher", reviewer_id=rid))  # fmt: skip

    lab("t1", "B1", a)
    lab("t2", "A2", a)
    lab("t2", "B2", b)  # disputed: left out
    lab("t3", "unsure", a)
    assert gold_levels(conn) == {"t1": "B1"}
    rows = [{"slug": f"t{i}", "words": str(100 * i)} for i in (1, 2, 3)]
    merged = with_levels(rows, {"t1": "B1"})
    assert [r["level"] for r in merged] == ["B1", "", ""]
    gold = score(merged, "gold")["basis"]
    assert (gold["truth"], gold["n"], gold["gate"]) == ("gold", 1, "not_measured")
    felt = score([r | {"level": "B1"} for r in rows])
    assert felt["basis"]["truth"] == "feedback" and felt["basis"]["gate"] == "not_measured"
