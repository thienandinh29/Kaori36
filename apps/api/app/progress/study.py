"""The progress study, N-of-1 (specs/validation/step-v4.md). Pure.

Independent tests (a baseline, then every 28 days) measure progress; NodeTrail's own estimates are
snapshotted next to each result and only compared, never taken as proof. One learner and a few
sittings show a trajectory, not a cause: the report gives changes, intervals where the test has
them, and whether NodeTrail's estimate moved the same way, and nothing more.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Literal

from app.evalkit.stats import rate
from app.validation.gate import basis

INTERVAL_DAYS = 28
Skill = Literal["listening", "reading", "writing", "speaking", "overall"]
MarkedBy = Literal["answer_key", "trained_rater", "self"]
SKILLS: tuple[str, ...] = ("listening", "reading", "writing", "speaking", "overall")
# The rater's criteria per skill (step V4 addition, 27 Nov 2026): whole bands 0-9. TR stands for
# Task Achievement on Writing Task 1. One weak criterion caps the skill's band, so the report names
# the lowest; the skill's band itself is always the rater's, never computed here.
CRITERIA: dict[str, tuple[str, ...]] = {
    "writing": ("tr", "cc", "lr", "gra"),
    "speaking": ("fc", "lr", "gra", "p"),
}


@dataclass(frozen=True)
class Result:
    taken_on: date
    skill: str
    paper: str
    timed: bool
    marked_by: str
    baseline: bool = False
    raw_k: int | None = None
    raw_n: int | None = None
    band: float | None = None
    snapshot: Mapping[str, Any] = field(default_factory=dict)
    criteria: Mapping[str, int] | None = None


def parse_criteria(text: str) -> dict[str, int]:
    """'fc=7,lr=7,gra=6,p=7' as a mapping; malformed text is refused."""
    out: dict[str, int] = {}
    for part in text.split(","):
        key, sep, value = part.strip().partition("=")
        if not sep or not key or not value.strip().isdigit():
            raise ValueError(f"criteria look like fc=7,lr=7,gra=6,p=7, not {text!r}")
        if key.strip().lower() in out:
            raise ValueError(f"criterion {key.strip()!r} given twice")
        out[key.strip().lower()] = int(value)
    return out


def check_criteria(skill: str, marked_by: str, criteria: Mapping[str, int]) -> dict[str, int]:
    """All four of the skill's criteria as whole bands 0-9, from a rater or the learner."""
    names = CRITERIA.get(skill)
    if names is None:
        raise ValueError("criterion bands are for writing or speaking only")
    if marked_by not in ("trained_rater", "self"):
        raise ValueError("criterion bands come from a rater (trained_rater) or yourself (self)")
    if set(criteria) != set(names):
        raise ValueError(f"{skill} criteria are exactly {', '.join(names)}")
    if any(not 0 <= v <= 9 for v in criteria.values()):
        raise ValueError("each criterion is a whole band from 0 to 9")
    return {k: int(criteria[k]) for k in names}


def lowest(criteria: Mapping[str, int]) -> list[str]:
    """The weakest criteria (all of them on a tie)."""
    low = min(criteria.values())
    return [k for k, v in criteria.items() if v == low]


def truth_of(marked_by: str) -> tuple[Literal["gold", "bronze"], bool]:
    """(truth, declared): the paper's key or a trained rater is Gold, as entered; self is Bronze."""
    if marked_by in ("answer_key", "trained_rater"):
        return "gold", True
    if marked_by == "self":
        return "bronze", False
    raise ValueError(f"marked_by is one of answer_key, trained_rater, self, not {marked_by!r}")


