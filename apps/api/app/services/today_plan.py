"""Today's plan: done marks, minutes and the week's study days (specs/two-layer-map/step-m5.md).

Pure functions. "Done" means practised today, never mastered: nothing here touches mastery. The
thresholds and minutes are assumptions, not measurements. No streak: the week is a calendar of
days with any saved answer, and nothing counts days in a row.
"""

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from app.services.vocabulary import DEFAULT_LIMIT, VIETNAM

VOCAB_BAND_ANSWERS = 10
GRAMMAR_ANSWERS = 5
COMPETENCY_ANSWERS = 3  # the engine's MIN_EVIDENCE
SECONDS_PER_REVIEW = 15
SKILL_MINUTES = {"writing": 40, "reading": 20, "listening": 15, "speaking": 15}


@dataclass(frozen=True)
class TodayEvidence:
    """What the learner did since the start of today (Vietnam time)."""

    reviews: Mapping[str, int] = field(default_factory=dict)  # "vocab" / "phrases" -> answers
    bands: Mapping[str, int] = field(default_factory=dict)  # vocabulary band node -> word answers
    grammar: Mapping[str, int] = field(default_factory=dict)  # node -> answers
    recordings: int = 0
    essays: int = 0
    competencies: Mapping[str, int] = field(default_factory=dict)  # Reading/Listening answers


@dataclass(frozen=True)
class Target:
    """What an activity's target is, as the service knows it."""

    kind: str  # "review", "vocab_band", "grammar", "pronunciation", "competency"
    nodes: tuple[str, ...] = ()  # grammar: the node itself, or a milestone's hidden nodes
    skill: str | None = None  # competency: writing, reading, listening, speaking


def is_done(target: Target, slug: str, due_at_plan: int, ev: TodayEvidence) -> bool:
    if target.kind == "review":
        need = max(1, min(due_at_plan, DEFAULT_LIMIT))
        return ev.reviews.get(slug, 0) >= need
    if target.kind == "vocab_band":  # answers on that band's words only
        return ev.bands.get(slug, 0) >= VOCAB_BAND_ANSWERS
    if target.kind == "grammar":
        return sum(ev.grammar.get(n, 0) for n in target.nodes) >= GRAMMAR_ANSWERS
    if target.kind == "pronunciation":
        return ev.recordings >= 1
    if target.kind == "competency":
        if target.skill == "writing":
            return ev.essays >= 1
        return ev.competencies.get(slug, 0) >= COMPETENCY_ANSWERS
    return False


TASK1_MINUTES = 20  # a Task 1 report; other Writing competencies need a Task 2 essay


def estimate_minutes(target: Target, due_at_plan: int, slug: str = "") -> int:
    if target.kind == "review":
        cards = max(1, min(due_at_plan, DEFAULT_LIMIT))
        return max(2, min(10, round(cards * SECONDS_PER_REVIEW / 60)))
    if target.kind in ("vocab_band", "pronunciation"):
        return 5
    if target.kind == "grammar":
        return 10
    if target.skill == "writing" and slug == "writing-task1":
        return TASK1_MINUTES
    return SKILL_MINUTES.get(target.skill or "", 15)


def local_day(at: datetime) -> date:
    return at.astimezone(VIETNAM).date()


def week_start(today: date) -> date:
    return today - timedelta(days=today.weekday())  # Monday


def week_bounds(at: datetime) -> tuple[datetime, datetime]:
    """The current week, Monday 00:00 to next Monday 00:00 in Vietnam, as UTC instants."""
    start = week_start(local_day(at))
    begin = datetime(start.year, start.month, start.day, tzinfo=VIETNAM)
    return begin.astimezone(UTC), (begin + timedelta(days=7)).astimezone(UTC)


@dataclass(frozen=True)
class StudyDay:
    day: date
    answers: int
    is_today: bool
    is_future: bool

    @property
    def studied(self) -> bool:
        return self.answers > 0


def study_week(answered: Iterable[datetime], at: datetime) -> list[StudyDay]:
    """Monday to Sunday of `at`'s week with the answers saved on each day (Vietnam time)."""
    today = local_day(at)
    start = week_start(today)
    counts = Counter(local_day(t) for t in answered)
    days = [start + timedelta(days=i) for i in range(7)]
    return [StudyDay(d, counts.get(d, 0), d == today, d > today) for d in days]
