"""Step V1: labels in the database and the backfill."""

from collections.abc import Iterator
from datetime import UTC, datetime

import psycopg
import pytest
from psycopg.types.json import Jsonb

from app.validation.cli import backfill
from app.validation.store import LabelIn, add_label, add_reviewer, effective_tier, summary

NOW = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)


@pytest.fixture
def conn(database_url: str) -> Iterator[psycopg.Connection]:
    with psycopg.connect(database_url) as c:
        yield c
        c.rollback()


def test_tier_is_set_by_code_and_same_source_replaces(conn: psycopg.Connection) -> None:
    base = {"content_type": "grammar_item", "content_id": "g1", "aspect": "item_ok"}
    add_label(conn, LabelIn(**base, value="right", role="model", name="baidu/ernie"))
    add_label(conn, LabelIn(**base, value="wrong", role="model", name="baidu/ernie"))
    rows = conn.execute(
        "select value,tier,independence from labels where content_id='g1'"
    ).fetchall()
    assert rows == [("wrong", "bronze", "model:baidu")]
    add_label(conn, LabelIn(**base, value="wrong", role="code_check", name="grammar"))
    assert effective_tier(conn, "grammar_item", "g1", "item_ok").tier == "silver"


def test_expert_labels_need_a_matching_reviewer(conn: psycopg.Connection) -> None:
    rid = add_reviewer(conn, "Cô Lan", "expert_teacher", "10 năm", NOW)
    base = {"content_type": "text_level", "content_id": "t1", "aspect": "cefr_level", "value": "B1"}
    with pytest.raises(ValueError):
        add_label(conn, LabelIn(**base, role="ielts_rater", reviewer_id=rid))
    with pytest.raises(ValueError):
        add_label(conn, LabelIn(**base, role="owner_developer", reviewer_id=rid))
    with pytest.raises(ValueError):
        add_label(conn, LabelIn(**base, role="expert_teacher"))
    with pytest.raises(ValueError):
        add_reviewer(conn, "Bạn", "owner_developer", "", NOW)
    with pytest.raises(ValueError):
        add_label(conn, LabelIn(**{**base, "content_type": "poem"}, role="model", name="a/b"))
    add_label(conn, LabelIn(**base, role="expert_teacher", reviewer_id=rid))
    add_label(conn, LabelIn(**{**base, "value": "A2"}, role="owner_developer"))
    got = effective_tier(conn, "text_level", "t1", "cefr_level")
    assert (got.tier, got.value) == ("gold", "B1")


def test_backfill_copies_existing_decisions_and_reruns_safely(conn: psycopg.Connection) -> None:
    learner = conn.execute(
        "insert into learners(display_name) values ('O') returning id"
    ).fetchone()
    assert learner is not None
    rec = conn.execute(
        "insert into speech_recordings(learner_id,prompt_id,consent,audio,seconds,quality,keep) "
        "values (%s,'p1','voice-v1','\\x00',1,'{}',true) returning id::text",
        (learner[0],),
    ).fetchone()
    assert rec is not None
    conn.execute(
        "insert into speech_labels(recording_id,target,label) "
        "values (%s,0,'right'),(%s,1,'unsure')",
        (rec[0], rec[0]),
    )
    item = {"kind": "tfng"}
    rows = [
        ("i-ok", "verified", None, "baidu/ernie"),
        ("i-doubt", "needs_review", None, "baidu/ernie"),
        ("i-drop", "dropped", None, None),
        ("i-appr", "approved", "verified", "baidu/ernie"),
        ("i-rej", "rejected", "verified", "baidu/ernie"),
    ]
    for item_id, status, was, model in rows:
        conn.execute(
            "insert into reading_items(id,text_slug,passage_sha256,kind,item,status,review_was,"
            "checker_model) values (%s,'t','h','tfng',%s,%s,%s,%s)",
            (item_id, Jsonb(item), status, was, model),
        )
    first = backfill(conn)
    assert first == {
        "speech_target": 2,
        "reading_code_check": 5,
        "reading_model": 4,
        "reading_owner": 2,
    }
    assert backfill(conn) == first
    assert conn.execute("select count(*) from labels").fetchone() == (13,)

    def tier(item_id: str) -> tuple[str | None, str | None, bool]:
        e = effective_tier(conn, "reading_item", item_id, "item_ok")
        return e.tier, e.value, e.disputed

    assert tier("i-ok") == ("silver", "right", False)
    assert tier("i-doubt") == ("bronze", None, True)
    assert tier("i-drop") == ("bronze", "wrong", False)
    assert tier("i-appr") == ("silver", "right", False)  # the owner's approval adds nothing
    assert tier("i-rej") == ("bronze", None, True)  # the owner's doubt is kept
    s = summary(conn)
    assert s["speech_target/phone_ok"] == {"bronze": 1, "none": 1}
    assert s["reading_item/item_ok"] == {"silver": 2, "disputed": 2, "bronze": 1}
