"""Analyse stored recordings with the pronunciation service (specs/pronunciation, step 3.3).

The worker takes the oldest stored recording, sends it with the prompt's canonical phones to the
service, and keeps only the target sounds' results. After analysis the audio is cleared unless the
learner chose to keep it (the strict voice policy): the scores stay, the voice does not.
Nothing here marks a sound wrong: thresholds come from the owner's labelled recordings (step 3.3b).
"""

import base64
import json
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from app.curriculum.course import CourseSpec
from app.curriculum.store import sync_course
from app.engine import bkt
from app.engine.graph import UNSEEN_P_KNOWN
from app.engine.trace import fmt_p
from app.pronunciation.canonical import Word, flat, targets
from app.pronunciation.evidence import LEARNER_GUESS, LEARNER_SLIP
from app.pronunciation.marks import Applied, observations

Score = Callable[[bytes, list[str]], dict[str, Any]]


class ServiceUnavailable(Exception):
    """The pronunciation service could not be reached (starting, down, overloaded): try later."""


def transient(exc: BaseException) -> bool:
    """A failure of the service, not of this recording: the recording stays queued."""
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code >= 500 or exc.code == 429
    return isinstance(exc, urllib.error.URLError | TimeoutError | ConnectionError)


# Reading a sentence aloud is a little practice; small until fitted from data (engine/bkt_fit.py).
P_TRANSIT = 0.05


@dataclass(frozen=True)
class Evidence:
    """What moves the pronunciation nodes (step 3.4b): the course and the applied groups."""

    course: CourseSpec
    group_of: Mapping[str, str]  # sound id -> group = hidden node slug
    applied: Mapping[str, Applied]


def apply_evidence(
    conn: psycopg.Connection[Any],
    learner: Any,
    recording: Any,
    result: Mapping[str, Any],
    evidence: Evidence,
    now: datetime,
) -> list[dict[str, Any]]:
    """BKT updates for one recording; what moved, for the analysis record."""
    from app.services.backend import save_trace
    from app.services.learning import save_mastery

    ts = result["targets"]
    obs = observations(ts, evidence.group_of, evidence.applied)
    if not obs:
        return []
    ids = sync_course(conn, evidence.course)
    subject = conn.execute(
        "select id from subjects where slug=%s", (evidence.course.slug,)
    ).fetchone()
    assert subject is not None
    rows = conn.execute(
        "select concept_id, p_known from mastery where learner_id=%s and concept_id = any(%s)",
        (learner, [ids[g] for g, _, _ in obs]),
    ).fetchall()
    known = {r[0]: float(r[1]) for r in rows}
    moved = []
    for group, index, correct in obs:
        a = evidence.applied[group]
        model = a.evidence()
        assert model is not None  # observations() keeps only groups whose outcomes say something
        slip, guess = model
        params = bkt.BKTParams(p_init=0.2, p_transit=P_TRANSIT, p_slip=slip, p_guess=guess)
        t = ts[index]
        p = known.get(ids[group], UNSEEN_P_KNOWN)
        p_new, trace = bkt.update_traced(
            p, correct, params, concept_slug=group, now=now,
            item_id=f"recording:{recording}:{index}",
            misconception=None if correct else f"pronunciation:{t['sound']}",
        )  # fmt: skip
        verdict = "được nghe là đúng" if correct else "bị đánh dấu là có thể chưa đúng"
        r = a.rates
        trace = trace.model_copy(
            update={
                "rule": "pronunciation.outcome",
                "rule_vi": (
                    f"Âm /{t['phone']}/ trong «{t['word']}» {verdict} → khả năng đã nắm vững "
                    f"{'tăng' if p_new >= p else 'giảm'} từ {fmt_p(p)} "
                    f"{'lên' if p_new >= p else 'xuống'} {fmt_p(p_new)}. Hai loại sai được tính "
                    f"riêng: người học đã nắm vẫn có lúc nói sai (giả định {fmt_p(LEARNER_SLIP)}) "
                    f"hay chưa nắm vẫn nói đúng ({fmt_p(LEARNER_GUESS)}), còn máy đánh dấu nhầm "
                    f"{fmt_p(r.wrong_if_right)} số âm đúng và nghe nhầm thành đúng "
                    f"{fmt_p(r.right_if_wrong)} số âm sai (đo trên bản ghi đã gán nhãn). Âm máy "
                    "chưa chắc thì không tính."
                ),
            }
        )
        save_mastery(conn, learner, ids[group], p_new)
        save_trace(conn, learner, subject[0], trace)
        moved.append({"node": group, "target": index, "correct": correct,
                      "p_before": round(p, 4), "p_after": round(p_new, 4)})  # fmt: skip
    return moved


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
    evidence: Evidence | None = None,
) -> bool:
    """Analyse one stored recording; False when none waits.

    Raises ServiceUnavailable, changing nothing, when the service cannot be reached: a recording is
    marked failed (and, unless kept, its audio cleared) only for a failure of the recording itself.
    """
    row = conn.execute(
        "select id,prompt_id,audio,keep,learner_id from speech_recordings where status='stored' "
        "order by created_at limit 1 for update skip locked"
    ).fetchone()
    if row is None:
        return False
    rid, prompt_id, audio, keep, learner = row
    now = now or datetime.now(UTC)
    try:
        words = canonical[prompt_id]
        result = summarise(words, prompt_sounds[prompt_id], score(bytes(audio), flat(words)))
    except Exception as exc:  # recorded, never retried in a loop
        if transient(exc):
            conn.rollback()  # releases the row lock; the recording stays 'stored'
            raise ServiceUnavailable(f"{type(exc).__name__}: {exc}") from exc
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
    if evidence is not None:  # same transaction: a retried job never counts a recording twice
        result["evidence"] = apply_evidence(conn, learner, rid, result, evidence, now)
        if result["evidence"]:
            conn.execute(
                "update speech_recordings set analysis=%s where id=%s", (Jsonb(result), rid)
            )
    return True
