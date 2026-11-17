# ruff: noqa: RUF001
"""Step 3.3a (specs/pronunciation/step-3.3.md): canonical phones, target rules, worker analysis."""

from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg_pool import ConnectionPool

from app.api import pronunciation as routes
from app.pronunciation.analysis import process_next, summarise
from app.pronunciation.canonical import (
    Word,
    check,
    cluster_positions,
    flat,
    load_canonical,
    phone_set,
    targets,
)
from app.services.recordings import Recordings, load_checked_canonical, load_prompts

from .test_recordings import NOW, post, speech_like

FOLDER = Path(__file__).resolve().parents[4] / "data" / "pronunciation"


def w(text: str, phones: str) -> Word:
    return Word(text, tuple(phones.split()))


def test_every_prompt_has_canonical_phones_the_model_knows_and_every_target_occurs() -> None:
    _, prompts = load_prompts(FOLDER)
    canonical = load_canonical(FOLDER / "canonical.yaml")
    model = phone_set(FOLDER / "model-phones.txt")
    assert len(model) > 300 and "θ" in model and "iː" in model
    assert check(canonical, {p.id: (p.text, p.targets) for p in prompts}, model) == []
    assert set(canonical) == {p.id for p in prompts}


def test_check_names_each_kind_of_problem() -> None:
    canonical = {"x": [w("Hi", "h aɪ"), w("there", "ð ɛ ə")]}
    problems = check(
        canonical,
        {"x": ("Hi you.", ["th-voiceless"]), "y": ("Hello.", [])},
        {"h", "aɪ", "ð", "ɛ"},
    )
    assert problems == [
        "x: words differ from the prompt",
        "x: phones not in the model's set: ['ə']",
        "x: target th-voiceless never occurs",
        "y: no canonical phones",
    ]


def test_final_consonants_count_only_at_the_end_of_a_word() -> None:
    words = [w("top", "t ɒ p"), w("cat", "k æ t"), w("it", "ɪ t")]
    found = targets(words, ["final-t"])
    assert [(t.text, t.phone) for t in found] == [("cat", 5), ("it", 7)]  # not the t of "top"


def test_anywhere_sounds_and_clusters_are_found_once_each_in_order() -> None:
    words = [w("three", "θ ɹ iː"), w("texts", "t ɛ k s t s")]
    found = targets(words, ["th-voiceless", "r-l", "long-ee", "clusters"])
    # θ and ɹ are both in the onset cluster: the first rule that names a position keeps it
    assert [(t.sound, t.phone) for t in found] == [
        ("th-voiceless", 0),
        ("r-l", 1),
        ("long-ee", 2),
        ("clusters", 5),
        ("clusters", 6),
        ("clusters", 7),
        ("clusters", 8),
    ]


@pytest.mark.parametrize(
    ("phones", "expected"),
    [("s t ɹ iː t", [0, 1, 2]), ("m ʌ n θ", [2, 3]), ("k æ t", []), ("t ɛ k s t s", [2, 3, 4, 5])],
)
def test_clusters_are_two_or_more_consonants_at_a_word_edge(
    phones: str, expected: list[int]
) -> None:
    assert cluster_positions(phones.split()) == expected


def fake_phones(phones: list[str]) -> dict[str, Any]:
    return {
        "recognised": phones,
        "phones": [
            {
                "phone": p,
                "start_ms": 100 * i,
                "end_ms": 100 * i + 80,
                "gop": -0.1 * i,
                "competitor": p,
            }
            for i, p in enumerate(phones)
        ],
    }


def test_summarise_keeps_only_the_target_sounds() -> None:
    words = [w("the", "ð ə"), w("cat", "k æ t")]
    out = summarise(words, ["th-voiced", "final-t"], fake_phones(flat(words)))
    assert [(t["sound"], t["word"], t["phone"], t["start_ms"]) for t in out["targets"]] == [
        ("th-voiced", "the", "ð", 0),
        ("final-t", "cat", "t", 400),
    ]
    with pytest.raises(ValueError, match="number of phones"):
        summarise(words, ["final-t"], fake_phones(["ð"]))


@pytest.fixture
def stack(database_url: str) -> Iterator[tuple[TestClient, str, ConnectionPool]]:
    pool = ConnectionPool(database_url, open=True)
    with pool.connection() as conn:
        row = conn.execute(
            "insert into learners(display_name) values ('Owner') returning id"
        ).fetchone()
        assert row is not None
        owner = str(row[0])
    app = FastAPI()
    app.include_router(routes.create_router(Recordings(lambda: pool, FOLDER, owner, lambda: NOW)))
    yield TestClient(app), owner, pool
    with pool.connection() as conn:  # one database per run: leave no rows for other tests
        conn.execute("delete from speech_recordings where learner_id=%s", (owner,))
    pool.close()


