"""Step 4.2d: generated Reading questions travel as committed files."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
import yaml  # type: ignore[import-untyped]
from psycopg.types.json import Jsonb

from app.reading.itemfile import STALE, drop_stale, export, import_
from app.reading.pipeline import generate_text
from app.validation.cli import backfill

from .test_generation import PASSAGE, generated

NOW = datetime(2026, 11, 19, 3, 0, tzinfo=UTC)


def _rows(conn: psycopg.Connection[Any]) -> list[tuple[Any, ...]]:
    return conn.execute(
        "select id, text_slug, passage_sha256, kind, status, item, problems, checker_answer, "
        "checker_model, generated_at, checked_at, reviewed_at, review_note, review_was, check_view "
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
            "added": len(before), "updated": 0, "kept": 0, "stale": 0,
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
        assert counts == {"added": n, "updated": 0, "kept": 0, "stale": n}
        assert (
            import_(conn, tmp_path, {})["kept"] == n
        )  # a text no longer in the bank: kept, nothing added
        conn.rollback()


def test_a_newer_check_reaches_an_undecided_row_but_never_a_decided_one(
    database_url: str, tmp_path: Path
) -> None:
    """Step 4.3c: a question imported before its blind check used to stay unchecked forever."""
    later = datetime(2026, 11, 20, 3, 0, tzinfo=UTC)
    with psycopg.connect(database_url) as conn:

        async def gen(system: str, text: str):  # type: ignore[no-untyped-def]
            return generated()

        asyncio.run(generate_text(conn, "bees", PASSAGE, gen, NOW))
        # The laptop imported the file while every question still waited for its check, and
        # the owner has since rejected one of them.
        conn.execute("update reading_items set status='rejected' where id='bees-tfng-2'")
        # The daily batch checked them elsewhere; its file arrives.
        sandbox = tmp_path / "batch"
        conn.execute(
            "update reading_items set status='verified', checker_answer='B', "
            "checker_model='baidu/ernie', checked_at=%s, check_view='shuffled' "
            "where id in ('bees-mcq-1','bees-tfng-2')",
            (later,),
        )
        export(conn, {"bees": ("openstax-reading", PASSAGE)}, sandbox)
        conn.execute(
            "update reading_items set status='generated', checker_answer=null, "
            "checker_model=null, checked_at=null, check_view=null where id='bees-mcq-1'"
        )
        conn.execute("update reading_items set status='rejected' where id='bees-tfng-2'")
        counts = import_(conn, sandbox, {"bees": PASSAGE})
        assert counts["added"] == 0 and counts["updated"] == 1
        row = conn.execute(
            "select status, checker_answer, checker_model, checked_at, check_view "
            "from reading_items where id='bees-mcq-1'"
        ).fetchone()
        assert row == ("verified", "B", "baidu/ernie", later, "shuffled")
        decided = conn.execute("select status from reading_items where id='bees-tfng-2'")
        assert decided.fetchone() == ("rejected",)  # the owner's decision stands
        # The same file again changes nothing; an older check never replaces a newer one.
        assert import_(conn, sandbox, {"bees": PASSAGE})["updated"] == 0
        conn.execute(
            "update reading_items set checked_at=%s, checker_answer='C' where id='bees-mcq-1'",
            (later.replace(day=21),),
        )
        assert import_(conn, sandbox, {"bees": PASSAGE})["updated"] == 0
        kept = conn.execute("select checker_answer from reading_items where id='bees-mcq-1'")
        assert kept.fetchone() == ("C",)
        conn.rollback()


def test_a_newer_check_of_a_decided_row_comes_in_without_touching_the_decision(
    database_url: str, tmp_path: Path
) -> None:
    """21 Nov: a decided row kept its old check, and the laptop's export wrote it back over main."""
    early = datetime(2026, 11, 19, 3, 0, tzinfo=UTC)
    later = datetime(2026, 11, 20, 3, 0, tzinfo=UTC)
    reviewed = datetime(2026, 11, 20, 5, 0, tzinfo=UTC)
    with psycopg.connect(database_url) as conn:

        async def gen(system: str, text: str):  # type: ignore[no-untyped-def]
            return generated()

        asyncio.run(generate_text(conn, "bees", PASSAGE, gen, NOW))
        # main's file: the owner rejected it, then it was re-checked in the shown order.
        conn.execute(
            "update reading_items set status='rejected', review_note='two answers', "
            "review_was='needs_review', reviewed_at=%s, checker_answer='B', "
            "checker_model='baidu/ernie', checked_at=%s, check_view='shuffled' "
            "where id='bees-mcq-1'",
            (reviewed, later),
        )
        main = tmp_path / "main"
        export(conn, {"bees": ("openstax-reading", PASSAGE)}, main)
        # The laptop has the same decision with the older check.
        conn.execute(
            "update reading_items set checker_answer='A', checker_model='dots', "
            "checked_at=%s, check_view=null where id='bees-mcq-1'",
            (early,),
        )
        assert import_(conn, main, {"bees": PASSAGE})["updated"] == 1
        row = conn.execute(
            "select status, review_note, review_was, reviewed_at, checker_answer, checker_model, "
            "checked_at, check_view from reading_items where id='bees-mcq-1'"
        ).fetchone()
        assert row == (
            "rejected",
            "two answers",
            "needs_review",
            reviewed,
            "B",
            "baidu/ernie",
            later,
            "shuffled",
        )
        # Exporting now reproduces main's file exactly.
        again = tmp_path / "again"
        export(conn, {"bees": ("openstax-reading", PASSAGE)}, again)
        for f in main.glob("*.yaml"):
            assert (again / f.name).read_text(encoding="utf-8") == f.read_text(encoding="utf-8")
        # An older check in a file never replaces the newer one on a decided row.
        conn.execute(
            "update reading_items set checked_at=%s, checker_answer='C' where id='bees-mcq-1'",
            (later.replace(day=21),),
        )
        assert import_(conn, main, {"bees": PASSAGE})["updated"] == 0
        conn.rollback()


