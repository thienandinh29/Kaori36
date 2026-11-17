"""Thresholds per sound group from the owner's labels (specs/pronunciation/step-3.3.md, 3.3b).

Pure except `main`. Recordings, not phones, are split into a tune half and a check half, so no
sentence is in both. A sound is flagged when its GOP is below the threshold. The threshold is
chosen on the tune half; the false-alarm share (flagged but labelled right, over flagged) is
measured on the check half with a Wilson interval. Only a `pass` group may get marks (step 3.4).
"""

import argparse
import hashlib
import json
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

MAX_FALSE_SHARE = 0.10
MIN_FLAGGED = 10
Half = Literal["tune", "check"]


@dataclass(frozen=True)
class Labelled:
    recording: str
    group: str
    gop: float
    wrong: bool


def half(recording: str) -> Half:
    """A fixed half per recording, from a hash of its id."""
    return "tune" if hashlib.sha256(recording.encode()).digest()[0] % 2 == 0 else "check"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def counts(items: Sequence[Labelled], threshold: float) -> tuple[int, int, int, int]:
    """(flagged, false alarms, wrong caught, wrong total)."""
    flagged = [x for x in items if x.gop < threshold]
    false = sum(not x.wrong for x in flagged)
    caught = sum(x.wrong for x in flagged)
    return len(flagged), false, caught, sum(x.wrong for x in items)


def choose(items: Sequence[Labelled], max_false: float = MAX_FALSE_SHARE) -> float | None:
    """The threshold catching the most wrong sounds with a false-alarm share at most `max_false`.

    Candidates sit just above each observed GOP, so "below the threshold" includes that sound.
    Ties in catches go to the lower threshold (fewer flags). None when nothing qualifies.
    """
    best: tuple[int, float] | None = None
    for gop in sorted({x.gop for x in items}):
        threshold = round(gop + 1e-3, 3)
        flagged, false, caught, _ = counts(items, threshold)
        if caught == 0 or false / flagged > max_false:
            continue
        if best is None or caught > best[0]:
            best = (caught, threshold)
    return None if best is None else best[1]


def report_group(items: Sequence[Labelled]) -> dict[str, Any]:
    tune = [x for x in items if half(x.recording) == "tune"]
    check = [x for x in items if half(x.recording) == "check"]
    out: dict[str, Any] = {
        "tune": {"n": len(tune), "wrong": sum(x.wrong for x in tune)},
        "check": {"n": len(check), "wrong": sum(x.wrong for x in check)},
        "threshold": choose(tune),
    }
    if out["threshold"] is None:
        out["verdict"] = "too_few"
        return out
    flagged, false, caught, wrong = counts(check, out["threshold"])
    right = len(check) - wrong
    share = false / flagged if flagged else None
    out["check"] |= {
        "flagged": flagged,
        "false_alarms": false,
        "false_alarm_share": None if share is None else round(share, 3),
        "false_alarm_share_95": [round(v, 3) for v in wilson(false, flagged)],
        "recall": round(caught / wrong, 3) if wrong else None,
        "false_positive_rate": round(false / right, 3) if right else None,
    }
    if flagged < MIN_FLAGGED or share is None:
        out["verdict"] = "too_few"
    else:
        out["verdict"] = "pass" if share <= MAX_FALSE_SHARE else "fail"
    return out


def report(items: Iterable[Labelled]) -> dict[str, Any]:
    groups: dict[str, list[Labelled]] = {}
    for x in items:
        groups.setdefault(x.group, []).append(x)
    return {
        "rule": (
            f"flag when GOP < threshold; threshold chosen on the tune half for the most catches "
            f"with false-alarm share <= {MAX_FALSE_SHARE}; pass needs share <= {MAX_FALSE_SHARE} "
            f"and >= {MIN_FLAGGED} flags on the check half"
        ),
        "groups": {g: report_group(v) for g, v in sorted(groups.items())},
    }


def from_rows(rows: Iterable[tuple[str, Any, int, str]], groups: dict[str, str]) -> list[Labelled]:
    """(recording id, analysis, target index, label) rows to labelled sounds; unsure left out."""
    out = []
    for recording, analysis, target, label in rows:
        if label == "unsure":
            continue
        t = analysis["targets"][target]
        out.append(Labelled(str(recording), groups[t["sound"]], float(t["gop"]), label == "wrong"))
    return out


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - needs the database
    import psycopg

    from app.config import get_settings
    from app.services.recordings import load_prompts

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    settings = get_settings()
    sounds, _ = load_prompts(settings.pronunciation_dir)
    with psycopg.connect(settings.database_url) as conn:
        rows = conn.execute(
            "select r.id::text, r.analysis, l.target, l.label from speech_labels l "
            "join speech_recordings r on r.id = l.recording_id where r.status = 'analysed'"
        ).fetchall()
    result = report(from_rows(rows, {s.id: s.group for s in sounds.values()}))
    result["recordings"] = len({r[0] for r in rows})
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["groups"], indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
