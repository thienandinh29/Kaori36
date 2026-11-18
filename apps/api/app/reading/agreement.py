"""How often the owner agrees with the blind checker (specs/listening-reading/step-4.2c.md).

    uv run python -m app.reading.agreement [--out report.json]

Pairs, one per reviewed item: the checker's call (`verified` = good, `needs_review` = not good)
and the owner's decision (approve = good, reject = not good). Reports agreement with an exact
interval, Cohen's kappa, the confusion counts and the reject reasons.
"""

import argparse
import json
import re
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from app.evalkit.stats import cohen_kappa, rate

MIN_ITEMS = 50  # the plan's gate


def report(rows: Sequence[tuple[str, str, str | None]]) -> dict[str, Any]:
    """rows: (checker's call, owner's status, review note)."""
    checker = ["good" if was == "verified" else "not_good" for was, _, _ in rows]
    owner = ["good" if status == "approved" else "not_good" for _, status, _ in rows]
    agree = sum(a == b for a, b in zip(checker, owner, strict=True))
    r = rate(agree, len(rows))
    kappa = cohen_kappa(checker, owner)
    reasons = Counter(
        m.group(1)
        for _, status, note in rows
        if status == "rejected" and note and (m := re.match(r"\[(\w+)\]", note))
    )
    confusion = Counter(f"checker_{a}__owner_{b}" for a, b in zip(checker, owner, strict=True))
    out: dict[str, Any] = {
        "reviewed": len(rows),
        "agreement": {"k": r.k, "n": r.n, "low": r.low, "high": r.high},
        "kappa": None if kappa is None else round(kappa, 3),
        "confusion": dict(sorted(confusion.items())),
        "reject_reasons": dict(reasons.most_common()),
    }
    if len(rows) < MIN_ITEMS:
        out["note"] = f"fewer than {MIN_ITEMS} reviewed items: the gate is not measured yet"
    return out


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - database
    import psycopg

    from app.config import get_settings

    parser = argparse.ArgumentParser(prog="python -m app.reading.agreement")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    with psycopg.connect(get_settings().database_url) as conn:
        rows = conn.execute(
            "select review_was, status, review_note from reading_items "
            "where status in ('approved','rejected') and review_was is not null"
        ).fetchall()
    text = json.dumps(report(rows), indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
