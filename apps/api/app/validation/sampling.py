"""Stratified samples for reviewers (specs/validation/step-v2.md). Pure.

Every item the checker disagreed on (up to the size), the rest filled at random from the items it
agreed on, then shuffled so the strata are not visible in the serving order. The population counts
are kept so a later report can weight each stratum by its share of the whole.
"""

import random
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Sample:
    item_ids: list[str]
    strata: dict[str, str]
    population: dict[str, int]


def stratified(disagreed: Sequence[str], agreed: Sequence[str], size: int, seed: int) -> Sample:
    if size < 1:
        raise ValueError("a sample needs at least one item")
    rng = random.Random(seed)
    hard = sorted(set(disagreed))
    easy = sorted(set(agreed) - set(hard))
    if len(hard) > size:
        hard = rng.sample(hard, size)
    easy = rng.sample(easy, min(len(easy), size - len(hard)))
    strata = {i: "disagreed" for i in hard} | {i: "agreed" for i in easy}
    order = sorted(strata)
    rng.shuffle(order)
    return Sample(
        order,
        strata,
        {"disagreed": len(set(disagreed)), "agreed": len(set(agreed) - set(disagreed))},
    )


def everything(ids: Sequence[str], seed: int) -> Sample:
    """All items (e.g. every text in the bank), in a shuffled order."""
    order = sorted(set(ids))
    random.Random(seed).shuffle(order)
    return Sample(order, {i: "all" for i in order}, {"all": len(order)})
