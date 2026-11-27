"""Step 5.4a (specs/speaking/step-5.4a.md): sittings, answers, owner rule, retention, deletion."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg_pool import ConnectionPool

from app.api import speaking as routes
from app.services.recordings import CONSENT
from app.services.speaking_tests import SpeakingTests, purge_expired
from tests.pronunciation.test_recordings import hiss, speech_like, tone, wav

FOLDER = Path(__file__).resolve().parents[4] / "data" / "speaking" / "tests"
NOW = datetime(2026, 11, 27, 9, 0, tzinfo=UTC)


@pytest.fixture
def setup(database_url: str) -> Iterator[tuple[TestClient, str, str, ConnectionPool]]:
    pool = ConnectionPool(database_url, open=True)
    with pool.connection() as conn:
        ids = []
        for name in ("Owner", "Other"):
            row = conn.execute(
                "insert into learners(display_name) values (%s) returning id", (name,)
            ).fetchone()
            assert row is not None
            ids.append(str(row[0]))
    owner, other = ids
    app = FastAPI()
    app.include_router(
        routes.create_router(SpeakingTests(lambda: pool, FOLDER, owner, lambda: NOW))
    )
    yield TestClient(app), owner, other, pool
    pool.close()


def start(client: TestClient, learner: str, keep: bool = False, consent: str = CONSENT):  # type: ignore[no-untyped-def]
    return client.post(
        "/speaking/tests",
        params={"learner_id": learner},
        json={"test_id": "t01", "consent": consent, "keep": keep},
    )


def answer(client: TestClient, learner: str, sitting: str, question: str, audio: bytes):  # type: ignore[no-untyped-def]
    return client.post(
        f"/speaking/tests/{sitting}/answers",
        params={"learner_id": learner, "question": question},
        content=audio,
        headers={"content-type": "audio/wav"},
    )


def test_only_the_owner_sits_a_test_and_only_after_consent(setup) -> None:  # type: ignore[no-untyped-def]
    client, owner, other, _ = setup
    seen = client.get("/speaking/tests", params={"learner_id": other}).json()
    assert seen["can_record"] is False and seen["past"] == [] and len(seen["tests"]) >= 5
    r = start(client, other)
    assert r.status_code == 403 and "quyền riêng tư" in r.json()["detail"]
    assert start(client, owner, consent="old").status_code == 409
    r = client.post(
        "/speaking/tests",
        params={"learner_id": owner},
        json={"test_id": "t99", "consent": CONSENT},
    )
    assert r.status_code == 404


def test_a_sitting_gives_the_questions_and_timing_and_stores_each_answer_once(setup) -> None:  # type: ignore[no-untyped-def]
    client, owner, other, _ = setup
    s = start(client, owner).json()
    test = s["test"]
    first = test["questions"][0]
    assert (first["id"], first["part"], first["seconds"]) == ("p1-1-1", 1, 40)
    timing = {"part1": 40, "prepare": 60, "long_turn": 120, "closing": 30, "part3": 60}
    assert test["timing"] == timing
    assert len(test["cue_card"]["points"]) == 3 and test["draft"] is True
    ok = answer(client, owner, s["id"], "p1-1-1", speech_like())
    assert ok.status_code == 200 and ok.json()["problems"] == []
    # A quiet answer is still an answer: stored, with the reason, never judged.
    quiet = answer(client, owner, s["id"], "p1-1-2", wav(hiss(1.0, 3)))
    assert quiet.status_code == 200 and "too_quiet" in quiet.json()["problems"]
    assert answer(client, owner, s["id"], "p1-1-1", speech_like()).status_code == 409  # once
    assert answer(client, owner, s["id"], "p3-9", speech_like()).status_code == 404
    assert answer(client, owner, s["id"], "p1-1-3", b"not a wav").status_code == 422
    assert answer(client, owner, s["id"], "p1-1-3", wav(tone(46, 8000))).status_code == 413
    assert answer(client, other, s["id"], "p1-1-3", speech_like()).status_code == 403
    done = client.post(f"/speaking/tests/{s['id']}/finish", params={"learner_id": owner}).json()
    assert done["finished_at"] == NOW.isoformat()
    answered = [q for q in done["questions"] if q["answer"]]
    assert [q["id"] for q in answered] == ["p1-1-1", "p1-1-2"]
    assert answered[0]["answer"]["audio"] is True and "band" not in str(done)
    assert answer(client, owner, s["id"], "p1-1-3", speech_like()).status_code == 409  # finished


def test_audio_is_cleared_after_a_day_unless_kept_and_a_sitting_can_be_deleted(setup) -> None:  # type: ignore[no-untyped-def]
    client, owner, other, pool = setup
    temp = start(client, owner).json()["id"]
    kept = start(client, owner, keep=True).json()["id"]
    a = answer(client, owner, temp, "p1-1-1", speech_like()).json()["id"]
    b = answer(client, owner, kept, "p1-1-1", speech_like()).json()["id"]
    q = {"learner_id": owner}
    assert client.get(f"/speaking/answers/{a}/audio", params=q).content.startswith(b"RIFF")
    theirs = client.get(f"/speaking/answers/{a}/audio", params={"learner_id": other})
    assert theirs.status_code == 403
    with pool.connection() as conn:  # a day passes: only the kept sitting keeps its audio
        assert purge_expired(conn, NOW + timedelta(hours=25)) >= 1  # the database is shared
    assert client.get(f"/speaking/answers/{a}/audio", params=q).status_code == 404
    assert client.get(f"/speaking/answers/{b}/audio", params=q).status_code == 200
    past = {p["id"]: p for p in client.get("/speaking/tests", params=q).json()["past"]}
    assert past[temp]["answers"] == 1 and past[temp]["with_audio"] == 0  # the row stays
    assert past[kept]["with_audio"] == 1
    gone = client.get(f"/speaking/tests/{temp}", params=q).json()["questions"][0]["answer"]
    assert gone["audio"] is False
    assert client.delete(f"/speaking/tests/{kept}", params={"learner_id": other}).status_code == 404
    assert client.delete(f"/speaking/tests/{kept}", params=q).status_code == 204
    with pool.connection() as conn:
        left = conn.execute(
            "select count(*) from speaking_answers where id in (%s,%s)", (a, b)
        ).fetchone()
    assert left == (1,)  # the deleted sitting's answer went with it


def test_the_microphone_check_stores_nothing(setup) -> None:  # type: ignore[no-untyped-def]
    client, owner, _, pool = setup
    count = "select count(*) from speaking_answers"
    with pool.connection() as conn:
        before = conn.execute(count).fetchone()
    r = client.post(
        "/speaking/mic-check", params={"learner_id": owner}, content=speech_like()
    ).json()
    assert r["ok"] is True
    noisy = client.post(
        "/speaking/mic-check", params={"learner_id": owner}, content=wav(hiss(2.0, 6000))
    ).json()
    assert noisy["problems"] == ["too_noisy"]
    with pool.connection() as conn:
        assert conn.execute(count).fetchone() == before
