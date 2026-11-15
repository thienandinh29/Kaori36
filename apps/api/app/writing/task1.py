"""Checks for a Task 1 essay against the chart's own data (specs/writing/step-2.5.md). Pure.

Flags, not verdicts: the code does not understand sentences. It looks up the numbers the essay
writes among what the chart can support, lists the key features the essay never mentions, and
notes whether an overview marker is present. Direction of change is left to the model.
"""

import re
from dataclasses import asdict, dataclass
from itertools import combinations
from typing import Any

from app.curriculum.facts import chart_facts
from app.curriculum.figures import ChartFigure

NUMBER = re.compile(r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)(\s*%)?")
SMALL_BARE_MAX = 10  # a bare "3" is usually a count of things, not data: not flagged
TOLERANCE = 0.051  # a number written to one decimal place
OVERVIEW_MARKERS = (
    "overall", "in general", "generally", "as a whole", "it is clear", "it can be seen that",
    "to summarise", "to summarize", "in summary", "the most striking",
)  # fmt: skip
FEATURE_KINDS = ("max", "min", "overall_change", "share")


@dataclass(frozen=True)
class NumberCheck:
    text: str
    supported: bool


@dataclass(frozen=True)
class FeatureCheck:
    kind: str
    series: str | None
    category: str | None
    text: str
    covered: bool


@dataclass(frozen=True)
class Task1Check:
    numbers: tuple[NumberCheck, ...]
    features: tuple[FeatureCheck, ...]
    overview: bool

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def numbers_in(text: str) -> list[tuple[str, float, bool]]:
    """(as written, value, followed by %) for each number; commas as thousands separators."""
    out: list[tuple[str, float, bool]] = []
    for m in NUMBER.finditer(text):
        raw = m.group(1).rstrip(",")
        try:
            out.append((raw + (m.group(2) or "").strip(), float(raw.replace(",", "")),
                        bool(m.group(2))))  # fmt: skip
        except ValueError:
            continue
    return out


def supported_values(chart: ChartFigure) -> set[float]:
    """Every number the chart can honestly support."""
    allowed: set[float] = set()
    for s in chart.series:
        allowed.update(s.values)
        allowed.update(abs(a - b) for a, b in combinations(s.values, 2))
        allowed.add(sum(s.values))
    for i in range(len(chart.categories)):
        allowed.add(sum(s.values[i] for s in chart.series))
    for cat in chart.categories:
        allowed.update(float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*(?:\.\d+)?", cat))
    if chart.chart_type == "pie":
        values = chart.series[0].values
        total = sum(values)
        if total:
            allowed.update(100 * v / total for v in values)
    return allowed


def _near(x: float, allowed: set[float]) -> bool:
    return any(abs(a - x) < TOLERANCE or (x == int(x) and abs(a - x) <= 0.5) for a in allowed)


def check_numbers(essay: str, chart: ChartFigure) -> list[NumberCheck]:
    allowed = supported_values(chart)
    checks = []
    for text, value, percent in numbers_in(essay):
        if not percent and value <= SMALL_BARE_MAX and value == int(value):
            continue
        checks.append(NumberCheck(text, _near(value, allowed)))
    return checks


def _stem(name: str) -> str:
    return name.lower().rstrip("s")


HIGH_WORDS = (
    "highest",
    "peak",
    "most",
    "largest",
    "greatest",
    "reach",
    "top",
    "biggest",
    "maximum",
)
LOW_WORDS = ("lowest", "least", "smallest", "bottom", "minimum", "fewest")
CHANGE_WORDS = (
    "rise", "rose", "grow", "grew", "increase", "fall", "fell", "decrease", "decline", "drop",
    "stable", "stay", "remain", "climb",
)  # fmt: skip


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


WORD_WINDOW = 70  # characters after the series name in which an extreme or change word counts


def _covers(sentence: str, name: str, values: list[float], words: tuple[str, ...]) -> bool:
    """The sentence names the series and gives a value of it, or a fitting word right after it."""
    low = sentence.lower()
    at = low.find(_stem(name))
    if at < 0:
        return False
    written = [v for _, v, _ in numbers_in(sentence)]
    if any(abs(v - w) < TOLERANCE for v in values for w in written):
        return True
    return any(word in low[at : at + WORD_WINDOW] for word in words)


def check_features(essay: str, chart: ChartFigure) -> list[FeatureCheck]:
    sentences = _sentences(essay)
    series = {s.name: s.values for s in chart.series}
    out: list[FeatureCheck] = []
    for f in chart_facts(chart):
        if f.kind not in FEATURE_KINDS:
            continue
        if f.kind == "share":  # a pie: the category is the feature; only the largest matters
            if any(o.kind == "share" for o in out):
                continue
            covered = f.category is not None and _stem(f.category) in essay.lower()
        else:
            assert f.series is not None
            vals = series[f.series]
            words: tuple[str, ...]
            if f.kind == "max":
                values, words = [max(vals)], HIGH_WORDS
            elif f.kind == "min":
                values, words = [min(vals)], LOW_WORDS
            else:  # overall change: where it started and where it ended
                values, words = [vals[0], vals[-1]], CHANGE_WORDS
            covered = any(_covers(x, f.series, values, words) for x in sentences)
        out.append(FeatureCheck(f.kind, f.series, f.category, f.text, covered))
    return out


def has_overview(essay: str) -> bool:
    low = essay.lower()
    return any(m in low for m in OVERVIEW_MARKERS)


def check(essay: str, chart: ChartFigure) -> Task1Check:
    return Task1Check(
        tuple(check_numbers(essay, chart)), tuple(check_features(essay, chart)), has_overview(essay)
    )


def describe(chart: ChartFigure) -> str:
    """The chart as text for the model: its data table, then the exact facts."""
    unit = f" ({chart.unit})" if chart.unit else ""
    lines = [f"{chart.title}{unit}", "Categories: " + ", ".join(chart.categories)]
    lines += [f"{s.name}: " + ", ".join(f"{v:g}" for v in s.values) for s in chart.series]
    lines += ["Key facts:", *[f"- {f.text}" for f in chart_facts(chart)]]
    return "\n".join(lines)
