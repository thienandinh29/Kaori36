"""Step 3.1 (specs/pronunciation/step-3.1.md): quality check, storage, deletion, owner rule."""

import io
import math
import random
import wave
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg_pool import ConnectionPool

from app.api import pronunciation as routes
from app.pronunciation.quality import RATE, check
from app.services.recordings import CONSENT, Recordings, load_prompts, purge_expired

FOLDER = Path(__file__).resolve().parents[4] / "data" / "pronunciation"


def wav(samples: list[int], rate: int = RATE, channels: int = 1) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(
            b"".join(max(-32768, min(32767, s)).to_bytes(2, "little", signed=True) for s in samples)
        )
    return buf.getvalue()


def tone(seconds: float, amp: float, freq: float = 220.0) -> list[int]:
    return [
        round(amp * math.sin(2 * math.pi * freq * i / RATE)) for i in range(int(seconds * RATE))
    ]


def hiss(seconds: float, amp: int, seed: int = 1) -> list[int]:
    rng = random.Random(seed)
    return [rng.randint(-amp, amp) for _ in range(int(seconds * RATE))]


def speech_like() -> bytes:
    """Quiet room, then "speech" well above the floor, then quiet again."""
    return wav(hiss(0.5, 30) + tone(1.2, 8000) + hiss(0.5, 30, 2))


@pytest.mark.parametrize(
    ("audio", "problem"),
    [
        (wav(hiss(0.5, 30)), "too_short"),
        (wav(hiss(16, 30)), "too_long"),
        (wav(hiss(0.5, 3) + tone(1.0, 200) + hiss(0.5, 3)), "too_quiet"),
        (wav(hiss(0.5, 30) + tone(1.0, 40_000) + hiss(0.5, 30)), "clipped"),
        (wav(hiss(2.0, 6000)), "too_noisy"),
        (wav(tone(2.0, 8000), rate=44_100), "format"),
        (wav(tone(1.0, 8000) * 2, channels=2), "format"),
        (b"not a wav file", "format"),
    ],
)
def test_bad_recordings_get_a_reason_not_a_judgement(audio: bytes, problem: str) -> None:
    q = check(audio)
    assert not q.ok and problem in q.problems


def test_a_clean_recording_passes_with_its_measurements() -> None:
    q = check(speech_like())
    assert q.ok and q.problems == ()
    assert q.seconds == pytest.approx(2.2, abs=0.05)
    assert q.snr_db is not None and q.snr_db > 30 and q.speech_seconds >= 1.0


def test_every_prompt_targets_known_sounds_and_all_groups_are_covered() -> None:
    sounds, prompts = load_prompts(FOLDER)
    covered = {t for p in prompts for t in p.targets}
    assert covered == set(sounds)  # every sound has at least one sentence
    assert {s.group for s in sounds.values()} == {
        "final-consonants",
        "th",
        "s-sh-ch-j-r-l",
        "clusters-vowels",
    }


NOW = datetime(2026, 11, 17, 9, 0, tzinfo=UTC)


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
    app.include_router(routes.create_router(Recordings(lambda: pool, FOLDER, owner, lambda: NOW)))
    yield TestClient(app), owner, other, pool
    pool.close()


def post(client: TestClient, learner: str, audio: bytes, **params: object) -> dict:  # type: ignore[type-arg]
    q = {"learner_id": learner, "prompt_id": "p01", "consent": CONSENT, **params}
    r = client.post("/recordings", params=q, content=audio, headers={"content-type": "audio/wav"})
    assert r.status_code == 200, r.text
    return r.json()  # type: ignore[no-any-return]


def test_only_the_owner_records_and_only_after_consent(setup) -> None:  # type: ignore[no-untyped-def]
    client, owner, other, _ = setup
    assert (
        client.get("/pronunciation/prompts", params={"learner_id": other}).json()["can_record"]
        is False
    )
    r = client.post(
        "/recordings",
        params={"learner_id": other, "prompt_id": "p01", "consent": CONSENT},
        content=speech_like(),
    )
    assert r.status_code == 403 and "quyền riêng tư" in r.json()["detail"]
    r = client.post(
        "/recordings",
        params={"learner_id": owner, "prompt_id": "p01", "consent": "old"},
        content=speech_like(),
    )
    assert r.status_code == 409


def test_a_bad_recording_is_never_stored(setup) -> None:  # type: ignore[no-untyped-def]
    client, owner, _, pool = setup
    out = post(client, owner, wav(hiss(2.0, 6000)))
    assert out["id"] is None and out["quality"]["problems"] == ["too_noisy"]
    with pool.connection() as conn:
        assert conn.execute("select count(*) from speech_recordings").fetchone() == (0,)


def test_a_good_recording_is_stored_for_a_day_unless_kept_and_can_be_deleted(setup) -> None:  # type: ignore[no-untyped-def]
    client, owner, other, pool = setup
    temp = post(client, owner, speech_like())
    kept = post(client, owner, speech_like(), keep="true")
    assert temp["id"] and datetime.fromisoformat(temp["delete_after"]) == NOW + timedelta(hours=24)
    assert kept["delete_after"] is None
    listed = client.get("/recordings", params={"learner_id": owner}).json()
    assert {x["id"] for x in listed} == {temp["id"], kept["id"]} and "audio" not in listed[0]
    assert client.get("/recordings", params={"learner_id": other}).json() == []  # only your own
    assert (
        client.delete(f"/recordings/{kept['id']}", params={"learner_id": other}).status_code == 404
    )
    with pool.connection() as conn:  # the day passes: only the kept one is left
        assert purge_expired(conn, NOW + timedelta(hours=25)) == 1
    left = client.get("/recordings", params={"learner_id": owner}).json()
    assert [x["id"] for x in left] == [kept["id"]]
    assert (
        client.delete(f"/recordings/{kept['id']}", params={"learner_id": owner}).status_code == 204
    )
    with psycopg.connect(pool.conninfo) as conn:
        assert conn.execute("select count(*) from speech_recordings").fetchone() == (0,)
