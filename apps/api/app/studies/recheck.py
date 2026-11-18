"""FORGET-001: which grammar nodes to re-check, with which item (specs/forget-001/spec.md). Pure.

A node known at p >= 0.9 whose last evidence is at least MIN_DAYS old, and which had no re-check in
the last GAP_DAYS, is due; the oldest evidence goes first; at most PER_WEEK re-checks are created in
any rolling 7 days. The item is one the learner has never answered for that node, else the least
recently answered.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.engine.milestones import ASSUMED_KNOWN

MIN_DAYS = 5
GAP_DAYS = 28
PER_WEEK = 3


@dataclass(frozen=True)
class Known:
    node: str
    p_known: float
    evidence_at: datetime


def due(
    known: Iterable[Known],
    last_recheck: Mapping[str, datetime],
    created_this_week: int,
    now: datetime,
) -> list[Known]:
    """The nodes to re-check now, oldest evidence first, within the weekly cap."""
    room = max(0, PER_WEEK - created_this_week)
    candidates = [
        k
        for k in known
        if k.p_known >= ASSUMED_KNOWN
        and now - k.evidence_at >= timedelta(days=MIN_DAYS)
        and (k.node not in last_recheck or now - last_recheck[k.node] >= timedelta(days=GAP_DAYS))
    ]
    candidates.sort(key=lambda k: (k.evidence_at, k.node))
    return candidates[:room]


def pick_item(items: Sequence[str], last_answered: Mapping[str, datetime]) -> str | None:
    """Never-answered items first (in bank order), then the least recently answered."""
    if not items:
        return None
    fresh = [i for i in items if i not in last_answered]
    if fresh:
        return fresh[0]
    return min(items, key=lambda i: last_answered[i])
