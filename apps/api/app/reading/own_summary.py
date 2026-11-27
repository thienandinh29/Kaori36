"""The summary across a learner's pasted Reading tests (step 4.3d part 2): pure, no database.

Per question type: answers, wrong, the share right with an exact 95% interval, and the most
frequent trap. The pacing line: whether wrong answers pile up late in a test (passage 3, or the
last third of a passage's questions) and the learner's own marks say time ran out.

The thresholds (5 answers per type, 3 tests, 20 points, half marked) are assumptions, labelled so on
the page. The marks are self-report (Bronze).
"""

from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

from app.evalkit.stats import rate

Mark = Literal["guessed", "no_time"]

MIN_PER_KIND = 5  # fewer answers of a type is "chưa đủ dữ liệu"
MIN_TESTS_FOR_PACING = 3
PACING_GAP = 0.20  # late errors at least 20 points above the rest
PACING_MARKED_SHARE = 0.5  # at least half of the late wrong answers blank or marked


@dataclass(frozen=True)
class Answer:
    """One row of `reading_own_answers`: a marked question of one pasted test."""

    fingerprint: str
    number: int
    kind: str
    correct: bool
    blank: bool
    trap: str | None
    mark: Mark | None
    position: int | None  # the passage's place in the test (1-3), when the learner gave it


def late_numbers(numbers: Sequence[int]) -> frozenset[int]:
    """The last third of a passage's marked questions, by number (13 questions: the last 4)."""
    ordered = sorted(set(numbers))
    third = len(ordered) // 3
    return frozenset(ordered[len(ordered) - third :]) if third else frozenset()


def _share(k: int, n: int) -> dict[str, Any]:
    r = rate(k, n)
    return {"k": r.k, "n": r.n, "low": r.low, "high": r.high}


def by_kind(answers: Sequence[Answer]) -> list[dict[str, Any]]:
    """Per question type: right/answers with an interval, and the top trap among wrong answers.

    A guessed answer counts in the score but not in the trap counts (a guess says little about
    which trap tempted the learner).
    """
    groups: dict[str, list[Answer]] = defaultdict(list)
    for a in answers:
        groups[a.kind].append(a)
    out = []
    for kind in ("tfng", "ynng", "mcq", "completion"):
        rows = groups.get(kind, [])
        if not rows:
            continue
        wrong = [a for a in rows if not a.correct]
        traps = Counter(a.trap for a in wrong if a.trap and a.mark != "guessed")
        top = traps.most_common(1)
        counted = sum(traps.values())
        out.append({
            "kind": kind,
            "answers": len(rows),
            "wrong": len(wrong),
            "enough": len(rows) >= MIN_PER_KIND,
            "right": _share(len(rows) - len(wrong), len(rows)),
            "top_trap": (
                {"trap": top[0][0], "count": top[0][1], "of": counted} if top else None
            ),
        })  # fmt: skip
    return out


def pacing(answers: Sequence[Answer]) -> dict[str, Any]:
    """Late errors against the rest, over the learner's pasted tests.

    `status`: `not_enough` (fewer than 3 tests, or no passage 3 among them), `maybe_time` (late
    errors at least 20 points higher and at least half of them blank or marked by the learner), or
    `counts_only`. Passage 3 is also the hardest passage, so late errors mix difficulty and time;
    only the learner's marks separate them, and the line says "có thể", never "do".
    """
    tests: dict[str, list[Answer]] = defaultdict(list)
    for a in answers:
        tests[a.fingerprint].append(a)
    has_third = any(a.position == 3 for a in answers)
    late: list[Answer] = []
    rest: list[Answer] = []
    for rows in tests.values():
        last = late_numbers([a.number for a in rows])
        for a in rows:
            (late if a.position == 3 or a.number in last else rest).append(a)
    late_wrong = [a for a in late if not a.correct]
    marked = sum(1 for a in late_wrong if a.blank or a.mark is not None)
    rest_wrong = sum(1 for a in rest if not a.correct)
    result: dict[str, Any] = {
        "tests": len(tests),
        "late": {"wrong": len(late_wrong), "n": len(late)},
        "rest": {"wrong": rest_wrong, "n": len(rest)},
        "late_wrong_marked": marked,
    }
    if len(tests) < MIN_TESTS_FOR_PACING or not has_third or not late or not rest:
        return result | {"status": "not_enough"}
    gap = len(late_wrong) / len(late) - rest_wrong / len(rest)
    enough_marked = bool(late_wrong) and marked >= PACING_MARKED_SHARE * len(late_wrong)
    status = "maybe_time" if gap >= PACING_GAP and enough_marked else "counts_only"
    return result | {"status": status}


def summary(answers: Sequence[Answer]) -> dict[str, Any]:
    return {
        "tests": len({a.fingerprint for a in answers}),
        "answers": len(answers),
        "by_kind": by_kind(answers),
        "pacing": pacing(answers),
        "thresholds": {
            "min_per_kind": MIN_PER_KIND,
            "min_tests": MIN_TESTS_FOR_PACING,
            "gap": PACING_GAP,
            "marked_share": PACING_MARKED_SHARE,
        },
    }
