"""The tester report (specs/speaking/step-5.5.md). Pure; for the owner, never audio or words.

Counts per tester, retention against the phase gate (at least 5 of 10 testers still using it after
2 weeks) with an exact interval, and each consenting tester's own numbers by week: only the answers
that count as evidence (strict mock answers and the first try of a practised question). One person's
numbers are N-of-1; nothing here compares testers.
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from statistics import median
from typing import Any
from uuid import UUID

from app.evalkit.stats import rate

RETENTION_DAYS = 14


@dataclass(frozen=True)
class Enrolled:
    learner: UUID
    label: str
    revoked: bool
    research: bool  # accepted the optional notice for the report's numbers


@dataclass(frozen=True)
class Sitting:
    learner: UUID
    day: date  # the Vietnam day it started
    mode: str  # 'exam' or 'guided'


@dataclass(frozen=True)
class Number:
    learner: UUID
    week: str  # ISO week of the answer, e.g. "2026-W48"
    speech_rate: float | None
    pauses_per_minute: float | None


def iso_week(day: date) -> str:
    year, week, _ = day.isocalendar()
    return f"{year}-W{week:02d}"


def _median(values: list[float]) -> float | None:
    return None if not values else round(float(median(values)), 1)


def report(
    testers: Sequence[Enrolled],
    sittings: Sequence[Sitting],
    numbers: Sequence[Number],
    today: date,
) -> dict[str, Any]:
    by_learner: dict[UUID, list[Sitting]] = defaultdict(list)
    for s in sittings:
        by_learner[s.learner].append(s)
    weeks: dict[UUID, dict[str, list[Number]]] = defaultdict(lambda: defaultdict(list))
    for n in numbers:
        weeks[n.learner][n.week].append(n)
    rows: list[dict[str, Any]] = []
    eligible = retained = 0
    for t in sorted(testers, key=lambda t: t.label.lower()):
        mine = by_learner.get(t.learner, [])
        days = sorted({s.day for s in mine})
        first = days[0] if days else None
        row: dict[str, Any] = {
            "label": t.label,
            "switched_off": t.revoked,
            "first_day": None if first is None else first.isoformat(),
            "last_day": None if not days else days[-1].isoformat(),
            "days_active": len(days),
            "mock_tests": sum(1 for s in mine if s.mode == "exam"),
            "practice_tries": sum(1 for s in mine if s.mode == "guided"),
            "research_notice": t.research,
        }
        if first is not None and (today - first).days >= RETENTION_DAYS:
            eligible += 1
            if any((d - first).days >= RETENTION_DAYS for d in days):
                retained += 1
        if t.research:  # a tester's numbers only under the notice they accepted
            row["weekly_numbers"] = [
                {
                    "week": week,
                    "answers": len(items),
                    "median_speech_rate": _median(
                        [n.speech_rate for n in items if n.speech_rate is not None]
                    ),
                    "median_pauses_per_minute": _median(
                        [n.pauses_per_minute for n in items if n.pauses_per_minute is not None]
                    ),
                }
                for week, items in sorted(weeks[t.learner].items())
            ]
        rows.append(row)
    share = rate(retained, eligible)
    return {
        "testers": rows,
        "retention": {
            "rule": f"active on or after day {RETENTION_DAYS} from the first day",
            "gate": "at least 5 of 10 testers still using it after 2 weeks",
            "eligible": eligible,
            "retained": retained,
            "share": None if eligible == 0 else round(retained / eligible, 3),
            "low": None if share.low is None else round(share.low, 3),
            "high": None if share.high is None else round(share.high, 3),
            "note": (
                "Fewer than 10 testers: the interval is wide."
                if eligible < 10
                else "Exact 95% interval."
            ),
        },
        "note": (
            "For the owner. Counts only, plus the numbers of testers who accepted the research "
            "notice. No audio, no transcript, nothing a tester said. N-of-1 per tester."
        ),
    }
