"""FORGET-001: what is forgotten after about a week (specs/forget-001/spec.md). Pure except `main`.

Vocabulary: every card's answers are replayed through app/engine/srs.py exactly as the vocabulary
service applied them (a new card at the first answer, then `review(correct)` at each answer). Before
each review after the first, FSRS's predicted recall at that moment is compared with what happened.
Grammar: delayed re-checks (grammar_rechecks) against the hypothesis bar of 80% retained.
No result is claimed before the experiment's minimum: the report says whether it is met.
"""

import argparse
import json
import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from fsrs import Card

from app.engine import srs
from app.evalkit.stats import rate

WEEK_MIN_DAYS = 5.0
WEEK_MAX_DAYS = 10.0
MIN_DELAYED = 200  # the experiment's minimum of delayed vocabulary reviews
MIN_WORD_DELAYED = 3
RECHECK_BAR = 0.80
EPS = 1e-6


@dataclass(frozen=True)
class Review:
    card: str  # "<list>/<word_key>"
    kind: str
    correct: bool
    at: datetime


@dataclass(frozen=True)
class Prediction:
    card: str
    kind: str
    predicted: float  # FSRS's recall probability just before the review
    elapsed_days: float  # since the previous review of this card
    correct: bool


def replay(reviews: Iterable[Review]) -> list[Prediction]:
    """Predictions for every review after a card's first, in the order they happened."""
    scheduler = srs.make_scheduler()
    by_card: dict[str, list[Review]] = {}
    for r in reviews:
        by_card.setdefault(r.card, []).append(r)
    out: list[Prediction] = []
    for card, rows in by_card.items():
        rows.sort(key=lambda r: r.at)
        state = srs.new_card(rows[0].at).state
        previous: datetime | None = None
        for r in rows:
            if previous is not None:
                p = scheduler.get_card_retrievability(Card.from_dict(state), current_datetime=r.at)
                elapsed = (r.at - previous).total_seconds() / 86400
                out.append(Prediction(card, r.kind, float(p), elapsed, r.correct))
            state = srs.review(state, r.correct, r.at).state
            previous = r.at
    return out


def _interval(k: int, n: int) -> dict[str, Any]:
    x = rate(k, n)
    return {"k": k, "n": n,
            "share": None if x.point is None else round(x.point, 3),
            "low": None if x.low is None else round(x.low, 3),
            "high": None if x.high is None else round(x.high, 3)}  # fmt: skip


def scores(preds: Sequence[Prediction]) -> dict[str, Any]:
    """Calibration by decile, ECE, Brier and log loss, next to a constant (in-sample) baseline."""
    n = len(preds)
    if n == 0:
        return {"n": 0}
    base = sum(p.correct for p in preds) / n
    deciles = []
    ece = 0.0
    for d in range(10):
        lo, hi = d / 10, (d + 1) / 10
        group = [p for p in preds if lo <= p.predicted < hi or (d == 9 and p.predicted == 1.0)]
        if not group:
            continue
        mean_p = sum(p.predicted for p in group) / len(group)
        actual = sum(p.correct for p in group)
        ece += len(group) / n * abs(mean_p - actual / len(group))
        deciles.append({"range": [lo, hi], "mean_predicted": round(mean_p, 3),
                        "actual": _interval(actual, len(group))})  # fmt: skip

    def brier(f: Callable[[Prediction], float]) -> float:
        return round(sum((f(p) - p.correct) ** 2 for p in preds) / n, 4)

    def log_loss(f: Callable[[Prediction], float]) -> float:
        total = 0.0
        for p in preds:
            q = min(1 - EPS, max(EPS, f(p)))
            total -= math.log(q if p.correct else 1 - q)
        return round(total / n, 4)

    return {
        "n": n,
        "recall": _interval(sum(p.correct for p in preds), n),
        "deciles": deciles,
        "ece": round(ece, 4),
        "brier": {"fsrs": brier(lambda p: p.predicted), "constant": brier(lambda p: base)},
        "log_loss": {"fsrs": log_loss(lambda p: p.predicted), "constant": log_loss(lambda p: base)},
        "constant_note": "the constant is the overall recall share, fitted on the same data",
    }


def delayed(preds: Sequence[Prediction]) -> list[Prediction]:
    return [p for p in preds if WEEK_MIN_DAYS <= p.elapsed_days <= WEEK_MAX_DAYS]


def retention(
    preds: Sequence[Prediction], category: Callable[[Prediction], str | None]
) -> dict[str, Any]:
    groups: dict[str, list[bool]] = {}
    for p in preds:
        c = category(p)
        if c is not None:
            groups.setdefault(c, []).append(p.correct)
    return {c: _interval(sum(v), len(v)) for c, v in sorted(groups.items())}


