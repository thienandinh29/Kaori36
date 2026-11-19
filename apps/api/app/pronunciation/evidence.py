"""Pronunciation evidence: three outcomes and two error layers (specs/pronunciation/step-3.6a.md).

Pure. A target sound comes out `wrong`, `right` or `inconclusive`. BKT sees only the conclusive
ones, with slip and guess that combine the learner's own slips and guesses with the detector's
measured errors, never the detector's errors alone.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

Outcome = Literal["right", "wrong", "inconclusive"]

# The learner's own slip and guess for a sound: assumptions until fitted (engine/bkt_fit.py) on
# enough recordings. A learner who knows /θ/ still says /t/ now and then (slip); one who does not
# sometimes gets it right (guess, higher for sounds that are easy to hit by chance).
LEARNER_SLIP = 0.10
LEARNER_GUESS = 0.25


@dataclass(frozen=True)
class Rates:
    """The detector's measured rates on the check half, by what the sound really was."""

    right_if_right: float  # P(outcome right | said right)
    wrong_if_right: float  # P(outcome wrong | said right): false alarms
    right_if_wrong: float  # P(outcome right | said wrong): accepted although wrong
    wrong_if_wrong: float  # P(outcome wrong | said wrong): caught

    @classmethod
    def from_counts(cls, said_right: Mapping[str, int], said_wrong: Mapping[str, int]) -> "Rates":
        def share(c: Mapping[str, int], k: str) -> float:
            n = sum(c.values())
            return round(c.get(k, 0) / n, 4) if n else 0.0

        return cls(
            share(said_right, "right"), share(said_right, "wrong"),
            share(said_wrong, "right"), share(said_wrong, "wrong"),
        )  # fmt: skip


def outcome(target: Mapping[str, Any], threshold: float, accept: float) -> Outcome:
    """A target sound's outcome: wrong needs a low GOP and a heard competitor; right a high GOP."""
    gop = float(target["gop"])
    if gop < threshold and target.get("competitor"):
        return "wrong"
    if gop >= accept:
        return "right"
    return "inconclusive"


def effective(
    rates: Rates, slip: float = LEARNER_SLIP, guess: float = LEARNER_GUESS
) -> tuple[float, float] | None:
    """(slip, guess) for BKT on a conclusive outcome; None when the outcome says nothing.

    P(o | knows) = (1-s)·P(o | said right) + s·P(o | said wrong), and
    P(o | not known) = g·P(o | said right) + (1-g)·P(o | said wrong); inconclusive outcomes are
    left out, so each is renormalised over {right, wrong}.
    """
    wrong_k = (1 - slip) * rates.wrong_if_right + slip * rates.wrong_if_wrong
    right_k = (1 - slip) * rates.right_if_right + slip * rates.right_if_wrong
    right_n = guess * rates.right_if_right + (1 - guess) * rates.right_if_wrong
    wrong_n = guess * rates.wrong_if_right + (1 - guess) * rates.wrong_if_wrong
    if wrong_k + right_k <= 0 or right_n + wrong_n <= 0:
        return None
    s_eff = wrong_k / (wrong_k + right_k)
    g_eff = right_n / (right_n + wrong_n)
    if s_eff + g_eff >= 1:
        return None  # a right outcome is no likelier when the learner knows the sound
    return round(s_eff, 4), round(g_eff, 4)
