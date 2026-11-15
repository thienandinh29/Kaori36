"""Export what the owner rates by hand: feedback points and AI corrections (step 2.4 spec).

    uv run python -m app.writing.export_review feedback --learner <uuid> \
        --out ../../data/private/writing/feedback.csv
    uv run python -m app.writing.export_review corrections --learner <uuid> \
        --out ../../data/private/writing/corrections.csv

`feedback`: one row per feedback point, with its quotes. The owner fills `supported` with y or n:
does the point say something true about the essay, shown by its quotes?
`corrections`: one row per correction the model proposed (shown as "gợi ý từ AI"). The owner fills
`correct` with y or n: is the suggested fix right, and the sentence was really wrong?
Both sheets quote essays, so they belong in `data/private/` (git-ignored); the scorer is
`app.evalkit.writing_review`.
"""

import argparse
import csv
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import psycopg

from app.config import get_settings

FEEDBACK_COLUMNS = ("essay_id", "criterion", "point", "kind", "point_vi", "quotes", "supported",
                    "note")  # fmt: skip
CORRECTION_COLUMNS = ("essay_id", "issue_id", "sentence", "text", "suggestion", "errant_type",
                      "node", "correct", "note")  # fmt: skip


def feedback_rows(essays: Iterable[tuple[Any, dict[str, Any]]]) -> list[dict[str, str]]:
    out = []
    for essay_id, result in essays:
        criteria = ((result.get("feedback") or {}).get("criteria")) or {}
        for criterion, points in criteria.items():
            for n, p in enumerate(points):
                out.append(
                    {
                        "essay_id": str(essay_id),
                        "criterion": criterion,
                        "point": str(n),
                        "kind": p["kind"],
                        "point_vi": p["point_vi"],
                        "quotes": " | ".join(p["quotes"]),
                        "supported": "",
                        "note": "",
                    }
                )
    return out


def correction_rows(essays: Iterable[tuple[Any, dict[str, Any]]]) -> list[dict[str, str]]:
    out = []
    for essay_id, result in essays:
        for issue in (result.get("grammar") or {}).get("issues", []):
            if issue.get("source") != "llm":
                continue
            out.append(
                {
                    "essay_id": str(essay_id),
                    "issue_id": str(issue["id"]),
                    "sentence": issue["sentence"],
                    "text": issue["text"],
                    "suggestion": issue["suggestion"] or "",
                    "errant_type": issue["errant_type"] or "",
                    "node": issue["node"] or "",
                    "correct": "",
                    "note": "",
                }
            )
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("what", choices=["feedback", "corrections"])
    parser.add_argument("--learner", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if "private" not in args.out.resolve().parts:
        print("refusing: the sheet quotes essays; write it under data/private/", file=sys.stderr)
        return 2
    with psycopg.connect(get_settings().database_url) as conn:
        essays = conn.execute(
            "select id, result from essays where learner_id=%s and status='done' "
            "and (result->>'version')::int >= 2 order by submitted_at",
            (args.learner,),
        ).fetchall()
    pairs = [(e[0], e[1]) for e in essays]
    columns: Sequence[str]
    if args.what == "feedback":
        columns, rows = FEEDBACK_COLUMNS, feedback_rows(pairs)
    else:
        columns, rows = CORRECTION_COLUMNS, correction_rows(pairs)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} rows from {len(pairs)} essays -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
