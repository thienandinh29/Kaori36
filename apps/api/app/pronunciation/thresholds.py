"""Thresholds per sound group from labelled sounds (specs/pronunciation/step-3.3.md, 3.3b).

Truth (specs/validation/step-v3.md): Gold `phone_ok` labels from a trained reviewer when they exist;
otherwise the owner's labels, as Bronze. Only a measured basis (Gold, at least MIN_RECORDINGS
recordings) may be applied to the product; a Bronze report checks the pipeline, nothing more.

Pure except `main`. Recordings, not phones, are split into a tune half and a check half, so no
sentence is in both. A sound is flagged when its GOP is below the threshold. The threshold is
chosen on the tune half; the false-alarm share (flagged but labelled right, over flagged) is
measured on the check half with a Wilson interval. Only a `pass` group may get marks (step 3.4).

Step 3.6a adds a second, higher `accept` threshold: a sound at or above it counts as said right,
one between the two is inconclusive (no evidence). The check half then reports the outcomes by
truth, which give the observation model its rates (`evidence.effective`); a group also needs few
wrongly accepted sounds and at least half of its sounds conclusive.
"""

import argparse
import hashlib
import json
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from app.pronunciation.evidence import is_dropped
from app.validation.gate import Truth, basis, measured

MAX_FALSE_SHARE = 0.10
MIN_FLAGGED = 10
MAX_ACCEPTED_WRONG = 0.10  # of the sounds counted as right, at most this share labelled wrong
MIN_ACCEPTED = 10
MIN_CONCLUSIVE = 0.5  # a detector that is rarely sure is not useful, however rarely wrong
MIN_RECORDINGS = 50  # the plan: 50-100 labelled sentences
Half = Literal["tune", "check"]


@dataclass(frozen=True)
class Labelled:
    recording: str
    group: str
    gop: float
    wrong: bool
    dropped: bool = False  # the product calls it wrong whatever its GOP (step 3.6b)


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
    flagged = [x for x in items if x.gop < threshold or x.dropped]
    false = sum(not x.wrong for x in flagged)
    caught = sum(x.wrong for x in flagged)
    return len(flagged), false, caught, sum(x.wrong for x in items)


def choose(items: Sequence[Labelled], max_false: float = MAX_FALSE_SHARE) -> float | None:
    """The threshold catching the most wrong sounds with a false-alarm share at most `max_false`.

    Candidates sit just above each observed GOP, so "below the threshold" includes that sound.
    Ties in catches go to the lower threshold (fewer flags). None when nothing qualifies.
    Thresholds stay at or below 0: below 0 some frame always prefers another phone, so the
    product's rule (a low GOP and a heard competitor, `marks.marks`) flags exactly these sounds
    and the measured rates describe what is shown.
    """
    best: tuple[int, float] | None = None
    for gop in sorted({x.gop for x in items}):
        threshold = round(gop + 1e-3, 3)
        if threshold > 0:
            break
        flagged, false, caught, _ = counts(items, threshold)
        if caught == 0 or false / flagged > max_false:
            continue
        if best is None or caught > best[0]:
            best = (caught, threshold)
    return None if best is None else best[1]


def choose_accept(
    items: Sequence[Labelled], threshold: float, max_wrong: float = MAX_ACCEPTED_WRONG
) -> float | None:
    """The lowest `accept` (at or above `threshold`) with at most `max_wrong` of accepted sounds
    labelled wrong: as many sounds conclusive as the limit allows. None when nothing qualifies."""
    for gop in sorted({x.gop for x in items if x.gop >= threshold}):
        accepted = [x for x in items if x.gop >= gop and not x.dropped]
        if accepted and sum(x.wrong for x in accepted) / len(accepted) <= max_wrong:
            return round(gop, 3)
    return None


def outcomes(
    items: Sequence[Labelled], threshold: float, accept: float
) -> dict[str, dict[str, int]]:
    """Outcome counts by truth. Thresholds stay at or below 0, where a competitor is always heard,
    so `GOP < threshold` is the product's `wrong` (`evidence.outcome`)."""
    out = {t: {"right": 0, "wrong": 0, "inconclusive": 0} for t in ("said_right", "said_wrong")}
    for x in items:
        o = (
            "wrong"
            if x.gop < threshold or x.dropped
            else "right"
            if x.gop >= accept
            else "inconclusive"
        )
        out["said_wrong" if x.wrong else "said_right"][o] += 1
    return out


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
    out["accept"] = choose_accept(tune, out["threshold"])
    if flagged < MIN_FLAGGED or share is None or out["accept"] is None:
        out["verdict"] = "too_few"
        return out
    by_truth = outcomes(check, out["threshold"], out["accept"])
    accepted = by_truth["said_right"]["right"] + by_truth["said_wrong"]["right"]
    wrongly = by_truth["said_wrong"]["right"]
    conclusive = len(check) - sum(t["inconclusive"] for t in by_truth.values())
    out["check"] |= {
        "outcomes": by_truth,
        "accepted": accepted,
        "accepted_wrong_share": round(wrongly / accepted, 3) if accepted else None,
        "accepted_wrong_share_95": [round(v, 3) for v in wilson(wrongly, accepted)],
        "conclusive_share": round(conclusive / len(check), 3) if check else None,
    }
    if accepted < MIN_ACCEPTED:
        out["verdict"] = "too_few"
    elif (
        share > MAX_FALSE_SHARE
        or wrongly / accepted > MAX_ACCEPTED_WRONG
        or conclusive / len(check) < MIN_CONCLUSIVE
    ):
        out["verdict"] = "fail"
    else:
        out["verdict"] = "pass"
    return out


