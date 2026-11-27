"""The offline run that explains the bank's questions (CP4b, bank step 1), on a real database."""

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import psycopg
import pytest
from psycopg.types.json import Jsonb

from app.reading.calls import CallLog
from app.reading.explain import ExplainOut
from app.reading.explain_run import explain_pending, pending
from app.reading.pipeline import sha256
from app.writing.model_calls import Prices
from tests.reading.test_explain import MCQ, NG, PASSAGE, TF, WHY

NOW = datetime(2025, 6, 3, tzinfo=UTC)


@pytest.fixture
def conn(database_url: str) -> Iterator[psycopg.Connection[Any]]:
    with psycopg.connect(database_url) as c:
        c.execute("delete from reading_items where text_slug in ('t', 'gone')")
        c.commit()
        yield c
        c.execute("delete from reading_items where text_slug in ('t', 'gone')")
        c.commit()


def add(conn: psycopg.Connection[Any], item: Any, status: str, digest: str | None = None,
        slug: str = "t", kind: str | None = None) -> None:  # fmt: skip
    conn.execute(
        "insert into reading_items(id,text_slug,passage_sha256,kind,item,status,generated_at) "
        "values (%s,%s,%s,%s,%s,%s,%s)",
        (item.id, slug, digest or sha256(PASSAGE), kind or item.kind,
         Jsonb(item.model_dump(mode="json")), status, NOW),
    )  # fmt: skip
    conn.commit()


class Scripted:
    """Good explanations, except a made-up quote for the not-given question."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def __call__(self, system: str, text: str) -> ExplainOut | None:
        self.prompts.append(text)
        if "government paid" in text:
            return ExplainOut(
                key_quotes=["words nobody wrote"], why_key_vi=WHY, skills=["fng_logic"]
            )
        return ExplainOut(key_quotes=["By 1957 it was declared biologically dead"], why_key_vi=WHY,
                          skills=["scan_detail"])  # fmt: skip


def test_approved_first_verified_only_when_asked_and_never_twice(
    conn: psycopg.Connection[Any],
) -> None:
    add(conn, TF, "approved")
    add(conn, NG, "approved")
    add(conn, MCQ, "verified")
    add(conn, TF.model_copy(update={"id": "t-tfng-9"}), "approved", digest="stale")  # text edited
    add(conn, TF.model_copy(update={"id": "gone-tfng-1", "text": "gone"}), "approved", slug="gone")
    add(conn, TF.model_copy(update={"id": "t-tfng-8"}), "needs_review")
    passages = {"t": PASSAGE}
    assert [t[0] for t in pending(conn, passages)] == ["t-tfng-1", "t-tfng-2"]
    assert [t[0] for t in pending(conn, passages, include_verified=1)][-1] == "t-mcq-1"

    log = CallLog(Prices(1.0, 4.0))
    model = Scripted()
    todo = pending(conn, passages)
    counts = asyncio.run(explain_pending(conn, todo, model, lambda: "deepseek-test", log, 0.10,
                                         NOW))  # fmt: skip
    assert counts == {"checked": 1, "dropped": 1, "no_reply": 0, "waiting": 0}
    rows = conn.execute(
        "select item_id, status, skills, problems, model from reading_explanations "
        "where item_id like 't-%%' order by item_id"
    ).fetchall()
    assert rows[0][:3] == ("t-tfng-1", "checked", ["scan_detail"]) and rows[0][4] == "deepseek-test"
    assert rows[1][1] == "dropped" and any("not in the passage" in p for p in rows[1][3])
    assert pending(conn, passages) == []  # both versions explained (a drop is not retried)

    edited = TF.model_copy(update={"statement": "The Thames was declared dead by 1957."})
    conn.execute("update reading_items set item=%s where id='t-tfng-1'",
                 (Jsonb(edited.model_dump(mode="json")),))  # fmt: skip
    conn.commit()
    assert [t[0] for t in pending(conn, passages)] == ["t-tfng-1"]  # an edited question again


def test_the_cost_cap_stops_new_calls_and_no_reply_is_retried(
    conn: psycopg.Connection[Any],
) -> None:
    add(conn, TF, "approved")
    add(conn, NG, "approved")
    passages = {"t": PASSAGE}
    log = CallLog(Prices(1.0, 4.0))
    log.cost_usd = 0.10
    counts = asyncio.run(explain_pending(conn, pending(conn, passages), Scripted(), lambda: None,
                                         log, 0.10, NOW))  # fmt: skip
    assert counts["waiting"] == 2 and counts["checked"] == 0

    async def silent(system: str, text: str) -> ExplainOut | None:
        return None

    counts = asyncio.run(explain_pending(conn, pending(conn, passages), silent, lambda: None,
                                         CallLog(Prices(1.0, 4.0)), 0.10, NOW))  # fmt: skip
    assert counts["no_reply"] == 2 and len(pending(conn, passages)) == 2
