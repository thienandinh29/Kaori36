"""Step 4.4b: Listening practice routes, evidence and "Hôm nay" (a fake voice, a real database)."""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml  # type: ignore[import-untyped]
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg_pool import ConnectionPool

from app.api import listening_practice as routes
from app.api.speech import SpeechClient
from app.services.grammar import GrammarService
from app.services.listening_practice import ListeningPractice
from app.services.today import TodayService

from .test_items import PASSAGE

NOW = datetime(2026, 11, 20, 9, 0, tzinfo=UTC)
DATA = Path(__file__).resolve().parents[4] / "data"


class FakeVoice(SpeechClient):
    def __init__(self) -> None:
        super().__init__("http://voice.invalid")
        self.said: list[tuple[str, str]] = []

    async def speak(self, text: str, pace: str) -> bytes:
        self.said.append((text, pace))
        return b"RIFF" + text.encode()


@pytest.fixture
def env(database_url: str, tmp_path: Path) -> Iterator[dict[str, Any]]:
    pool = ConnectionPool(database_url, open=True)
    with pool.connection() as conn:
        row = conn.execute("insert into learners(display_name) values ('L') returning id::text")
        learner = row.fetchone()
        assert learner is not None
    texts = tmp_path / "texts"
    texts.mkdir()
    (texts / "bees.yaml").write_text(
        yaml.safe_dump({"slug": "bees", "title": "Honey bees", "text": PASSAGE}), "utf-8"
    )
    voice = FakeVoice()
    practice = ListeningPractice(lambda: pool, texts, voice, lambda: NOW)
    app = FastAPI()
    app.include_router(routes.create_router(practice))
    silent = FastAPI()
    silent.include_router(
        routes.create_router(ListeningPractice(lambda: pool, texts, None, lambda: NOW))
    )
    yield {"client": TestClient(app), "silent": TestClient(silent), "learner": learner[0],
           "pool": pool, "voice": voice, "practice": practice}  # fmt: skip
    with pool.connection() as conn:
        conn.execute("delete from listening_answers")
    pool.close()


def test_the_sentence_never_reaches_the_browser_before_answering(env: dict[str, Any]) -> None:
    c, learner = env["client"], env["learner"]
    listed = c.get("/listening/texts", params={"learner_id": learner}).json()
    assert listed == {"available": True, "texts": [
        {"slug": "bees", "title": "Honey bees", "dictation": 2, "gaps": 2},
    ]}  # fmt: skip
    text = c.get("/listening/texts/bees", params={"learner_id": learner}).json()
    items = {i["id"]: i for i in text["items"]}
    assert items["bees-dictation-1"] == {
        "id": "bees-dictation-1",
        "kind": "dictation",
        "prompt": None,
    }
    gap = items["bees-gap-1"]["prompt"]
    assert "___" in gap and "collect" not in gap
    body = text | {}
    assert "Honey bees live" not in str(body) and "sentence" not in str(body)
    # The audio is made on the server, once per sentence and pace.
    for _ in range(2):
        r = c.get("/listening/items/bees-dictation-1/audio", params={"pace": "slow"})
        assert r.status_code == 200 and r.headers["content-type"] == "audio/wav"
    assert env["voice"].said == [
        ("Honey bees live in large colonies near flowers and trees.", "slow")
    ]
    assert c.get("/listening/items/bees-nothing-1/audio").status_code == 404