def report(items: Iterable[Labelled]) -> dict[str, Any]:
    groups: dict[str, list[Labelled]] = {}
    for x in items:
        groups.setdefault(x.group, []).append(x)
    return {
        "rule": (
            f"wrong when GOP < threshold, right when GOP >= accept, inconclusive between; "
            f"threshold chosen on the tune half for the most catches with false-alarm share <= "
            f"{MAX_FALSE_SHARE}, accept the lowest with accepted-but-wrong share <= "
            f"{MAX_ACCEPTED_WRONG}; pass needs, on the check half, false-alarm share <= "
            f"{MAX_FALSE_SHARE} with >= {MIN_FLAGGED} flags, accepted-but-wrong share <= "
            f"{MAX_ACCEPTED_WRONG} with >= {MIN_ACCEPTED} accepted, and conclusive share >= "
            f"{MIN_CONCLUSIVE}"
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
        out.append(
            Labelled(str(recording), groups[t["sound"]], float(t["gop"]), label == "wrong",
                     is_dropped(t))
        )  # fmt: skip
    return out


def gold_rows(conn: Any) -> list[tuple[str, Any, int, str]]:
    """Expert verdicts per target sound (agreeing experts only) as `from_rows` rows."""
    from app.validation.tiers import Label, effective

    rows = conn.execute(
        "select l.content_id, l.role, l.value, l.independence, r.analysis "
        "from labels l join speech_recordings r on r.id::text = split_part(l.content_id, ':', 1) "
        "where l.content_type='speech_target' and l.aspect='phone_ok' and l.tier='gold' "
        "and r.status='analysed' order by l.content_id, l.id"
    ).fetchall()
    groups: dict[str, tuple[Any, list[Label]]] = {}
    for cid, role, value, key, analysis in rows:
        groups.setdefault(cid, (analysis, []))[1].append(Label(role, value, key))
    out = []
    for cid, (analysis, labels) in groups.items():
        e = effective(labels)
        if e.tier == "gold" and e.value in ("right", "wrong"):
            recording, target = cid.split(":", 1)
            out.append((recording, analysis, int(target), e.value))
    return out


def with_basis(result: dict[str, Any], truth: Truth, recordings: int) -> dict[str, Any]:
    return result | {"recordings": recordings, "basis": basis(truth, recordings, MIN_RECORDINGS)}


def apply_allowed(result: dict[str, Any]) -> bool:
    """Marks reach learners only from a measured (Gold) basis."""
    return measured(result.get("basis", {}))


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - needs the database
    import psycopg

    from app.config import get_settings
    from app.services.recordings import load_prompts

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--apply",
        type=Path,
        help="also write the pass groups to the file the product reads (step 3.4)",
    )
    args = parser.parse_args(argv)
    settings = get_settings()
    sounds, _ = load_prompts(settings.pronunciation_dir)
    with psycopg.connect(settings.database_url) as conn:
        rows = gold_rows(conn)
        truth: Truth = "gold"
        if not rows:
            truth = "bronze"
            rows = conn.execute(
                "select r.id::text, r.analysis, l.target, l.label from speech_labels l "
                "join speech_recordings r on r.id = l.recording_id where r.status = 'analysed'"
            ).fetchall()
    result = with_basis(
        report(from_rows(rows, {s.id: s.group for s in sounds.values()})),
        truth,
        len({r[0] for r in rows}),
    )
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["groups"], indent=2))
    print(json.dumps(result["basis"], indent=2, ensure_ascii=False))
    if args.apply and not apply_allowed(result):
        print("not applied: " + result["basis"].get("why_en", "the basis is not measured"))
        return 1
    if args.apply:
        from datetime import date

        from app.pronunciation.marks import applicable

        applied = applicable(result, date.today().isoformat())
        args.apply.write_text(json.dumps(applied, indent=2) + "\n", encoding="utf-8")
        print(f"applied: {sorted(applied['groups']) or 'no group passed; nothing is marked'}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
