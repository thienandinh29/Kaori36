"""Step 4.2d: generated Reading questions travel as committed files."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
import yaml  # type: ignore[import-untyped]

from app.reading.itemfile import export, import_
from app.reading.pipeline import generate_text
from app.validation.cli import backfill

from .test_generation import PASSAGE, generated

NOW = datetime(2026, 11, 19, 3, 0, tzinfo=UTC)


def _rows(conn: psycopg.Connection[Any]) -> list[tuple[Any, ...]]:
    return conn.execute(
        "select id, text_slug, passage_sha256, kind, status, item, problems, checker_answer, "
        "checker_model, generated_at, checked_at, reviewed_at, review_note, review_was "
        "from reading_items where text_slug='bees' order by id"
    ).fetchall()


def test_round_trip_keeps_rows_and_never_overwrites(database_url: str, tmp_path: Path) -> None:
    with psycopg.connect(database_url) as conn:

        async def gen(system: str, text: str):  # type: ignore[no-untyped-def]
            return generated()

        asyncio.run(generate_text(conn, "bees", PASSAGE, gen, NOW))
        conn.execute(
            "update reading_items set status='verified', checker_answer='TRUE', "
            "checker_model='baidu/ernie', checked_at=%s where id='bees-tfng-1'",
            (NOW,),
        )
        before = _rows(conn)
        assert export(conn, {"bees": ("openstax-reading", PASSAGE)}, tmp_path) == len(before)
        doc = yaml.safe_load((tmp_path / "bees.yaml").read_text("utf-8"))
        assert doc["source"] == "openstax-reading" and len(doc["versions"]) == 1
        # A fresh database: everything comes back as it was.
        conn.execute("delete from reading_items where text_slug='bees'")
        assert import_(conn, tmp_path, {"bees": PASSAGE}) == {
            "added": len(before), "kept": 0, "stale": 0,
        }  # fmt: skip
        assert _rows(conn) == before
        # A review made since is never overwritten by a second import.
        conn.execute(
            "update reading_items set status='approved', review_was='verified', reviewed_at=%s "
            "where id='bees-tfng-1'",
            (NOW,),
        )
        assert import_(conn, tmp_path, {"bees": PASSAGE})["added"] == 0
        status = conn.execute("select status from reading_items where id='bees-tfng-1'").fetchone()
        assert status == ("approved",)
        # The checks become labels.
        assert backfill(conn)["reading_model"] >= 1
        conn.rollback()


def test_a_changed_passage_is_reported_stale(database_url: str, tmp_path: Path) -> None:
    with psycopg.connect(database_url) as conn:

        async def gen(system: str, text: str):  # type: ignore[no-untyped-def]
            return generated()

        asyncio.run(generate_text(conn, "bees", PASSAGE, gen, NOW))
        n = export(conn, {"bees": ("openstax-reading", PASSAGE)}, tmp_path)
        conn.execute("delete from reading_items where text_slug='bees'")
        counts = import_(conn, tmp_path, {"bees": PASSAGE + "\n\nEdited."})
        assert counts == {"added": n, "kept": 0, "stale": n}
        assert (
            import_(conn, tmp_path, {})["kept"] == n
        )  # a text no longer in the bank: kept, nothing added
        conn.rollback()
