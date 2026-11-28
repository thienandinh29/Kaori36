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
from app.speaking.language import LanguageStep
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
    gaps and called between or inside a clause. Without a parser only a leading filler marks a
    clause end."""
    words = [Word(w["word"], w["start"], w["end"]) for w in transcript.get("words", [])]
    frames = speech_frames(audio)
    boundaries = clause_boundaries([w.text for w in words], nlp or (lambda text: []))
    return measure(words, pauses(frames), boundaries, len(frames) * FRAME_SECONDS)


MAX_ATTEMPTS = 3


def language_of(
    step: LanguageStep, transcript: dict[str, Any], question: str, measures: dict[str, Any]
) -> dict[str, Any]:
    """The answer's grammar and vocabulary checks (step 5.3a). LanguageTool unreachable raises
    `Unavailable` (retried later); any other failure is stored as failed, not retried in a loop."""
    try:
        return step.analyse(transcript, question, measures)
    except httpx.HTTPError as exc:
        raise Unavailable(str(exc)) from None
    except Exception as exc:  # one answer must not stop the worker
        return {"failed": f"{type(exc).__name__}: {exc}"[:300]}


def _finish(
    conn: psycopg.Connection[Any],
    answer: Any,
    audio: bytes,
    transcript: dict[str, Any],
    measures: dict[str, Any] | None,
    checked: bool,
    question: str,
    nlp: Callable[[str], Any] | None,
    language: LanguageStep | None,
    now: Callable[[], datetime],
) -> None:
    """Measure, and check, a transcribed answer while its audio is still there. Each result is
    written only if the answer does not have it yet; nothing is held locked while the (slow)
    checks run. LanguageTool unreachable raises `Unavailable` after the measures are kept."""
    if measures is None:
        measures = measures_of(audio, transcript, nlp)
        conn.execute(
            "update speaking_answers set measures=%s,measured_at=%s where id=%s "
            "and measures is null",
            (Jsonb(measures), now(), answer),
        )
        conn.commit()
    if language is not None and not checked:
        found = language_of(language, transcript, question, measures)
        conn.execute(
            "update speaking_answers set language=%s,language_at=%s where id=%s "
            "and language is null",
            (Jsonb(found), now(), answer),
        )
        conn.commit()


def process_next(
    conn: psycopg.Connection[Any],
    transcribe: Transcribe,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    nlp: Callable[[str], Any] | None = None,
    language: LanguageStep | None = None,
) -> bool:
    """Transcribe, measure and (with a language step) check one waiting answer; False when none
    waits.

    The row is read and the transaction closed before the service is called (a transcript can take
    minutes), and the result is written only if the answer is still waiting. One worker transcribes,
    so no row lock is needed. A refusal fails the answer at once; a service failure is counted and,
    on the third, fails it too. Answers with fewer failures go first. An answer transcribed
    in an earlier step is finished while its audio is still there.
    """
    row = conn.execute(
        "select id,audio,transcript_attempts,question from speaking_answers "
        "where transcript_status is null and audio is not null "
        "order by transcript_attempts, recorded_at limit 1"
    ).fetchone()
    conn.commit()
    if row is None:
        unfinished = conn.execute(
            "select id,audio,transcript,measures,language is not null,question "
            "from speaking_answers where audio is not null and transcript_status='done' "
            "and (measures is null or (%s and language is null)) order by recorded_at limit 1",
            (language is not None,),
        ).fetchone()
        conn.commit()
        if unfinished is None:
            return False
        answer, audio, transcript, measures, checked, question = unfinished
        _finish(
            conn, answer, bytes(audio), transcript, measures, checked, question, nlp, language, now
        )
        return True
    answer, audio, attempts, question = row
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
    transcript = stored(result)
    done = conn.execute(
        "update speaking_answers set transcript=%s,transcript_status='done',transcribed_at=%s "
        "where id=%s and transcript_status is null",
        (Jsonb(transcript), now(), answer),
    )
    conn.commit()
    if done.rowcount:  # the answer may have been deleted or already finished meanwhile
        _finish(conn, answer, bytes(audio), transcript, None, False, question, nlp, language, now)
    return True
