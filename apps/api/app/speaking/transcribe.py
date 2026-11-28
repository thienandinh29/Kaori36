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


MAX_ATTEMPTS = 3


def process_next(
    conn: psycopg.Connection[Any],
    transcribe: Transcribe,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> bool:
    """Transcribe one waiting answer; False when none waits.

    The row is read and the transaction closed before the service is called (a transcript can take
    minutes), and the result is written only if the answer is still waiting. One worker transcribes,
    so no row lock is needed. A refusal fails the answer at once; a service failure is counted and,
    on the third, fails it too. Answers with fewer failures go first.
    """
    row = conn.execute(
        "select id,audio,transcript_attempts from speaking_answers "
        "where transcript_status is null and audio is not null "
        "order by transcript_attempts, recorded_at limit 1"
    ).fetchone()
    conn.commit()
    if row is None:
        return False
    answer, audio, attempts = row
    try:
        result = transcribe(bytes(audio))
    except Refused as exc:
        conn.execute(
            "update speaking_answers set transcript=%s,transcript_status='failed',"
            "transcript_error=%s,transcribed_at=%s where id=%s and transcript_status is null",
            (Jsonb({"error": str(exc)}), str(exc)[:200], now(), answer),
        )
        conn.commit()
        return True
    except Unavailable as exc:
        failed = attempts + 1 >= MAX_ATTEMPTS
        conn.execute(
            "update speaking_answers set transcript_attempts=transcript_attempts+1,"
            "transcript_error=%s"
            + (",transcript_status='failed',transcript=%s,transcribed_at=%s" if failed else "")
            + " where id=%s and transcript_status is null",
            (
                (
                    str(exc)[:200],
                    Jsonb({"error": f"service unavailable: {exc}"[:200]}),
                    now(),
                    answer,
                )
                if failed
                else (str(exc)[:200], answer)
            ),
        )
        conn.commit()
        raise
    conn.execute(
        "update speaking_answers set transcript=%s,transcript_status='done',transcribed_at=%s "
        "where id=%s and transcript_status is null",
        (Jsonb(stored(result)), now(), answer),
    )
    conn.commit()
    return True
