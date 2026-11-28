"""Fluency measures of a Speaking answer (specs/speaking/step-5.2.md): numbers, never a verdict.

Pauses are found in the raw audio (the recogniser's voice-activity filter removes the silences these
numbers need), then placed on the gaps between words and called "between clauses" or "inside a
clause" from the clause boundaries of the transcript. The rates come from the word timings. Every
threshold below is an assumption, one constant each, and the page says the app only counts.
"""

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app.pronunciation.quality import FRAME, QUIET_DB, RATE, BadAudio, _db, _percentile, samples
from app.speaking.wer import FILLERS

PAUSE_SECONDS = 0.5  # a stretch of non-speech at least this long between speech is a pause
LONG_PAUSE_SECONDS = 2.0
SHORT_ANSWER_SECONDS = 15.0  # under this much speaking, rates are shown with a warning
SPEECH_ABOVE_NOISE_DB = 10.0  # the recording-quality check's own rule for a speech frame
FRAME_SECONDS = FRAME / RATE
_EDGE_PUNCTUATION = re.compile(r"[.,;:?!]+$")


@dataclass(frozen=True)
class Word:
    text: str
    start: float
    end: float


@dataclass(frozen=True)
class Pause:
    start: float
    end: float

    @property
    def seconds(self) -> float:
        return self.end - self.start


def speech_frames(data: bytes) -> list[bool]:
    """Per 30 ms frame, whether it holds speech: louder than the noise floor by 10 dB and not
    quiet in absolute terms (the rule the recording-quality check uses). Unreadable audio: none."""
    try:
        x = samples(data)
    except BadAudio:
        return []
    levels = [
        _db(math.sqrt(sum(s * s for s in x[i : i + FRAME]) / FRAME))
        for i in range(0, len(x) - FRAME + 1, FRAME)
    ]
    if not levels:
        return []
    noise = _percentile(levels, 0.1)
    return [level > noise + SPEECH_ABOVE_NOISE_DB and level > QUIET_DB for level in levels]


def pauses(frames: Sequence[bool], minimum: float = PAUSE_SECONDS) -> list[Pause]:
    """Runs of non-speech frames of at least `minimum` seconds between the first and last speech
    frame. Leading and trailing silence is not a pause."""
    if True not in frames:
        return []
    first = frames.index(True)
    last = len(frames) - 1 - frames[::-1].index(True)
    out: list[Pause] = []
    run = None
    for i in range(first, last + 1):
        if not frames[i]:
            run = i if run is None else run
        elif run is not None:
            if (i - run) * FRAME_SECONDS >= minimum:
                out.append(Pause(round(run * FRAME_SECONDS, 2), round(i * FRAME_SECONDS, 2)))
            run = None
    return out


def clean(word: str) -> str:
    return _EDGE_PUNCTUATION.sub("", word).strip().lower()


def is_filler(word: str) -> bool:
    return clean(word) in FILLERS


def place(pause: Pause, words: Sequence[Word]) -> int | None:
    """The index of the word after which the pause falls: the last word that starts before the
    pause's middle. None for a pause before the first word or after the last (not counted)."""
    middle = (pause.start + pause.end) / 2
    index = None
    for i, w in enumerate(words):
        if w.start <= middle:
            index = i
        else:
            break
    if index is None or index >= len(words) - 1:
        return None
    return index


def _rate(count: float, seconds: float) -> float | None:
    return None if seconds <= 0 else round(count / seconds * 60, 1)


def measure(
    words: Sequence[Word],
    found: Sequence[Pause],
    boundaries: set[int],
    recording_seconds: float,
    asked_seconds: float | None = None,
) -> dict[str, Any]:
    """The measures of one answer. `boundaries` holds the word indices after which a clause ends."""
    if not words:
        return {
            "words": 0,
            "recording_seconds": round(recording_seconds, 2),
            "speaking_seconds": 0.0,
            "short": True,
            "speech_rate": None,
            "articulation_rate": None,
            "pauses": {"count": 0, "per_minute": None, "between_clauses": 0, "inside_clause": 0,
                       "long": 0, "total_seconds": 0.0, "longest_seconds": 0.0, "unplaced": 0},
            "fillers": {"count": 0},
            "longest_run": {"words": 0, "seconds": 0.0},
            "asked_seconds": asked_seconds,
            "share_of_time": None,
        }  # fmt: skip
    span = words[-1].end - words[0].start
    placed: list[tuple[Pause, int]] = []
    unplaced = 0
    for p in found:
        at = place(p, words)
        if at is None:
            unplaced += 1
        else:
            placed.append((p, at))
    paused = sum(p.seconds for p, _ in placed)
    between = sum(1 for _, i in placed if i in boundaries)
    cuts = sorted({i for _, i in placed})
    starts = [0, *(i + 1 for i in cuts)]
    ends = [*cuts, len(words) - 1]
    run = max(
        ((e - s + 1, words[e].end - words[s].start) for s, e in zip(starts, ends, strict=True)),
        key=lambda r: (r[0], r[1]),
    )
    return {
        "words": len(words),
        "recording_seconds": round(recording_seconds, 2),
        "speaking_seconds": round(span, 2),
        "short": span < SHORT_ANSWER_SECONDS,
        "speech_rate": _rate(len(words), span),
        "articulation_rate": _rate(len(words), span - paused),
        "pauses": {
            "count": len(placed),
            "per_minute": _rate(len(placed), span),
            "between_clauses": between,
            "inside_clause": len(placed) - between,
            "long": sum(1 for p, _ in placed if p.seconds >= LONG_PAUSE_SECONDS),
            "total_seconds": round(paused, 2),
            "longest_seconds": round(max((p.seconds for p, _ in placed), default=0.0), 2),
            "unplaced": unplaced,
        },
        "fillers": {"count": sum(1 for w in words if is_filler(w.text))},
        "longest_run": {"words": run[0], "seconds": round(run[1], 2)},
        "asked_seconds": asked_seconds,
        "share_of_time": None if not asked_seconds else round(min(span / asked_seconds, 9.99), 2),
    }


def pooled(parts: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    """The test's numbers pooled over its measured answers: total words over total speaking time,
    pauses summed. None when no answer has measures."""
    parts = [m for m in parts if m.get("words")]
    if not parts:
        return None
    words = sum(m["words"] for m in parts)
    span = sum(m["speaking_seconds"] for m in parts)
    count = sum(m["pauses"]["count"] for m in parts)
    return {
        "answers": len(parts),
        "words": words,
        "speaking_seconds": round(span, 1),
        "speech_rate": _rate(words, span),
        "pauses_per_minute": _rate(count, span),
        "between_clauses": sum(m["pauses"]["between_clauses"] for m in parts),
        "inside_clause": sum(m["pauses"]["inside_clause"] for m in parts),
        "long": sum(m["pauses"]["long"] for m in parts),
        "fillers": sum(m["fillers"]["count"] for m in parts),
        "longest_run_words": max(m["longest_run"]["words"] for m in parts),
    }
