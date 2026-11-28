"""Transcripts of the examiner test's answers (specs/speaking/step-5.1.md), one answer per call.

The worker sends the oldest answer that has audio and no transcript to the recognition service and
stores the result. A refusal (bad audio) is stored as `failed` with its reason and never retried
in a loop; an unreachable service raises `Unavailable` so the worker waits and tries again later.
Audio cleared after its 24 hours before it was reached simply stays untranscribed.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx
import psycopg
from psycopg.types.json import Jsonb

from app.speaking.clauses import clause_boundaries
from app.speaking.measures import FRAME_SECONDS, Word, measure, pauses, speech_frames

Transcribe = Callable[[bytes], dict[str, Any]]


class Unavailable(RuntimeError):
    """The recognition service did not answer (starting, downloading its weights, or down)."""


class Refused(ValueError):
    """The service refused this audio; retrying will not help."""


def service_transcribe(
    url: str, timeout: float = 600.0, transport: httpx.BaseTransport | None = None
) -> Transcribe:
    """POST the WAV to the service; a 4xx is a refusal, anything else unavailability."""

    def run(audio: bytes) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=timeout, trust_env=False, transport=transport) as client:
                r = client.post(
                    f"{url.rstrip('/')}/transcribe",
                    content=audio,
                    headers={"content-type": "audio/wav"},
                )
        except httpx.HTTPError as exc:
            raise Unavailable(str(exc)) from None
        if 400 <= r.status_code < 500:
            raise Refused(f"{r.status_code}: {r.text[:200]}")
        if r.status_code != 200:
            raise Unavailable(f"{r.status_code}: {r.text[:200]}")
        data: dict[str, Any] = r.json()
        return data

    return run


def stored(result: dict[str, Any]) -> dict[str, Any]:
    """What is kept: the text, the words with their timings, and which model made them."""
    words: list[dict[str, Any]] = [
        {
            "word": str(w["word"]),
            "start": float(w["start"]),
            "end": float(w["end"]),
            "probability": float(w["probability"]),
        }
        for w in result.get("words", [])
    ]
    return {
        "text": " ".join(str(w["word"]) for w in words),
        "words": words,
        "model": str(result.get("model", "")),
        "revision": str(result.get("revision", "")),
    }


def measures_of(
    audio: bytes, transcript: dict[str, Any], nlp: Callable[[str], Any] | None = None
) -> dict[str, Any]:
    """The answer's fluency measures (step 5.2): pauses from the raw audio, placed on the words'
    gaps and called between or inside a clause. Without a parser only punctuation marks a clause."""
    words = [Word(w["word"], w["start"], w["end"]) for w in transcript.get("words", [])]
    frames = speech_frames(audio)
    boundaries = clause_boundaries([w.text for w in words], nlp or (lambda text: []))
    return measure(words, pauses(frames), boundaries, len(frames) * FRAME_SECONDS)


def process_next(
    conn: psycopg.Connection[Any],
    transcribe: Transcribe,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    nlp: Callable[[str], Any] | None = None,
) -> bool:
    """Transcribe, and measure, one waiting answer; False when none waits. An answer transcribed
    before measures existed is measured while its audio is still there."""
    row = conn.execute(
        "select id,audio,transcript,transcript_status from speaking_answers where audio is not null"
        " and (transcript_status is null or (transcript_status='done' and measures is null)) "
        "order by recorded_at limit 1 for update skip locked"
    ).fetchone()
    if row is None:
        conn.commit()
        return False
    answer, audio, transcript, status = row
    if status is None:
        try:
            result = transcribe(bytes(audio))
        except Refused as exc:
            conn.execute(
                "update speaking_answers set transcript=%s,transcript_status='failed',"
                "transcribed_at=%s where id=%s",
                (Jsonb({"error": str(exc)}), now(), answer),
            )
            conn.commit()
            return True
        except Unavailable:
            conn.rollback()
            raise
        transcript = stored(result)
        conn.execute(
            "update speaking_answers set transcript=%s,transcript_status='done',transcribed_at=%s "
            "where id=%s",
            (Jsonb(transcript), now(), answer),
        )
    conn.execute(
        "update speaking_answers set measures=%s,measured_at=%s where id=%s",
        (Jsonb(measures_of(bytes(audio), transcript, nlp)), now(), answer),
    )
    conn.commit()
    return True
