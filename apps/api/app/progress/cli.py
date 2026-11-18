"""Record independent test results and report progress (specs/validation/step-v4.md).

    uv run python -m app.progress.cli add --learner ID --skill reading \\
        --paper "Cambridge 18 Test 1" --timed --raw 31/40 --band 7.0 --marked-by answer_key \\
        [--baseline] [--on 2026-11-20]
    uv run python -m app.progress.cli schedule --learner ID
    uv run python -m app.progress.cli report --learner ID [--out ../../data/private/progress.json]

Only this package touches `progress_tests` (evaluation data). Results are scores only: never the
paper's questions or answers.
"""

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from app.config import REPO_ROOT
from app.progress.study import SKILLS, Result, report, schedule, truth_of

KNOWN = 0.9
DEFAULT_OUT = REPO_ROOT / "data" / "private" / "progress-report.json"


def snapshot(conn: psycopg.Connection, learner: str) -> dict[str, Any]:
    """NodeTrail's own estimates now, read-only: mastery per subject and the latest level test."""
    subjects = {
        slug: {"concepts": n, "mean_p_known": round(float(mean), 3), "known": known}
        for slug, n, mean, known in conn.execute(
            "select s.slug, count(*), avg(m.p_known), count(*) filter (where m.p_known >= %s) "
            "from mastery m join concepts c on c.id = m.concept_id "
            "join subjects s on s.id = c.subject_id where m.learner_id::text = %s group by s.slug",
            (KNOWN, learner),
        ).fetchall()
    }
    row = conn.execute(
        "select result, finished_at from level_tests where learner_id::text=%s and result is "
        "not null order by finished_at desc limit 1",
        (learner,),
    ).fetchone()
    level = None
    if row is not None:
        result, at = row
        level = {
            "grammar_level": result.get("grammar_level"),
            "vocab_level": result.get("vocab_level"),
            "finished_at": at.isoformat() if at else None,
        }
    return {"subjects": subjects, "level_test": level}


def add(conn: psycopg.Connection, learner: str, r: Result) -> str:
    if r.skill not in SKILLS:
        raise ValueError(f"skill is one of {SKILLS}")
    truth_of(r.marked_by)  # validates
    if r.raw_k is None and r.band is None:
        raise ValueError("give a raw score, a band, or both")
    row = conn.execute(
        "insert into progress_tests(learner_id,taken_on,baseline,skill,paper,timed,raw_k,raw_n,"
        "band,marked_by,snapshot) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) returning id::text",
        (learner, r.taken_on, r.baseline, r.skill, r.paper, r.timed, r.raw_k, r.raw_n, r.band,
         r.marked_by, Jsonb(snapshot(conn, learner))),
    ).fetchone()  # fmt: skip
    assert row is not None
    return str(row[0])


def results(conn: psycopg.Connection, learner: str) -> list[Result]:
    rows = conn.execute(
        "select taken_on,skill,paper,timed,marked_by,baseline,raw_k,raw_n,band,snapshot "
        "from progress_tests where learner_id::text=%s order by taken_on, skill",
        (learner,),
    ).fetchall()
    return [
        Result(t, s, p, timed, m, b, k, n, None if band is None else float(band), snap)
        for t, s, p, timed, m, b, k, n, band, snap in rows
    ]


def when(conn: psycopg.Connection, learner: str, today: date) -> dict[str, Any]:
    row = conn.execute(
        "select min(taken_on) filter (where baseline), max(taken_on) from progress_tests "
        "where learner_id::text=%s",
        (learner,),
    ).fetchone()
    baseline, last = (None, None) if row is None else row
    return schedule(baseline, last, today)


def _raw(text: str | None) -> tuple[int | None, int | None]:
    if not text:
        return None, None
    k, _, n = text.partition("/")
    return int(k), int(n)


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - database
    from app.config import get_settings

    parser = argparse.ArgumentParser(prog="python -m app.progress.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("--learner", required=True)
    a.add_argument("--skill", required=True, choices=SKILLS)
    a.add_argument("--paper", required=True, help="which sample paper or mock (no content)")
    a.add_argument("--timed", action="store_true", help="taken under exam conditions")
    a.add_argument("--raw", help="raw score as k/n, e.g. 31/40")
    a.add_argument("--band", type=float)
    a.add_argument("--marked-by", required=True, choices=("answer_key", "trained_rater", "self"))
    a.add_argument("--baseline", action="store_true")
    a.add_argument("--on", type=date.fromisoformat, default=date.today())
    for name in ("schedule", "report"):
        p = sub.add_parser(name)
        p.add_argument("--learner", required=True)
    sub.choices["report"].add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    with psycopg.connect(get_settings().database_url) as conn:
        if args.cmd == "add":
            k, n = _raw(args.raw)
            r = Result(args.on, args.skill, args.paper, args.timed, args.marked_by,
                       args.baseline, k, n, args.band)  # fmt: skip
            try:
                out: Any = {
                    "id": add(conn, args.learner, r),
                    "next": when(conn, args.learner, args.on),
                }
            except (ValueError, psycopg.errors.IntegrityError) as err:
                parser.error(str(err).splitlines()[0])
        elif args.cmd == "schedule":
            out = when(conn, args.learner, date.today())
        else:
            out = report(results(conn, args.learner))
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", "utf-8")
            print(f"written to {args.out} (private: keep it out of git)")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