def test_the_worker_analyses_each_recording_once_and_clears_audio_unless_kept(stack) -> None:  # type: ignore[no-untyped-def]
    client, owner, pool = stack
    _, prompts = load_prompts(FOLDER)
    canonical = load_checked_canonical(FOLDER, prompts)
    sounds = {p.id: p.targets for p in prompts}
    temp = post(client, owner, speech_like())["id"]
    kept = post(client, owner, speech_like(), keep="true")["id"]
    sent: list[int] = []

    def score(audio: bytes, phones: list[str]) -> dict[str, Any]:
        sent.append(len(audio))
        assert phones == flat(canonical["p01"])
        return fake_phones(phones)

    with pool.connection() as conn:
        assert process_next(conn, score, canonical, sounds, NOW + timedelta(minutes=1))
        assert process_next(conn, score, canonical, sounds, NOW + timedelta(minutes=1))
        assert not process_next(conn, score, canonical, sounds)  # nothing left
        audio = dict(
            conn.execute("select id::text, length(audio) from speech_recordings").fetchall()
        )
    assert len(sent) == 2 and all(n > 1000 for n in sent)
    assert audio[temp] == 0 and audio[kept] > 1000  # the voice goes, the scores stay

    out = client.get(f"/recordings/{temp}", params={"learner_id": owner}).json()
    assert out["status"] == "analysed" and not out["failed"]
    found = {t["sound"] for t in out["analysis"]["targets"]}
    assert found == set(sounds["p01"])
    assert client.get("/recordings/not-a-uuid", params={"learner_id": owner}).status_code == 404


def test_a_service_failure_is_recorded_not_retried(stack) -> None:  # type: ignore[no-untyped-def]
    client, owner, pool = stack
    _, prompts = load_prompts(FOLDER)
    canonical = load_checked_canonical(FOLDER, prompts)
    rid = post(client, owner, speech_like())["id"]

    def broken(audio: bytes, phones: list[str]) -> dict[str, Any]:
        raise OSError("service down")

    with pool.connection() as conn:
        assert process_next(conn, broken, canonical, {p.id: p.targets for p in prompts})
        assert not process_next(conn, broken, canonical, {p.id: p.targets for p in prompts})
    out = client.get(f"/recordings/{rid}", params={"learner_id": owner}).json()
    assert out["status"] == "failed" and out["failed"] and out["analysis"] is None


def test_the_owner_labels_kept_recordings_and_hears_only_kept_audio(stack) -> None:  # type: ignore[no-untyped-def]
    client, owner, pool = stack
    _, prompts = load_prompts(FOLDER)
    canonical = load_checked_canonical(FOLDER, prompts)
    sounds = {p.id: p.targets for p in prompts}
    kept = post(client, owner, speech_like(), keep="true")["id"]
    temp = post(client, owner, speech_like())["id"]
    q = {"learner_id": owner}
    # before analysis there is nothing to label
    early = client.post(
        f"/recordings/{kept}/labels", params=q, json={"labels": [{"target": 0, "label": "right"}]}
    )
    assert early.status_code == 404
    with pool.connection() as conn:
        while process_next(conn, lambda a, p: fake_phones(p), canonical, sounds):
            pass
    audio = client.get(f"/recordings/{kept}/audio", params=q)
    assert audio.status_code == 200 and audio.content[:4] == b"RIFF"
    assert audio.headers["cache-control"] == "no-store"
    assert client.get(f"/recordings/{temp}/audio", params=q).status_code == 404  # cleared

    labels = {"labels": [{"target": 0, "label": "wrong"}, {"target": 1, "label": "unsure"}]}
    assert client.post(f"/recordings/{kept}/labels", params=q, json=labels).status_code == 204
    fix = {"labels": [{"target": 0, "label": "right"}]}  # a label can be changed
    assert client.post(f"/recordings/{kept}/labels", params=q, json=fix).status_code == 204
    out = client.get(f"/recordings/{kept}", params=q).json()
    assert out["labels"] == [{"target": 0, "label": "right"}, {"target": 1, "label": "unsure"}]

    too_far = {"labels": [{"target": 99, "label": "right"}]}
    assert client.post(f"/recordings/{kept}/labels", params=q, json=too_far).status_code == 422
    bad = {"labels": [{"target": 0, "label": "maybe"}]}
    assert client.post(f"/recordings/{kept}/labels", params=q, json=bad).status_code == 422
    assert client.delete(f"/recordings/{kept}", params=q).status_code == 204
    with pool.connection() as conn:  # the labels go with the recording
        assert conn.execute("select count(*) from speech_labels").fetchone() == (0,)
