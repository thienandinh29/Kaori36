"""Marks on target sounds and their observation model (specs/pronunciation/step-3.4.md).

Pure. A sound is marked only when its group passed the gate (an applied threshold), its GOP is
below that threshold, and the recogniser heard a competing phone. Anything else is unmarked, which
means "not sure", never "right".
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Applied:
    """One sound group's threshold, applied by the owner after the 3.3b report."""

    threshold: float
    slip: float | None  # P(marked | said right); None: no evidence from this group
    guess: float | None  # P(unmarked | said wrong)
    labelled: int


def observation(group: Mapping[str, Any]) -> tuple[float, float] | None:
    """(slip, guess) from a 3.3b group report's check half; None when they say nothing.

    slip is the false-positive rate on sounds labelled right; guess is the miss rate. With
    slip + guess >= 1 a mark would carry no information about the learner (BKT degeneracy).
    """
    check = group.get("check", {})
    fpr, recall = check.get("false_positive_rate"), check.get("recall")
    if fpr is None or recall is None:
        return None
    slip, guess = round(float(fpr), 3), round(1 - float(recall), 3)
    return None if slip + guess >= 1 else (slip, guess)


def applicable(report: Mapping[str, Any], today: str) -> dict[str, Any]:
    """The `pass` groups of a 3.3b report, in the applied-thresholds file format."""
    groups = {}
    for name, g in report["groups"].items():
        if g.get("verdict") != "pass":
            continue
        obs = observation(g)
        groups[name] = {
            "threshold": g["threshold"],
            "slip": obs[0] if obs else None,
            "guess": obs[1] if obs else None,
            "labelled": g["tune"]["n"] + g["check"]["n"],
        }
    return {"applied": today, "groups": groups}


def load_applied(path: Path) -> dict[str, Applied]:
    """Applied thresholds by sound group; none (so no marks) when the file does not exist."""
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {name: Applied(**g) for name, g in raw["groups"].items()}


def observations(
    targets: Sequence[Mapping[str, Any]],
    marked: Sequence[int],
    group_of: Mapping[str, str],
    applied: Mapping[str, Applied],
) -> list[tuple[str, int, bool]]:
    """One BKT observation per applied group with parameters: (group, target index, correct).

    The group's first target in the sentence is the observation (unmarked = correct). One per
    recording, so a long sentence does not count many times; the first, not the worst, so the
    measured slip and guess (per sound) still describe it.
    """
    out: list[tuple[str, int, bool]] = []
    seen: set[str] = set()
    for i, t in enumerate(targets):
        group = group_of.get(t["sound"], "")
        a = applied.get(group)
        if a is None or a.slip is None or a.guess is None or group in seen:
            continue
        seen.add(group)
        out.append((group, i, i not in marked))
    return out


def marks(
    targets: Sequence[Mapping[str, Any]],
    group_of: Mapping[str, str],
    applied: Mapping[str, Applied],
) -> list[int]:
    """Indexes of the target sounds marked as probably mispronounced."""
    out = []
    for i, t in enumerate(targets):
        a = applied.get(group_of.get(t["sound"], ""))
        if a is not None and t["gop"] < a.threshold and t.get("competitor"):
            out.append(i)
    return out