def test_answers_are_marked_and_move_the_listening_competencies(env: dict[str, Any]) -> None:
    c, learner, pool = env["client"], env["learner"], env["pool"]

    def post(item: str, a: str) -> Any:
        return c.post(f"/listening/items/{item}/answer", json={"learner_id": learner, "answer": a})

    right = post(
        "bees-dictation-1", "honey bees live in large colonies near flowers and trees"
    ).json()
    assert right["correct"] is True and right["score"] == 1.0
    assert right["competency"] == "listening-dictation"
    assert right["trace"]["prior"] == 0.2 and right["trace"]["posterior"] > 0.2
    near = post("bees-dictation-1", "Honey bee live in large colony near flowers and trees.").json()
    assert near["correct"] is False and near["score"] == 0.8
    assert [w["word"] for w in near["words"] if w["status"] == "wrong"] == ["bees", "colonies"]
    gap = post("bees-gap-1", "colect").json()
    assert gap["correct"] is False and gap["key"] == "collect"
    assert gap["competency"] == "listening-detail" and gap["words"] == []
    with pool.connection() as conn:
        rows = conn.execute(
            "select item_id, kind, competency, correct from listening_answers "
            "where learner_id=%s order by id",
            (learner,),
        ).fetchall()
    assert rows == [
        ("bees-dictation-1", "dictation", "listening-dictation", True),
        ("bees-dictation-1", "dictation", "listening-dictation", False),
        ("bees-gap-1", "gap", "listening-detail", False),
    ]
    assert post("bees-gap-9", "x").status_code == 404
    other = "00000000-0000-4000-8000-000000000999"
    assert c.post("/listening/items/bees-gap-1/answer",
                  json={"learner_id": other, "answer": "x"}).status_code == 404  # fmt: skip


def test_without_a_server_voice_nothing_is_offered(env: dict[str, Any]) -> None:
    s, learner = env["silent"], env["learner"]
    assert s.get("/listening/texts", params={"learner_id": learner}).json() == {
        "available": False, "texts": [],
    }  # fmt: skip
    assert s.get("/listening/texts/bees", params={"learner_id": learner}).status_code == 503
    assert s.get("/listening/items/bees-dictation-1/audio").status_code == 503
    r = s.post("/listening/items/bees-gap-1/answer", json={"learner_id": learner, "answer": "x"})
    assert r.status_code == 503


def test_listening_becomes_available_and_measured_in_today(env: dict[str, Any]) -> None:
    pool, learner, practice = env["pool"], env["learner"], env["practice"]
    grammar = GrammarService(
        lambda: pool, DATA / "courses", DATA / "items", DATA / "vocabulary", ""
    )
    silent = TodayService(grammar, clock=lambda: NOW)
    comps = {c["slug"]: c for s in silent.maps(learner)["skills"] for c in s["competencies"]}
    assert comps["listening-dictation"]["available"] is False
    today = TodayService(grammar, clock=lambda: NOW, listening=practice)
    comps = {c["slug"]: c for s in today.maps(learner)["skills"] for c in s["competencies"]}
    assert comps["listening-dictation"]["available"] is True
    assert comps["listening-dictation"]["status"] == "unmeasured"
    for _ in range(3):
        practice.answer(learner, "bees-dictation-1", "Honey bees live in large colonies.")
    comps = {c["slug"]: c for s in today.maps(learner)["skills"] for c in s["competencies"]}
    assert comps["listening-dictation"]["evidence"] == 3
    assert comps["listening-dictation"]["status"] != "unmeasured"
    acts = today.today(learner, 50)["activities"]
    assert ("diagnostic", "listening-dictation") not in [(a["kind"], a["target"]) for a in acts]
    links = {a["target"]: a["href"] for a in acts if a["target"].startswith("listening-")}
    assert all(link == "/nghe" for link in links.values())


def test_shadowing_shows_its_own_sentences_and_voices_them(env: dict[str, Any]) -> None:
    c, s, learner = env["client"], env["silent"], env["learner"]
    listed = c.get("/shadowing/texts", params={"learner_id": learner}).json()
    assert listed["available"] is True and listed["texts"][0]["slug"] == "bees"
    text = c.get("/shadowing/texts/bees", params={"learner_id": learner}).json()
    dictation = {i.sentence for i in env["practice"].items()["bees"]}
    shown = [x["text"] for x in text["sentences"]]
    assert shown and not set(shown) & dictation
    first = text["sentences"][0]["id"]
    r = c.get(f"/listening/items/{first}/audio")
    assert r.status_code == 200 and env["voice"].said[-1] == (shown[0], "normal")
    assert c.get("/listening/items/bees-shadow-99/audio").status_code == 404
    assert s.get("/shadowing/texts", params={"learner_id": learner}).json()["available"] is False
    assert s.get("/shadowing/texts/bees", params={"learner_id": learner}).status_code == 503
