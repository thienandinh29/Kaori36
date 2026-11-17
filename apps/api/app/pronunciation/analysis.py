"""Analyse stored recordings with the pronunciation service (specs/pronunciation, step 3.3).

The worker takes the oldest stored recording, sends it with the prompt's canonical phones to the
service, and keeps only the target sounds' results. After analysis the audio is cleared unless the
learner chose to keep it (the strict voice policy): the scores stay, the voice does not.
Nothing here marks a sound wrong: thresholds come from the owner's labelled recordings (step 3.3b).
"""

import base64
import json
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from app.pronunciation.canonical import Word, flat, targets

Score = Callable[[bytes, list[str]], dict[str, Any]]


def service_score(url: str) -> Score:
    """POST /score on the pronunciation service; raises on any failure."""

    def score(audio: bytes, phones: list[str]) -> dict[str, Any]:
        body = json.dumps({"audio": base64.b64encode(audio).decode(), "phones": phones}).encode()
        request = urllib.request.Request(
            url.rstrip("/") + "/score", body, {"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=120) as r:
            out: dict[str, Any] = json.loads(r.read())
        return out

    return score


def summarise(
    words: Sequence[Word], sounds: Sequence[str], scored: Mapping[str, Any]
) -> dict[str, Any]:
    """The target sounds' results from the service's per-phone output."""
    phones = scored["phones"]
    if len(phones) != len(flat(words)):
        raise ValueError("the service returned a different number of phones")
    return {
        "recognised": list(scored.get("recognised", [])),
        "targets": [
            {
                "sound": t.sound,
                "word": t.text,
                "phone": phones[t.phone]["phone"],
                "gop": phones[t.phone]["gop"],
                "competitor": phones[t.phone]["competitor"],
                "start_ms": phones[t.phone]["start_ms"],
                "end_ms": phones[t.phone]["end_ms"],
            }
            for t in targets(words, sounds)
        ],
    }


def process_next(
    conn: psycopg.Connection[Any],
    score: Score,
    canonical: Mapping[str, Sequence[Word]],
    prompt_sounds: Mapping[str, Sequence[str]],
    now: datetime | None = None,
) -> bool:
    """Analyse one stored recording; False when none waits."""
    row = conn.execute(
        "select id,prompt_id,audio,keep from speech_recordings where status='stored' "
        "order by created_at limit 1 for update skip locked"
    ).fetchone()
    if row is None:
        return False
    rid, prompt_id, audio, keep = row
    now = now or datetime.now(UTC)
    try:
        words = canonical[prompt_id]
        result = summarise(words, prompt_sounds[prompt_id], score(bytes(audio), flat(words)))
    except Exception as exc:  # recorded, never retried in a loop
        conn.execute(
            "update speech_recordings set status='failed', failure=%s, analysed_at=%s"
            + ("" if keep else ", audio=''::bytea")
            + " where id=%s",
            (type(exc).__name__ + ": " + str(exc)[:200], now, rid),
        )
        return True
    conn.execute(
        "update speech_recordings set status='analysed', analysis=%s, analysed_at=%s"
        + ("" if keep else ", audio=''::bytea")
        + " where id=%s",
        (Jsonb(result), now, rid),
    )
    return True
