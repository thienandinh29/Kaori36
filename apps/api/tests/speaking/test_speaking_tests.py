"""Step 5.4a (specs/speaking/step-5.4a.md): sittings, answers, owner rule, retention, deletion."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg_pool import ConnectionPool

from app.api import speaking as routes
from app.services.speaking_tests import CONSENT, SpeakingTests, purge_expired
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


def test_without_a_recogniser_no_answer_says_it_waits(setup) -> None:  # type: ignore[no-untyped-def]
    client, owner, _, _ = setup  # this fixture's service has transcripts=False (no ASR_URL)
    s = start(client, owner).json()["id"]
    answer(client, owner, s, "p1-1-1", speech_like())
    got = client.get(f"/speaking/tests/{s}", params={"learner_id": owner}).json()
    a = got["questions"][0]["answer"]
    assert a["transcript"] == "none" and a["text"] is None


# --- Step 5.4b: guided practice, a try at a time ---


def practise(
    client: TestClient,
    learner: str,
    question: str = "p3-1",
    previous: str | None = None,
    **extra: object,
) -> Any:
    body = {"test_id": "t01", "question_id": question, "consent": CONSENT, "previous_id": previous}
    return client.post("/speaking/practice", params={"learner_id": learner}, json={**body, **extra})


def test_a_question_is_tried_three_times_with_less_time_and_never_a_fourth(setup) -> None:  # type: ignore[no-untyped-def]
    client, owner, other, _ = setup
    assert practise(client, other).status_code == 403
    first = practise(client, owner, keep=True).json()
    assert (first["try_no"], first["asked_seconds"], first["keep"]) == (1, 60, True)
    q = {"learner_id": owner}
    # a repeat needs the previous try to have an answer
    assert practise(client, owner, previous=first["id"]).status_code == 409
    assert answer(client, owner, first["id"], "p3-1", speech_like()).status_code == 200
    second = practise(client, owner, previous=first["id"]).json()
    assert (second["try_no"], second["asked_seconds"], second["keep"]) == (2, 45, True)  # keeps
    assert answer(client, owner, second["id"], "p3-1", speech_like()).status_code == 200
    third = practise(client, owner, previous=second["id"]).json()  # any try leads to the first
    assert (third["try_no"], third["asked_seconds"]) == (3, 30)
    assert answer(client, owner, third["id"], "p3-1", speech_like()).status_code == 200
    assert practise(client, owner, previous=third["id"]).status_code == 409  # not a fourth
    view = client.get(f"/speaking/practice/{third['id']}", params=q).json()
    assert view["id"] == first["id"] and view["next_seconds"] is None and view["max_tries"] == 3
    assert [(t["try_no"], t["asked_seconds"], t["counts_as_evidence"]) for t in view["tries"]] == [
        (1, 60, True), (2, 45, False), (3, 30, False)
    ]  # fmt: skip
    assert all(t["answer"]["audio"] for t in view["tries"])
    assert view["question"]["part"] == 3 and view["theme"] == "travel and transport"
    assert view["cue_card"] is None and "tourism" in view["words"]


def test_a_try_takes_only_its_question_within_its_shrunk_time(setup) -> None:  # type: ignore[no-untyped-def]
    client, owner, _, _ = setup
    first = practise(client, owner, "p3-2").json()
    # another question of the test is refused, and so is audio past the time allowed
    assert answer(client, owner, first["id"], "p3-1", speech_like()).status_code == 422
    too_long = wav(tone(66, 8000))  # 60 s allowed + 5 s grace
    assert answer(client, owner, first["id"], "p3-2", too_long).status_code == 413
    assert answer(client, owner, first["id"], "p3-2", speech_like()).status_code == 200
    second = practise(client, owner, "p3-2", previous=first["id"]).json()
    assert answer(client, owner, second["id"], "p3-2", wav(tone(51, 8000))).status_code == 413
    assert practise(client, owner, "p3-3", previous=first["id"]).status_code == 422  # same question
    assert practise(client, owner, "p3-2", previous="not-a-uuid").status_code == 404
    assert practise(client, owner, "p9-9").status_code == 422  # not a question id at all
    unknown = {"test_id": "t99", "question_id": "p3-1", "consent": CONSENT}
    gone = client.post("/speaking/practice", params={"learner_id": owner}, json=unknown)
    assert gone.status_code == 404


def test_part_two_gets_its_cue_card_and_words_and_part_one_none(setup) -> None:  # type: ignore[no-untyped-def]
    client, owner, _, _ = setup
    p2 = practise(client, owner, "p2-long").json()
    assert p2["asked_seconds"] == 120
    v2 = client.get(f"/speaking/practice/{p2['id']}", params={"learner_id": owner}).json()
    assert v2["cue_card"]["task"].startswith("Describe") and "journey" in v2["words"]
    p1 = practise(client, owner, "p1-1-1").json()
    v1 = client.get(f"/speaking/practice/{p1['id']}", params={"learner_id": owner}).json()
    assert v1["words"] == [] and v1["cue_card"] is None and v1["theme"] is None


def test_practice_stays_out_of_the_exam_list_and_is_listed_apart_and_deleted_together(
    setup: Any,
) -> None:
    client, owner, other, pool = setup
    q = {"learner_id": owner}
    first = practise(client, owner).json()
    answer(client, owner, first["id"], "p3-1", speech_like())
    second = practise(client, owner, previous=first["id"]).json()
    seen = client.get("/speaking/tests", params=q).json()
    assert first["id"] not in {p["id"] for p in seen["past"]}  # not an exam sitting
    mine = [p for p in seen["practices"] if p["id"] == first["id"]]
    assert len(mine) == 1 and mine[0]["tries"] == 2 and "travel" in mine[0]["question"].lower()
    assert second["id"] not in {p["id"] for p in seen["practices"]}  # only the first try lists
    t1 = next(t for t in seen["tests"] if t["id"] == "t01")
    assert {"id": "p3-1", "part": 3, "seconds": 60}.items() <= next(
        x for x in t1["practice"] if x["id"] == "p3-1"
    ).items()
    assert (
        client.get(f"/speaking/practice/{first['id']}", params={"learner_id": other}).status_code
        == 403
    )
    assert (
        client.delete(f"/speaking/tests/{first['id']}", params={"learner_id": other}).status_code
        == 404
    )
    assert client.delete(f"/speaking/tests/{first['id']}", params=q).status_code == 204
    with pool.connection() as conn:  # the repeat went with the first try
        assert conn.execute("select count(*) from speaking_tests where id in (%s,%s)",
                            (first["id"], second["id"])).fetchone() == (0,)  # fmt: skip
