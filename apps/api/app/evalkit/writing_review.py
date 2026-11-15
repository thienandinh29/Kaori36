"""Score the owner's two hand ratings (step 2.4 spec, "Measured before opening it").

    uv run python -m app.evalkit.writing_review feedback \
        ../../data/private/writing/feedback.csv
    uv run python -m app.evalkit.writing_review corrections \
        ../../data/private/writing/corrections.csv

Input: a sheet from `app.writing.export_review` with the owner's `supported` (feedback) or
`correct` (corrections) column filled with y or n. Output: JSON metrics only, safe to commit.
- feedback: the share of points the owner found supported by their quotes, with an exact 95%
  interval, per criterion and per kind (strength / issue), and how many essays were rated. The
  quotes were already checked to be in the essay; this measures whether they support the point.
- corrections: precision of the model's proposed fixes with an exact interval, per ERRANT type.
  Counting AI corrections towards mastery needs at least 50 rated and a precision the owner finds
  acceptable (proposed: lower bound of the interval at or above 0.80). The tool states what it
  found; the owner decides.
"""

import argparse
import csv
import json
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from app.evalkit.stats import rate

FEEDBACK_MIN_POINTS = 60  # about 20 essays at 3 points a criterion is plenty; fewer is a warning
CORRECTIONS_MIN = 50
CORRECTIONS_PROPOSED_LOWER_BOUND = 0.80
YES = {"y", "yes", "1", "true", "đ", "đúng"}
NO = {"n", "no", "0", "false", "s", "sai"}


def verdict(value: str) -> bool | None:
    """True / False for y / n (also 1/0, đúng/sai); None when blank. Anything else is an error."""
    v = value.strip().lower()
    if not v:
        return None
    if v in YES:
        return True
    if v in NO:
        return False
    raise ValueError(f"cannot read {value!r}: use y or n")


def _rate(k: int, n: int) -> dict[str, Any]:
    r = rate(k, n)
    return {
        "yes": k,
        "rated": n,
        "share": None if r.point is None else round(r.point, 4),
        "interval": None
        if r.low is None or r.high is None
        else [round(r.low, 4), round(r.high, 4)],
    }


def score_feedback(rows: Sequence[dict[str, str]]) -> dict[str, Any]:
    by_c: dict[str, list[bool]] = defaultdict(list)
    by_k: dict[str, list[bool]] = defaultdict(list)
    rated_essays: set[str] = set()
    unrated = 0
    for r in rows:
        v = verdict(r["supported"])
        if v is None:
            unrated += 1
            continue
        by_c[r["criterion"]].append(v)
        by_k[r["kind"]].append(v)
        rated_essays.add(r["essay_id"])
    every = [v for vs in by_c.values() for v in vs]
    note = (
        f"{len(every)} points rated; at least {FEEDBACK_MIN_POINTS} (about 20 essays) gives a "
        "usable interval."
        if len(every) < FEEDBACK_MIN_POINTS
        else "Enough points rated for a usable interval."
    )
    return {
        "kind": "feedback_supported_by_quotes",
        "essays_rated": len(rated_essays),
        "unrated_points": unrated,
        "overall": _rate(sum(every), len(every)),
        "per_criterion": {c: _rate(sum(v), len(v)) for c, v in sorted(by_c.items())},
        "per_kind": {k: _rate(sum(v), len(v)) for k, v in sorted(by_k.items())},
        "note": note,
    }


def score_corrections(rows: Sequence[dict[str, str]]) -> dict[str, Any]:
    by_type: dict[str, list[bool]] = defaultdict(list)
    unrated = 0
    for r in rows:
        v = verdict(r["correct"])
        if v is None:
            unrated += 1
            continue
        t = r["errant_type"].split(":")[-1] or "untyped"
        by_type[t].append(v)
    every = [v for vs in by_type.values() for v in vs]
    overall = _rate(sum(every), len(every))
    low = overall["interval"][0] if overall["interval"] else None
    if len(every) < CORRECTIONS_MIN:
        note = f"{len(every)} rated; at least {CORRECTIONS_MIN} are needed before this means much."
    elif low is not None and low >= CORRECTIONS_PROPOSED_LOWER_BOUND:
        note = (
            f"Lower bound {low:.2f} is at or above the proposed "
            f"{CORRECTIONS_PROPOSED_LOWER_BOUND}: the owner may decide to let AI corrections "
            "count (same draft rule as the error map)."
        )
    else:
        note = (
            f"Lower bound {low:.2f} is below the proposed {CORRECTIONS_PROPOSED_LOWER_BOUND}: "
            "keep AI corrections as hints that never move mastery."
        )
    return {
        "kind": "ai_corrections_precision",
        "unrated": unrated,
        "overall": overall,
        "per_type": {t: _rate(sum(v), len(v)) for t, v in sorted(by_type.items())},
        "note": note,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("what", choices=["feedback", "corrections"])
    parser.add_argument("sheet", type=Path)
    args = parser.parse_args(argv)
    with args.sheet.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    column = "supported" if args.what == "feedback" else "correct"
    if rows and column not in rows[0]:
        print(f"the sheet has no {column!r} column: is it the {args.what} sheet?")
        return 2
    try:
        report = score_feedback(rows) if args.what == "feedback" else score_corrections(rows)
    except ValueError as err:
        print(err)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