def weakest_words(preds: Sequence[Prediction], limit: int = 15) -> list[dict[str, Any]]:
    by_word: dict[str, list[bool]] = {}
    for p in preds:
        by_word.setdefault(p.card, []).append(p.correct)
    rows = [(c, sum(v), len(v)) for c, v in by_word.items() if len(v) >= MIN_WORD_DELAYED]
    rows.sort(key=lambda r: (r[1] / r[2], -r[2]))
    return [{"card": c, **_interval(k, n)} for c, k, n in rows[:limit]]


@dataclass(frozen=True)
class Recheck:
    node: str
    correct: bool
    days_since_evidence: float


def _days_band(days: float) -> str:
    return "5-7" if days < 8 else ("8-14" if days < 15 else "15+")


def recheck_report(rows: Sequence[Recheck]) -> dict[str, Any]:
    total = _interval(sum(r.correct for r in rows), len(rows))
    by_band: dict[str, list[bool]] = {}
    for r in rows:
        by_band.setdefault(_days_band(r.days_since_evidence), []).append(r.correct)
    high = total["high"]
    return {
        "answered": len(rows),
        "retained": total,
        "by_days_since_evidence": {
            b: _interval(sum(v), len(v)) for b, v in sorted(by_band.items())
        },
        "bar": RECHECK_BAR,
        "reading": (
            "not enough re-checks yet"
            if len(rows) < 20
            else "below the bar: BKT overestimates what is kept"
            if high is not None and high < RECHECK_BAR
            else "consistent with the bar (or not yet distinguishable from it)"
        ),
    }


def report(
    reviews: Iterable[Review],
    words: Mapping[str, Mapping[str, str | None]],
    rechecks: Sequence[Recheck],
) -> dict[str, Any]:
    """words: card -> {"level", "topic"} from the word list (missing words are left out of those
    breakdowns)."""
    preds = replay(reviews)
    week = delayed(preds)
    return {
        "experiment": "FORGET-001",
        "minimum_met": len(week) >= MIN_DELAYED,
        "minimum": f"at least {MIN_DELAYED} reviews {WEEK_MIN_DAYS:g}-{WEEK_MAX_DAYS:g} days after "
        "the previous one, over about 4 weeks",
        "vocabulary": {
            "all_reviews": scores(preds),
            "after_a_week": scores(week),
            "retention_after_a_week": {
                "by_level": retention(week, lambda p: words.get(p.card, {}).get("level")),
                "by_kind": retention(week, lambda p: p.kind),
                "by_topic": retention(week, lambda p: words.get(p.card, {}).get("topic")),
            },
            "weakest_words": weakest_words(week),
            "not_here": "FSRS against fixed intervals needs parameters fitted to the learner"
            " (later)",
        },
        "grammar_rechecks": recheck_report(rechecks),
        "limits": "N-of-1; correlation only. Study time and topic are possible confounders.",
    }


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - database
    import psycopg

    from app.config import REPO_ROOT, get_settings
    from app.vocabulary.wordlist import shared_wordlist

    parser = argparse.ArgumentParser(prog="python -m app.studies.forget")
    parser.add_argument("--learner", required=True)
    parser.add_argument(
        "--out", type=Path, default=REPO_ROOT / "data" / "private" / "forget-001.json"
    )
    args = parser.parse_args(argv)
    settings = get_settings()
    wordlist = shared_wordlist(settings.vocab_dir / "core-seed.yaml", settings.vocab_imported_dir)
    words = {
        f"{wordlist.slug}/{w.lemma}:{w.pos}": {"level": w.level, "topic": w.topic}
        for w in wordlist.words
    }
    with psycopg.connect(settings.database_url) as conn:
        reviews = [
            Review(f"{lst}/{key}", kind, correct, at)
            for lst, key, kind, correct, at in conn.execute(
                "select list_slug, word_key, item_kind, correct, answered_at from vocab_reviews "
                "where learner_id::text=%s order by answered_at",
                (args.learner,),
            ).fetchall()
        ]
        rechecks = [
            Recheck(node, correct, (answered - evidence).total_seconds() / 86400)
            for node, correct, answered, evidence in conn.execute(
                "select node, correct, answered_at, evidence_at from grammar_rechecks "
                "where learner_id::text=%s and answered_at is not null",
                (args.learner,),
            ).fetchall()
        ]
    out = report(reviews, words, rechecks)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", "utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"written to {args.out} (private: keep it out of git)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
