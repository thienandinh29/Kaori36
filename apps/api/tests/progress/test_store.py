"""Step V4: recording results with NodeTrail's snapshot."""

from collections.abc import Iterator
from datetime import date

import psycopg
import pytest
from psycopg.types.json import Jsonb

from app.progress.cli import add, results, snapshot, when
from app.progress.study import Result, report


@pytest.fixture
def conn(database_url: str) -> Iterator[psycopg.Connection]:
    with psycopg.connect(database_url) as c:
        yield c
        c.rollback()


def test_snapshot_add_and_report(conn: psycopg.Connection) -> None:
    learner = conn.execute(
        "insert into learners(display_name) values ('O') returning id::text"
    ).fetchone()
    assert learner is not None
    lid = learner[0]
    subject = conn.execute(
        "insert into subjects(slug,name_vi,name_en) values ('english-ielts','A','A') "
        "on conflict (slug) do update set slug=excluded.slug returning id"
    ).fetchone()
    assert subject is not None
    for slug, p in (("v4-a", 0.95), ("v4-b", 0.35)):
        cid = conn.execute(
            "insert into concepts(subject_id,slug,name_vi,name_en) values (%s,%s,'x','x') "
            "returning id",
            (subject[0], slug),
        ).fetchone()
        assert cid is not None
        conn.execute(
            "insert into mastery(learner_id,concept_id,p_known) values (%s,%s,%s)", (lid, cid[0], p)
        )
    conn.execute(
        "insert into level_tests(learner_id,course,phase,result,finished_at) "
        "values (%s,'english-ielts','done',%s,now())",
        (lid, Jsonb({"grammar_level": "B1", "vocab_level": "A2"})),
    )
    snap = snapshot(conn, lid)
    assert snap["subjects"]["english-ielts"] == {"concepts": 2, "mean_p_known": 0.65, "known": 1}
    assert snap["level_test"]["grammar_level"] == "B1"
    before = conn.execute("select count(*) from mastery").fetchone()
    base = Result(date(2026, 11, 20), "reading", "Sample 1", True, "answer_key", True, 24, 40, 6.0)
    add(conn, lid, base)
    assert conn.execute("select count(*) from mastery").fetchone() == before  # read-only
    with pytest.raises(psycopg.errors.UniqueViolation), conn.transaction():
        add(conn, lid, base)  # one baseline per skill
    with pytest.raises(ValueError):
        add(conn, lid, Result(date(2026, 11, 20), "reading", "x", True, "answer_key"))
    add(conn, lid, Result(date(2026, 12, 18), "reading", "Sample 2", True, "answer_key",
                          False, 28, 40, 6.5))  # fmt: skip
    got = results(conn, lid)
    assert [r.band for r in got] == [6.0, 6.5]
    assert got[0].snapshot["subjects"]["english-ielts"]["mean_p_known"] == 0.65
    sittings = report(got)["skills"]["reading"]["sittings"]
    assert sittings[1]["change_from_baseline"] == 0.5 and sittings[1]["nodetrail_change"] == 0.0
    crit = {"fc": 7, "lr": 7, "gra": 6, "p": 7}
    add(conn, lid, Result(date(2026, 12, 18), "speaking", "Mock 1", True, "trained_rater",
                          band=6.5, criteria=crit))  # fmt: skip
    with pytest.raises(ValueError):  # a Reading sitting has no criteria
        add(conn, lid, Result(date(2026, 12, 18), "reading", "x", True, "answer_key",
                              band=6.0, criteria=crit))  # fmt: skip
    with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():  # nor in the table
        conn.execute(
            "update progress_tests set criteria=%s where learner_id::text=%s and skill='reading'",
            (Jsonb(crit), lid),
        )
    spoken = [r for r in results(conn, lid) if r.skill == "speaking"]
    assert spoken[0].criteria == crit and spoken[0].band == 6.5
    assert report(spoken)["skills"]["speaking"]["sittings"][0]["lowest"] == ["gra"]
    s = when(conn, lid, date(2027, 1, 20))
    assert (s["next_due"], s["overdue_days"]) == ("2027-01-15", 5)
