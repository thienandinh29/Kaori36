"""Offline Reading model calls are recorded with their cost (app/reading/calls.py)."""

from datetime import UTC, datetime
from typing import Literal

import psycopg

from app.llm.gateway import Attempt, Route
from app.reading.calls import CallLog
from app.writing.model_calls import Prices

Status = Literal["success", "validation_error"]
NOW = datetime(2026, 11, 19, 4, 0, tzinfo=UTC)


def attempt(model: str, status: Status = "success", task: str = "reading_items") -> Attempt:
    route = Route(provider="deepseek", model=model, family="deepseek")
    return Attempt(task=task, tier="free", route=route, number=1, latency_ms=1200.4,
                   status=status, input_tokens=2000, output_tokens=1500,
                   thoughts_tokens=500)  # fmt: skip


def test_every_attempt_is_recorded_and_free_models_cost_nothing(database_url: str) -> None:
    log = CallLog(Prices(1.0, 4.0))
    log.observe(attempt("deepseek-flash"))
    log.observe(attempt("deepseek-flash", "validation_error"))  # rejected replies cost money too
    log.observe(attempt("baidu/ernie-5.5-flash-preview:free", task="reading_check"))
    with psycopg.connect(database_url) as conn:
        log.flush(conn, NOW)
        rows = conn.execute(
            "select model, task, success, cost_usd, input_tokens, output_tokens from llm_calls "
            "where created_at=%s order by cost_usd desc, success",
            (NOW,),
        ).fetchall()
        conn.rollback()
    paid = (2000 * 1.0 + 2000 * 4.0) / 1_000_000  # thoughts count as output
    assert [(r[0], r[1], r[2], float(r[3]), r[4], r[5]) for r in rows] == [
        ("deepseek-flash", "reading_items", False, paid, 2000, 2000),
        ("deepseek-flash", "reading_items", True, paid, 2000, 2000),
        ("baidu/ernie-5.5-flash-preview:free", "reading_check", True, 0.0, 2000, 2000),
    ]
    assert log.calls == 3 and log.failed == 1 and log.pending == []
    assert log.cost_usd == 2 * paid
    assert "3 (1 failed)" in log.summary()
