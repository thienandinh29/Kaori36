"""Marks on target sounds and their evidence (specs/pronunciation/step-3.4.md, step-3.6a.md).

Pure. A sound is marked only when its group passed the gate (applied thresholds), its GOP is below
the mark threshold, and the recogniser heard a competing phone. A sound counts as said right only
at or above the group's higher `accept` threshold; anything between is "not sure" and moves
nothing. The observation model combines the learner's own slips and guesses with the detector's
measured errors (`evidence.effective`).
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.pronunciation.evidence import Outcome, Rates, effective, outcome


@dataclass(frozen=True)
class Applied:
    """One sound group's thresholds and measured rates, applied after a passing 3.3b report."""

    threshold: float  # below it (with a competitor heard): wrong
    accept: float  # at or above it: right; between: inconclusive
    rates: Rates  # the detector's outcomes by truth, on the check half
    labelled: int

    def evidence(self) -> tuple[float, float] | None:
        """(slip, guess) for BKT on a conclusive outcome; None when it says nothing."""
        return effective(self.rates)


def applicable(report: Mapping[str, Any], today: str) -> dict[str, Any]:
    """The `pass` groups of a 3.3b report, in the applied-thresholds file format."""
    groups = {}
    for name, g in report["groups"].items():
        if g.get("verdict") != "pass":
            continue
        by_truth = g["check"]["outcomes"]
        rates = Rates.from_counts(by_truth["said_right"], by_truth["said_wrong"])
        groups[name] = {
            "threshold": g["threshold"],
            "accept": g["accept"],
            "rates": rates.__dict__,
            "labelled": g["tune"]["n"] + g["check"]["n"],
        }
    return {"applied": today, "groups": groups}


def load_applied(path: Path) -> dict[str, Applied]:
    """Applied thresholds by sound group; none (so no marks) when the file does not exist."""
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        name: Applied(g["threshold"], g["accept"], Rates(**g["rates"]), g["labelled"])
        for name, g in raw["groups"].items()
    }


def outcomes(
    targets: Sequence[Mapping[str, Any]],
    group_of: Mapping[str, str],
    applied: Mapping[str, Applied],
) -> list[Outcome | None]:
    """Each target's outcome; None where its group is not applied (nothing is said about it)."""
    out: list[Outcome | None] = []
    for t in targets:
        a = applied.get(group_of.get(t["sound"], ""))
        out.append(None if a is None else outcome(t, a.threshold, a.accept))
    return out


def observations(
    targets: Sequence[Mapping[str, Any]],
    group_of: Mapping[str, str],
    applied: Mapping[str, Applied],
) -> list[tuple[str, int, bool]]:
    """One BKT observation per applied group with evidence: (group, target index, said right).

    The group's first target in the sentence decides, so a long sentence does not count many
    times and the measured rates (per sound) still describe it. When that first one is
    inconclusive the group gets nothing from this recording: picking another target would choose
    the evidence.
    """
    out: list[tuple[str, int, bool]] = []
    seen: set[str] = set()
    for i, (t, o) in enumerate(zip(targets, outcomes(targets, group_of, applied), strict=True)):
        group = group_of.get(t["sound"], "")
        if o is None or group in seen:
            continue
        seen.add(group)
        if o != "inconclusive" and applied[group].evidence() is not None:
            out.append((group, i, o == "right"))
    return out


def marks(
    targets: Sequence[Mapping[str, Any]],
    group_of: Mapping[str, str],
    applied: Mapping[str, Applied],
) -> list[int]:
    """Indexes of the target sounds marked as probably mispronounced."""
    return [i for i, o in enumerate(outcomes(targets, group_of, applied)) if o == "wrong"]