def _count(conn: psycopg.Connection[Any], sql: str, *params: object) -> int:
    row = conn.execute(sql, params).fetchone()
    assert row is not None
    return int(row[0])


def test_a_stale_unchecked_row_is_dropped_carried_by_import_and_never_labelled(
    database_url: str, tmp_path: Path
) -> None:
    stale = Jsonb([STALE])
    with psycopg.connect(database_url) as conn:

        async def gen(system: str, text: str):  # type: ignore[no-untyped-def]
            return generated()

        asyncio.run(generate_text(conn, "bees", PASSAGE, gen, NOW))
        conn.execute(
            "update reading_items set status='verified', checker_answer='TRUE', "
            "checker_model='baidu/ernie', checked_at=%s where id='bees-tfng-1'",
            (NOW,),
        )
        conn.commit()
        unchecked = _count(
            conn, "select count(*) from reading_items where text_slug='bees' and status='generated'"
        )
        assert unchecked >= 1
        # The text is unchanged, or gone from the bank: nothing is dropped.
        assert drop_stale(conn, {"bees": PASSAGE}) == 0
        assert drop_stale(conn, {}) == 0
        # Before the drop, another copy of the database (the owner's laptop) has these files.
        export(conn, {"bees": ("openstax-reading", PASSAGE)}, tmp_path / "before")
        # The passage is replaced: only the unchecked rows are dropped; the check is kept.
        edited = PASSAGE + "\n\nEdited."
        assert drop_stale(conn, {"bees": edited}) == unchecked
        status = _count(
            conn, "select count(*) from reading_items where id='bees-tfng-1' and status='verified'"
        )
        assert status == 1
        sql = "select count(*) from reading_items where text_slug='bees' and problems=%s"
        assert _count(conn, sql + " and status='dropped'", stale) == unchecked
        # The backfill gives the stale drops no code-check label.
        backfill(conn)
        labelled = (
            "select count(*) from labels where content_type='reading_item' and content_id in "
            "(select id from reading_items where problems=%s)"
        )
        assert _count(conn, labelled, stale) == 0
        # The laptop: its rows are still unchecked; importing the new files carries the drop.
        export(conn, {"bees": ("openstax-reading", PASSAGE)}, tmp_path / "after")
        conn.execute("delete from labels where content_type='reading_item'")
        conn.execute("delete from reading_items where text_slug='bees'")
        import_(conn, tmp_path / "before", {"bees": PASSAGE})
        assert _count(conn, sql, stale) == 0
        counts = import_(conn, tmp_path / "after", {"bees": edited})
        assert counts["updated"] == unchecked
        assert _count(conn, sql + " and status='dropped'", stale) == unchecked
        conn.execute("delete from reading_items where text_slug='bees'")
        conn.commit()
