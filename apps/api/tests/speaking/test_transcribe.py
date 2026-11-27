"""Step 5.1: the worker's transcript step, the result's transcripts, and the word error rate."""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg_pool import ConnectionPool

from app.api import speaking as routes
from app.services.speaking_tests import CONSENT, SpeakingTests, purge_expired
from app.speaking import transcribe as t
from app.speaking.wer import Pair, edits, report, words
from tests.pronunciation.test_recordings import speech_like

FOLDER = Path(__file__).resolve().parents[4] / "data" / "speaking" / "tests"
NOW = datetime(2026, 11, 27, 9, 0, tzinfo=UTC)
RESULT = {
    "model": "Systran/faster-whisper-small.en",
    "revision": "d1d751a",
    "text": "ignored: rebuilt from the words",
    "words": [
        {"word": "Um,", "start": 0.5, "end": 0.9, "probability": 0.4},
        {"word": "I", "start": 1.0, "end": 1.1, "probability": 0.9},
        {"word": "goes", "start": 1.1, "end": 1.4, "probability": 0.8},
    ],
}


@pytest.fixture
def setup(database_url: str) -> Iterator[tuple[TestClient, str, ConnectionPool, str]]:
    pool = ConnectionPool(database_url, open=True)
    with pool.connection() as conn:
        row = conn.execute(
            "insert into learners(display_name) values ('Owner') returning id"
        ).fetchone()
        assert row is not None
        owner = str(row[0])
    app = FastAPI()
    app.include_router(
        routes.create_router(
            SpeakingTests(lambda: pool, FOLDER, owner, lambda: NOW, transcripts=True)
        )
    )
    client = TestClient(app)
    sitting = client.post(
        "/speaking/tests",
        params={"learner_id": owner},
        json={"test_id": "t02", "consent": CONSENT},
    ).json()["id"]
    yield client, owner, pool, sitting
    pool.close()


def answer(client: TestClient, owner: str, sitting: str, question: str) -> str:
    r = client.post(
        f"/speaking/tests/{sitting}/answers",
        params={"learner_id": owner, "question": question},
        content=speech_like(),
    )
    assert r.status_code == 200, r.text
    return str(r.json()["id"])


def result(client: TestClient, owner: str, sitting: str) -> dict[str, Any]:
    out = client.get(f"/speaking/tests/{sitting}", params={"learner_id": owner}).json()
    return {q["id"]: q["answer"] for q in out["questions"] if q["answer"]}


def drain(pool: ConnectionPool, run: t.Transcribe) -> int:
    n = 0
    with pool.connection() as conn:
        while t.process_next(conn, run, lambda: NOW):
            n += 1
    return n


def test_answers_wait_then_get_a_transcript_from_the_words(setup) -> None:  # type: ignore[no-untyped-def]
    client, owner, pool, sitting = setup
    answer(client, owner, sitting, "p1-1-1")
    assert result(client, owner, sitting)["p1-1-1"]["transcript"] == "waiting"
    seen: list[bytes] = []

    def fake(audio: bytes) -> dict[str, Any]:
        seen.append(audio)
        return RESULT

    assert drain(pool, fake) >= 1
    assert seen[-1].startswith(b"RIFF")
    a = result(client, owner, sitting)["p1-1-1"]
    assert a["transcript"] == "done" and a["text"] == "Um, I goes"  # the learner's error kept
    assert a["words"][2] == {"word": "goes", "start": 1.1, "end": 1.4}
    with pool.connection() as conn:
        stored = conn.execute(
            "select transcript from speaking_answers where id=%s", (a["id"],)
        ).fetchone()
    assert stored is not None and stored[0]["model"] == "Systran/faster-whisper-small.en"


def test_a_refusal_is_stored_once_and_an_outage_is_retried(setup) -> None:  # type: ignore[no-untyped-def]
    client, owner, pool, sitting = setup
    answer(client, owner, sitting, "p1-2-1")

    def down(audio: bytes) -> dict[str, Any]:
        raise t.Unavailable("starting")

    with pool.connection() as conn, pytest.raises(t.Unavailable):
        t.process_next(conn, down, lambda: NOW)
    assert result(client, owner, sitting)["p1-2-1"]["transcript"] == "waiting"  # not marked

    def refuse(audio: bytes) -> dict[str, Any]:
        raise t.Refused("422: bad audio")

    drain(pool, refuse)
    assert result(client, owner, sitting)["p1-2-1"]["transcript"] == "failed"
    assert drain(pool, refuse) == 0  # never retried in a loop


def test_cleared_audio_is_not_transcribed_but_the_transcript_stays(setup) -> None:  # type: ignore[no-untyped-def]
    client, owner, pool, sitting = setup
    first = answer(client, owner, sitting, "p1-3-1")
    drain(pool, lambda audio: RESULT)
    second = answer(client, owner, sitting, "p1-3-2")
    with pool.connection() as conn:
        purge_expired(conn, datetime(2026, 11, 29, tzinfo=UTC))  # both past their day
        conn.commit()
    assert drain(pool, lambda audio: RESULT) == 0
    got = result(client, owner, sitting)
    assert got["p1-3-1"]["transcript"] == "done" and got["p1-3-1"]["audio"] is False
    assert got["p1-3-2"]["transcript"] == "none"
    assert first != second


def test_the_service_client_tells_refusal_from_outage() -> None:
    def transport(status: int) -> httpx.MockTransport:
        return httpx.MockTransport(lambda request: httpx.Response(status, json=RESULT))

    for status, error in ((422, t.Refused), (503, t.Unavailable)):
        with pytest.raises(error):
            t.service_transcribe("http://asr", transport=transport(status))(b"RIFF")
    ok = t.service_transcribe("http://asr", transport=transport(200))(b"RIFF")
    assert ok["words"][1]["word"] == "I"


def test_word_error_rate() -> None:
    assert words("Um, I GOES to school!") == ["um", "i", "goes", "to", "school"]
    assert words("Um, I goes, uh, there", drop_fillers=True) == ["i", "goes", "there"]
    assert words("don't  it's") == ["don't", "it's"]
    assert edits(["a", "b", "c"], ["a", "x", "c", "d"]) == 2  # one substitution, one insertion
    assert edits([], ["a"]) == 1 and edits(["a"], []) == 1
    pairs = [
        Pair("1", "um I goes to school", "I go to school"),  # filler dropped, error corrected
        Pair("2", "we was tired", "we was tired"),
    ]
    r = report(pairs, missing=["3"])
    kept, removed = r["fillers_kept"], r["fillers_removed"]
    assert kept["wer"] == round(2 / 8, 3) and removed["wer"] == round(1 / 7, 3)
    assert kept["low"] is not None and kept["low"] <= kept["wer"] <= kept["high"]
    assert r["missing_transcripts"] == ["3"]
    assert report([])["fillers_kept"]["wer"] is None


def test_a_deleted_sitting_takes_its_transcripts(setup) -> None:  # type: ignore[no-untyped-def]
    client, owner, pool, sitting = setup
    a = answer(client, owner, sitting, "p3-1")
    drain(pool, lambda audio: RESULT)
    assert (
        client.delete(f"/speaking/tests/{sitting}", params={"learner_id": owner}).status_code == 204
    )
    with psycopg.connect(pool.conninfo) as conn:
        assert conn.execute(
            "select count(*) from speaking_answers where id=%s", (a,)
        ).fetchone() == (0,)
