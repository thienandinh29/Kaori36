"""Make one feature row per recording (resumable) with the same code the app uses for answers.

Audio goes to the recognition service (or a supplied transcript is used), then 5.2's measures and,
when a language step is given, 5.3a's checks; `features.row` turns them into numbers. A recording
that cannot be read or transcribed is written as a failed row with its reason and tried again on
the next run; a service that is down stops the run (everything written so far is kept).
"""

import json
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from app.pronunciation.quality import BadAudio, samples
from app.speaking.language import LanguageStep
from app.speaking.spk001 import features
from app.speaking.spk001.manifest import Item
from app.speaking.transcribe import (
    Refused,
    Transcribe,
    Unavailable,
    language_of,
    measures_of,
    stored,
)


def done_ids(out: Path) -> set[str]:
    """The ids with a finished (not failed) row; the last row per id wins."""
    last: dict[str, bool] = {}
    if out.is_file():
        for line in out.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                last[r["id"]] = "failed" not in r
    return {i for i, ok in last.items() if ok}


def _meta(item: Item) -> dict[str, Any]:
    return {
        "id": item.id,
        "source": item.source,
        "speaker": item.speaker,
        "split": item.split,
        "test": item.test,
        "part": item.part,
        "score": item.score,
    }


def one(
    item: Item,
    transcribe: Transcribe | None,
    nlp: Callable[[str], Any] | None,
    language: LanguageStep | None,
) -> dict[str, Any]:
    """The feature row of one recording, or `{..., "failed": reason}`."""
    audio = item.audio.read_bytes()
    try:
        samples(audio)
    except BadAudio as exc:
        return {**_meta(item), "failed": f"audio: {exc} (convert with ffmpeg first)"}
    if item.words is not None:
        transcript = stored(json.loads(item.words.read_text(encoding="utf-8")))
    elif transcribe is None:
        return {**_meta(item), "failed": "no transcript and no recognition service"}
    else:
        try:
            transcript = stored(transcribe(audio))
        except Refused as exc:
            return {**_meta(item), "failed": f"refused: {exc}"[:300]}
    measures = measures_of(audio, transcript, nlp)
    if item.asked_seconds:
        measures["asked_seconds"] = item.asked_seconds
        measures["share_of_time"] = round(
            min(measures["speaking_seconds"] / item.asked_seconds, 9.99), 2
        )
    checked = None
    if language is not None:
        checked = language_of(language, transcript, item.question, measures)
        if "failed" in checked:
            return {**_meta(item), "failed": f"language: {checked['failed']}"}
    return {**_meta(item), "features": features.row(measures, checked)}


def run(
    items: Iterable[Item],
    out: Path,
    transcribe: Transcribe | None,
    nlp: Callable[[str], Any] | None,
    language: LanguageStep | None,
    log: Callable[[str], None] = lambda _: None,
) -> dict[str, int]:
    """Extract every item not yet done, appending one JSON line each; returns the counts.
    `Unavailable` (the service is down) propagates after what was done is kept."""
    out.parent.mkdir(parents=True, exist_ok=True)
    finished = done_ids(out)
    counts = {"done": 0, "failed": 0, "skipped": 0}
    with out.open("a", encoding="utf-8") as f:
        for item in items:
            if item.id in finished:
                counts["skipped"] += 1
                continue
            try:
                result = one(item, transcribe, nlp, language)
            except Unavailable:
                f.flush()
                raise
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
            f.flush()
            counts["failed" if "failed" in result else "done"] += 1
            if (counts["done"] + counts["failed"]) % 50 == 0:
                log(f"{counts['done']} done, {counts['failed']} failed")
    return counts
