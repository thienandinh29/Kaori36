"""Vocabulary band nodes from FSRS cards (specs/two-layer-map/spec.md, layer 1). Pure.

Vocabulary has no prerequisite edges, so it has no BKT node per word. A band node (vocab-a1 ...
vocab-c1, and vocab-nawl for the academic list) is the share of that band's words whose card is
stable: FSRS stability of at least STABLE_DAYS. The share is over every word in the band, seen or
not, so it measures the band, not only the words practised; how many words were reviewed is
returned as the evidence it rests on.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

STABLE_DAYS = 21.0


@dataclass(frozen=True)
class Band:
    node: str
    words: int  # in the band
    reviewed: int  # with a card
    stable: int  # card stability >= STABLE_DAYS

    @property
    def p(self) -> float:
        return self.stable / self.words if self.words else 0.0


def band_of(level: str, origin: str) -> str:
    """The band node a word belongs to: NAWL words form their own academic band."""
    # The NAWL, TSL and BSL have their own bands (step-tsl-bsl.md), so they never dilute B2 and C1.
    return f"vocab-{origin}" if origin in ("nawl", "tsl", "bsl") else f"vocab-{level.lower()}"


def bands(words: Iterable[tuple[str, str, str]], stability: Mapping[str, float]) -> dict[str, Band]:
    """words: (word key, CEFR level, origin); stability: word key -> FSRS stability in days."""
    totals: dict[str, list[int]] = {}
    for key, level, origin in words:
        t = totals.setdefault(band_of(level, origin), [0, 0, 0])
        t[0] += 1
        if key in stability:
            t[1] += 1
            t[2] += stability[key] >= STABLE_DAYS
    return {node: Band(node, *t) for node, t in sorted(totals.items())}
