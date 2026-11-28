"""Make testers, invite links and the report (specs/speaking/step-5.5.md).

    uv run python -m app.testers.cli add --label "Mai (bạn cùng lớp)"
    uv run python -m app.testers.cli invite --tester ID [--days 7] [--base-url https://...]
    uv run python -m app.testers.cli list
    uv run python -m app.testers.cli revoke --tester ID
    uv run python -m app.testers.cli report [--out ../../data/private/testers-report.json]

An invite link is shown once; only its hash is stored. A link works once. The report is private.
"""

import argparse
import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg

from app.config import REPO_ROOT
from app.testers import store
from app.testers.limits import VIETNAM
from app.testers.report import Enrolled, Number, Sitting, iso_week, report

DEFAULT_OUT = REPO_ROOT / "data" / "private" / "testers-report.json"


def collect(
    conn: psycopg.Connection[Any],
) -> tuple[list[Enrolled], list[Sitting], list[Number]]:
    """The report's inputs. Numbers are those of answers that count as evidence: a strict mock's
    answers and the first try of a practised question (repeats are practice)."""
    testers = [
        Enrolled(r[0], r[1], r[2] is not None, r[3] == store.RESEARCH_NOTICE)
        for r in conn.execute(
            "select learner_id,label,revoked_at,research_consent from testers"
        ).fetchall()
    ]
    sittings = [
        Sitting(r[0], r[1].astimezone(VIETNAM).date(), r[2])
        for r in conn.execute(
            "select t.learner_id,t.started_at,t.mode from speaking_tests t "
            "join testers x on x.learner_id=t.learner_id"
        ).fetchall()
    ]
    numbers = []
    for learner, at, measures in conn.execute(
        "select t.learner_id,a.recorded_at,a.measures from speaking_answers a "
        "join speaking_tests t on t.id=a.sitting_id join testers x on x.learner_id=t.learner_id "
        "where x.research_consent=%s and a.measures is not null and t.try_no=1",
        (store.RESEARCH_NOTICE,),
    ).fetchall():
        if not measures.get("words"):
            continue
        numbers.append(
            Number(
                learner,
                iso_week(at.astimezone(VIETNAM).date()),
                measures.get("speech_rate"),
                measures.get("pauses", {}).get("per_minute"),
            )
        )
    return testers, sittings, numbers


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - database
    from app.config import get_settings

    parser = argparse.ArgumentParser(prog="python -m app.testers.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("add").add_argument("--label", required=True)
    inv = sub.add_parser("invite")
    inv.add_argument("--tester", required=True)
    inv.add_argument("--days", type=int, default=store.INVITE_DAYS)
    inv.add_argument("--base-url", default="http://localhost:3000")
    sub.add_parser("list")
    sub.add_parser("revoke").add_argument("--tester", required=True)
    rep = sub.add_parser("report")
    rep.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    now = datetime.now(UTC)
    with psycopg.connect(get_settings().database_url) as conn:
        if args.cmd == "add":
            tester, learner = store.create_tester(conn, args.label)
            print(json.dumps({"tester": str(tester), "learner": str(learner)}))
        elif args.cmd == "invite":
            token = store.invite(conn, UUID(args.tester), now, args.days)
            print(f"{args.base_url.rstrip('/')}/vao/{token}")
            print(f"(works once, for {args.days} days; shown only now)")
        elif args.cmd == "list":
            for r in conn.execute(
                "select id,label,revoked_at,research_consent from testers order by created_at"
            ).fetchall():
                off = " (switched off)" if r[2] else ""
                print(f"{r[0]}  {r[1]}{off}  research={'yes' if r[3] else 'no'}")
        elif args.cmd == "revoke":
            print(
                "switched off" if store.revoke(conn, UUID(args.tester), now) else "no such tester"
            )
        else:
            out = report(*collect(conn), date.today())
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", "utf-8")
            print(f"written to {args.out} (private: keep it out of git)")
            print(json.dumps(out["retention"], indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
