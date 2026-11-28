"""The manifest SPK-001's features are made from, and the rules that keep the corpus in its place.

A manifest is a CSV, one row per recording. Columns: `id` (unique), `audio` (path relative to the
manifest; 16 kHz mono 16-bit WAV), `speaker`, `split` (train, dev or eval), `test`, `part`, `score`
(the human holistic score, passed through untouched), `source` (`own` or `corpus`), `question`,
`asked_seconds`, `words` (optional path to a transcript JSON with word timings, which skips
recognition). Only `id`, `audio` and `source` are required. Rules checked before anything runs:
- ids are unique; scores are numbers; a split is one of the three;
- **no speaker is in two splits** (held-out speakers are the experiment's whole premise);
- **corpus rows need the owner's licence note** (`data/private/spk-001/LICENCE.txt`, written after
  the licence is read: the experiment does not start before), and everything is written under
  git-ignored `data/private/` only.
"""

import csv
from dataclasses import dataclass
from pathlib import Path

SPLITS = ("train", "dev", "eval")
SOURCES = ("own", "corpus")


class ManifestError(ValueError):
    """The manifest breaks a rule; the message says which row and why."""


@dataclass(frozen=True)
class Item:
    id: str
    audio: Path
    source: str
    speaker: str = ""
    split: str = ""
    test: str = ""
    part: str = ""
    score: float | None = None
    question: str = ""
    asked_seconds: float | None = None
    words: Path | None = None


def _number(value: str, what: str, row: int) -> float | None:
    if not value.strip():
        return None
    try:
        return float(value)
    except ValueError:
        raise ManifestError(f"row {row}: {what} is not a number: {value!r}") from None


def load(path: Path) -> list[Item]:
    """Read and check a manifest; nothing is opened but the CSV and, for existence, the paths."""
    base = path.parent
    items: list[Item] = []
    seen: set[str] = set()
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = {"id", "audio", "source"} - set(reader.fieldnames or [])
        if missing:
            raise ManifestError(f"missing columns: {', '.join(sorted(missing))}")
        for n, r in enumerate(reader, start=2):
            ident = (r.get("id") or "").strip()
            if not ident:
                raise ManifestError(f"row {n}: id is empty")
            if ident in seen:
                raise ManifestError(f"row {n}: id {ident!r} is repeated")
            seen.add(ident)
            source = (r.get("source") or "").strip()
            if source not in SOURCES:
                raise ManifestError(f"row {n}: source must be one of {', '.join(SOURCES)}")
            split = (r.get("split") or "").strip()
            if split and split not in SPLITS:
                raise ManifestError(f"row {n}: split must be one of {', '.join(SPLITS)}")
            audio = base / (r.get("audio") or "")
            if not (r.get("audio") or "").strip() or not audio.is_file():
                raise ManifestError(f"row {n}: audio file not found: {r.get('audio')!r}")
            words = (r.get("words") or "").strip()
            if words and not (base / words).is_file():
                raise ManifestError(f"row {n}: transcript file not found: {words!r}")
            items.append(
                Item(
                    id=ident,
                    audio=audio,
                    source=source,
                    speaker=(r.get("speaker") or "").strip(),
                    split=split,
                    test=(r.get("test") or "").strip(),
                    part=(r.get("part") or "").strip(),
                    score=_number(r.get("score") or "", "score", n),
                    question=(r.get("question") or "").strip(),
                    asked_seconds=_number(r.get("asked_seconds") or "", "asked_seconds", n),
                    words=base / words if words else None,
                )
            )
    leaks = _leaking_speakers(items)
    if leaks:
        raise ManifestError(
            "speakers in more than one split (held-out speakers are the premise): "
            + ", ".join(sorted(leaks)[:10])
        )
    return items


def _leaking_speakers(items: list[Item]) -> set[str]:
    splits: dict[str, set[str]] = {}
    for i in items:
        if i.speaker and i.split:
            splits.setdefault(i.speaker, set()).add(i.split)
    return {s for s, found in splits.items() if len(found) > 1}


def guard(items: list[Item], out: Path, private: Path) -> None:
    """Refuse a run that would write outside `private`, or that reads corpus audio before the
    owner's licence note exists."""
    root = private.resolve()
    if not out.resolve().is_relative_to(root):
        raise ManifestError(f"output must be under {root} (git-ignored private data)")
    if any(i.source == "corpus" for i in items):
        note = root / "spk-001" / "LICENCE.txt"
        if not note.is_file() or not note.read_text(encoding="utf-8").strip():
            raise ManifestError(
                f"corpus rows need your licence note at {note}: write it after reading the "
                "licence in full (research/experiments/SPK-001.yaml); nothing runs before"
            )
