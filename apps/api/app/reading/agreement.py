"""How the blind checker compares with an expert, and with the owner (CP3, VER-001).

    uv run python -m app.reading.agreement [--out report.json]

The gate (specs/validation/step-v3.md) rests on Gold labels: an English teacher's `item_ok` verdicts
from the reviewer portal, against the checker's call before any review (`verified` = good,
`needs_review` = not good). It reports agreement and Cohen's kappa, and per stratum:
- defect escape: among items the checker verified, the share the expert says are wrong;
- false rejection: among items the checker sent to review, the share the expert says are fine;
each with an exact interval, plus overall accuracy weighted by each stratum's share of all checked
items (the portal samples the strata unequally). The owner's own decisions are reported apart, as
Bronze: a development number, never the gate.
"""

import argparse
import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from app.evalkit.stats import cohen_kappa, rate
from app.validation.gate import basis, process_supports

MIN_ITEMS = 50  # the plan's gate
ESCAPE_BAR = 0.05  # VER-001: at most 5% of faulty items let through


def _r(k: int, n: int) -> dict[str, Any]:
    r = rate(k, n)
    return {
        "k": k,
        "n": n,
        "share": None if r.point is None else round(r.point, 3),
        "low": None if r.low is None else round(r.low, 3),
        "high": None if r.high is None else round(r.high, 3),
    }


def expert_report(
    pairs: Sequence[tuple[str, str]], population: Mapping[str, int]
) -> dict[str, Any]:
    """pairs: (checker's call `verified`|`needs_review`, expert's `right`|`wrong`).

    population: how many checked items the checker verified / sent to review overall.
    """
    checker = ["good" if c == "verified" else "not_good" for c, _ in pairs]
    expert = ["good" if v == "right" else "not_good" for _, v in pairs]
    agree = sum(a == b for a, b in zip(checker, expert, strict=True))
    kappa = cohen_kappa(checker, expert)
    verified = [v for c, v in pairs if c == "verified"]
    sent = [v for c, v in pairs if c == "needs_review"]
    escape = _r(sum(v == "wrong" for v in verified), len(verified))
    false_rejection = _r(sum(v == "right" for v in sent), len(sent))
    # Accuracy of the checker's call, weighted by each stratum's share of all checked items.
    total = population.get("verified", 0) + population.get("needs_review", 0)
    weighted = None
    if total and verified and sent:
        acc_v = 1 - escape["k"] / escape["n"]
        acc_s = 1 - false_rejection["k"] / false_rejection["n"]
        weighted = round(
            (population.get("verified", 0) * acc_v + population.get("needs_review", 0) * acc_s)
            / total,
            3,
        )
    return {
        "basis": basis("gold", len(pairs), MIN_ITEMS),
        "labelled": len(pairs),
        "agreement": _r(agree, len(pairs)),
        "kappa": None if kappa is None else round(kappa, 3),
        "defect_escape": escape,
        "false_rejection": false_rejection,
        "population": dict(population),
        "weighted_accuracy": weighted,
        "process": process_supports(escape["k"], escape["n"], ESCAPE_BAR)
        | {
            "note": (
                "Serving checker-verified items rests on this: the upper 95% bound of defect "
                f"escape must be at most {ESCAPE_BAR:.0%}. With no escapes that needs at least "
                "72 verified items in the expert's sample."
            )
        },
    }


def report(rows: Sequence[tuple[str, str, str | None]]) -> dict[str, Any]:
    """The owner against the checker. rows: (checker's call, owner's status, review note)."""
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
        "basis": basis("bronze", len(rows), MIN_ITEMS),
        "reviewed": len(rows),
        "agreement": {"k": r.k, "n": r.n, "low": r.low, "high": r.high},
        "kappa": None if kappa is None else round(kappa, 3),
        "confusion": dict(sorted(confusion.items())),
        "reject_reasons": dict(reasons.most_common()),
    }
    if len(rows) < MIN_ITEMS:
        out["note"] = f"fewer than {MIN_ITEMS} reviewed items"
    return out


def expert_pairs(conn: Any) -> tuple[list[tuple[str, str]], dict[str, int]]:
    """Gold verdicts per item (experts agreeing; disputes and "unsure" left out), with the
    checker's call before any review, and the population of each stratum."""
    from app.validation.tiers import Label, effective

    rows = conn.execute(
        "select l.content_id, l.role, l.value, l.independence, "
        "case when i.status in ('approved','rejected') then i.review_was else i.status end "
        "from labels l join reading_items i on i.id = l.content_id "
        "where l.content_type='reading_item' and l.aspect='item_ok' and l.tier='gold' "
        "order by l.content_id, l.id"
    ).fetchall()
    groups: dict[str, tuple[str, list[Label]]] = {}
    for cid, role, value, key, call in rows:
        groups.setdefault(cid, (call, []))[1].append(Label(role, value, key))
    pairs = []
    for call, labels in groups.values():
        e = effective(labels)
        if (
            e.tier == "gold"
            and e.value in ("right", "wrong")
            and call
            in (
                "verified",
                "needs_review",
            )
        ):
            pairs.append((call, e.value))
    population = dict(
        conn.execute(
            "select call, count(*) from (select case when status in ('approved','rejected') "
            "then review_was else status end as call from reading_items "
            "where status in ('verified','needs_review','approved','rejected')) s "
            "where call in ('verified','needs_review') group by call"
        ).fetchall()
    )
    return pairs, population


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - database
    import psycopg

    from app.config import get_settings

    parser = argparse.ArgumentParser(prog="python -m app.reading.agreement")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    with psycopg.connect(get_settings().database_url) as conn:
        pairs, population = expert_pairs(conn)
        rows = conn.execute(
            "select review_was, status, review_note from reading_items "
            "where status in ('approved','rejected') and review_was is not null"
        ).fetchall()
    out = {"expert": expert_report(pairs, population), "owner": report(rows)}
    text = json.dumps(out, indent=2, ensure_ascii=False)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
