"""Step 4.4c (plan CP5b): a Reading passage read aloud, then its approved questions by ear."""

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import listening_practice as routes
from app.listening.items import _ascii
from app.listening.passages import MAX_PART, competency, parts, words
from app.services.listening_passages import ListeningPassages
from app.services.listening_practice import ListeningPractice
from tests.reading.test_practice import NOW, env  # noqa: F401  (the served Reading questions)

TEXTS = Path(__file__).resolve().parents[4] / "data" / "english" / "texts"


def test_every_bank_passage_is_read_whole_in_parts_the_voice_can_say() -> None:
    for path in sorted(TEXTS.glob("*.yaml")):
        text = yaml.safe_load(path.read_text(encoding="utf-8"))["text"]
        spoken = parts(text)
        assert all(0 < len(p) <= MAX_PART for p in spoken), path.name
        assert words(" ".join(spoken)) == words(_ascii(text)), path.name  # nothing skipped


def test_a_long_sentence_is_cut_at_commas_then_between_words() -> None:
    long = ", ".join(f"clause number {i} about the bees in the hive" for i in range(12)) + "."
    spoken = parts(long)
    assert len(spoken) > 1 and all(len(p) <= MAX_PART for p in spoken)
    assert words(" ".join(spoken)) == words(long)
    one = " ".join(["word"] * 120) + "."
    assert words(" ".join(parts(one))) == words(one)


def test_detail_questions_train_listening_detail_and_the_rest_the_main_idea() -> None:
    assert competency("detail") == "listening-detail"
    assert {competency(s) for s in ("main_idea", "inference", "writers_view", "skimming")} == {
        "listening-main-idea"
    }


class FakeVoice:
    def __init__(self) -> None:
        self.said: list[str] = []

    async def speak(self, text: str, pace: str) -> bytes:
        self.said.append(text)
        return b"RIFF" + text.encode()[:8]


def client(env: dict[str, Any], voice: FakeVoice | None) -> TestClient:  # noqa: F811
    listening = ListeningPractice(lambda: env["pool"], env["practice"].texts_dir, None)
    passages = ListeningPassages(env["practice"], voice, lambda: NOW)  # type: ignore[arg-type]
    app = FastAPI()
    app.include_router(routes.create_router(listening, passages))
    return TestClient(app)


def test_the_passage_is_never_sent_before_the_answers(env: dict[str, Any]) -> None:  # noqa: F811
    voice = FakeVoice()
    c, learner = client(env, voice), env["learner"]
    listed = c.get("/listening/passages", params={"learner_id": learner}).json()
    assert listed["available"] is True
    assert listed["texts"][0] | {"parts": 0} == {
        "slug": "bees",
        "title": "Honey bees",
        "questions": 2,
        "parts": 0,
        "read_before": False,
    }  # fmt: skip  (headings are left out: they need the paragraphs on screen)
    view = c.get("/listening/passages/bees", params={"learner_id": learner}).json()
    assert [i["id"] for i in view["items"]] == ["bees-tfng-1", "bees-mcq-1"]
    body = str(view)
    assert "passage" not in view and "keep warm" not in body and "key" not in body
    audio = c.get("/listening/passages/bees/audio/0")
    assert audio.status_code == 200 and audio.headers["content-type"] == "audio/wav"
    assert c.get("/listening/passages/bees/audio/0").status_code == 200
    assert len(voice.said) == 1  # cached
    assert c.get(f"/listening/passages/bees/audio/{view['parts']}").status_code == 404


def test_answers_move_listening_and_blanks_give_no_evidence(env: dict[str, Any]) -> None:  # noqa: F811
    c, learner, pool = client(env, FakeVoice()), env["learner"], env["pool"]
    out = c.post(
        "/listening/passages/bees/submit",
        json={"learner_id": learner, "answers": {"bees-tfng-1": "TRUE"}},
    ).json()
    assert (out["correct"], out["total"], out["answered"]) == (1, 2, 1)
    first = out["items"][0]
    assert first["correct"] and first["competency"] == "listening-detail"
    assert out["items"][1]["answer"] is None  # blank: wrong in the score, no evidence
    assert "keep warm" in out["transcript"]  # shown only after answering
    with pool.connection() as conn:
        rows = conn.execute(
            "select item_id, kind, competency, correct from listening_answers where learner_id=%s",
            (learner,),
        ).fetchall()
        reading = conn.execute(
            "select count(*) from reading_answers where learner_id=%s", (learner,)
        ).fetchone()
    assert rows == [("bees-tfng-1", "passage", "listening-detail", True)]
    assert reading == (0,)  # Listening never counts as Reading
    bad = c.post("/listening/passages/bees/submit",
                 json={"learner_id": learner, "answers": {"bees-headings-1": {}}})  # fmt: skip
    assert bad.status_code == 422
    listed = c.get("/listening/passages", params={"learner_id": learner}).json()
    assert listed["texts"][0]["read_before"] is False


def test_without_the_server_voice_nothing_is_offered(env: dict[str, Any]) -> None:  # noqa: F811
    c, learner = client(env, None), env["learner"]
    assert c.get("/listening/passages", params={"learner_id": learner}).json() == {
        "available": False, "texts": [],
    }  # fmt: skip
    assert c.get("/listening/passages/bees", params={"learner_id": learner}).status_code == 503