def schedule(baseline: date | None, last: date | None, today: date) -> dict[str, Any]:
    """The next test is due INTERVAL_DAYS after the last sitting (the baseline comes first)."""
    if baseline is None:
        return {"baseline": None, "next_due": today.isoformat(), "overdue_days": 0,
                "note": "Take the baseline first, before more learning."}  # fmt: skip
    due = (last or baseline) + timedelta(days=INTERVAL_DAYS)
    return {
        "baseline": baseline.isoformat(),
        "last": (last or baseline).isoformat(),
        "next_due": due.isoformat(),
        "overdue_days": max(0, (today - due).days),
    }


def _estimate(snapshot: Mapping[str, Any]) -> float | None:
    """One number for NodeTrail's own estimate: mean p_known over the English grammar course."""
    subject = snapshot.get("subjects", {}).get("english-ielts")
    value = None if subject is None else subject.get("mean_p_known")
    return None if value is None else float(value)


def _raw(r: Result) -> dict[str, Any] | None:
    if r.raw_k is None or r.raw_n is None:
        return None
    x = rate(r.raw_k, r.raw_n)
    return {"k": r.raw_k, "n": r.raw_n, "share": round(r.raw_k / r.raw_n, 3),
            "low": None if x.low is None else round(x.low, 3),
            "high": None if x.high is None else round(x.high, 3)}  # fmt: skip


def _score(r: Result) -> float | None:
    """The band if given, else the raw share: the number whose change is reported."""
    if r.band is not None:
        return r.band
    return None if r.raw_k is None or r.raw_n is None else r.raw_k / r.raw_n


def _sign(x: float | None) -> int | None:
    if x is None:
        return None
    return 0 if abs(x) < 1e-9 else (1 if x > 0 else -1)


def report(results: Sequence[Result]) -> dict[str, Any]:
    by_skill: dict[str, list[Result]] = {}
    for r in sorted(results, key=lambda r: (r.skill, r.taken_on)):
        by_skill.setdefault(r.skill, []).append(r)
    skills: dict[str, Any] = {}
    for skill, rows in by_skill.items():
        base = next((r for r in rows if r.baseline), rows[0])
        sittings = []
        previous: Result | None = None
        for r in rows:
            truth, declared = truth_of(r.marked_by)
            entry: dict[str, Any] = {
                "taken_on": r.taken_on.isoformat(),
                "paper": r.paper,
                "timed": r.timed,
                "baseline": r.baseline,
                "band": r.band,
                "raw": _raw(r),
                "basis": basis(truth, 1, 1, declared=declared),
                "nodetrail_estimate": _estimate(r.snapshot),
            }
            if r.criteria:
                entry["criteria"] = dict(r.criteria)
                entry["lowest"] = lowest(r.criteria)
                before = next(
                    (x.criteria for x in reversed(rows[: rows.index(r)]) if x.criteria), None
                )
                if before:
                    entry["criteria_change"] = {
                        k: v - before[k] for k, v in r.criteria.items() if k in before
                    }
            if r is not base:
                entry["change_from_baseline"] = _delta(_score(base), _score(r))
            if previous is not None:
                test_change = _delta(_score(previous), _score(r))
                own_change = _delta(_estimate(previous.snapshot), _estimate(r.snapshot))
                entry["change_from_previous"] = test_change
                entry["nodetrail_change"] = own_change
                a, b = _sign(test_change), _sign(own_change)
                if a is not None and b is not None and a * b < 0:
                    entry["disagreement"] = (
                        "NodeTrail's estimate moved the other way from the independent test: "
                        "trust the test, and look for why."
                    )
                if not r.timed:
                    entry["caution"] = "not under exam conditions"
            sittings.append(entry)
            previous = r
        skills[skill] = {"sittings": sittings}
    return {
        "skills": skills,
        "note": (
            "N-of-1: one learner, few sittings. Changes are descriptive; practice with the same "
            "kind of paper, mood and test difficulty move scores too. A change in NodeTrail's "
            "estimate is never evidence of progress on its own. Criterion bands are the rater's; "
            "NodeTrail never computes a band from them."
        ),
    }


def _delta(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else round(b - a, 3)
