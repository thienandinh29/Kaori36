"""Step 4.3 (plan CP4): Reading practice, the Silver serving rule, grading and evidence."""

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml  # type: ignore[import-untyped]
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg_pool import ConnectionPool

from app.api import reading_practice as routes
from app.reading.pipeline import generate_text
from app.services.grammar import GrammarService
from app.services.reading_practice import ReadingPractice
from app.services.today import TodayService
from app.validation.store import LabelIn, add_label, add_reviewer

from .test_generation import PASSAGE, generated

NOW = datetime(2026, 12, 1, 9, 0, tzinfo=UTC)
DATA = Path(__file__).resolve().parents[4] / "data"


def label(conn: Any, item: str, role: str, value: str = "right", **kw: Any) -> None:
    add_label(conn, LabelIn(content_type="reading_item", content_id=item, aspect="item_ok",
                            value=value, role=role, **kw))  # fmt: skip


@pytest.fixture
def env(database_url: str, tmp_path: Path) -> Iterator[dict[str, Any]]:
    pool = ConnectionPool(database_url, open=True)
    with pool.connection() as conn:
        learner = conn.execute(
            "insert into learners(display_name) values ('R') returning id::text"
        ).fetchone()
        assert learner is not None

        async def gen(system: str, text: str):  # type: ignore[no-untyped-def]
            return generated()

        asyncio.run(generate_text(conn, "bees", PASSAGE, gen, NOW))
        rows = conn.execute("select id from reading_items where text_slug='bees' order by id")
        ids = [r[0] for r in rows.fetchall()]
        # Approved and Silver (code checks + the blind checker agree): served.
        for i in ("bees-tfng-1", "bees-mcq-1", "bees-headings-1"):
            conn.execute("update reading_items set status='approved' where id=%s", (i,))
            label(conn, i, "code_check", name="reading")
            label(conn, i, "model", name="baidu/ernie")
        # Approved by the owner although the checker doubted it: disputed, not served.
        conn.execute("update reading_items set status='approved' where id='bees-completion-1'")
        label(conn, "bees-completion-1", "code_check", name="reading")
        label(conn, "bees-completion-1", "model", "wrong", name="baidu/ernie")
        label(conn, "bees-completion-1", "owner_developer")
        # Verified by the checker but never approved: not served.
        label(conn, "bees-tfng-2", "code_check", name="reading")
        label(conn, "bees-tfng-2", "model", name="baidu/ernie")
        teacher = add_reviewer(conn, "T", "expert_teacher", "", NOW)
    texts = tmp_path / "texts"
    texts.mkdir()
    (texts / "bees.yaml").write_text(
        yaml.safe_dump({"slug": "bees", "title": "Honey bees", "text": PASSAGE}), "utf-8"
    )
    practice = ReadingPractice(lambda: pool, texts, lambda: NOW)
    app = FastAPI()
    app.include_router(routes.create_router(practice))
    yield {"client": TestClient(app), "learner": learner[0], "pool": pool, "ids": ids,
           "teacher": teacher, "practice": practice}  # fmt: skip
    with pool.connection() as conn:
        conn.execute("delete from reading_items where text_slug='bees'")
        conn.execute("delete from labels where content_type='reading_item'")
        conn.execute("delete from reviewers")
    pool.close()


def test_only_silver_approved_items_are_served(env: dict[str, Any]) -> None:
    c, learner = env["client"], env["learner"]
    texts = c.get("/reading/texts", params={"learner_id": learner}).json()["texts"]
    assert texts == [{"slug": "bees", "title": "Honey bees", "questions": 3, "words": 48}]
    text = c.get("/reading/texts/bees", params={"learner_id": learner}).json()
    assert [i["id"] for i in text["items"]] == ["bees-tfng-1", "bees-mcq-1", "bees-headings-1"]
    assert all("key" not in i and "evidence" not in i for i in text["items"])
    assert text["items"][2]["paragraphs"] == [0, 1, 2]  # positions only
    # The shown order (step 4.3c): fixed per question, never the generator's.
    assert text["items"][1]["options"] == [
        "Stored honey",
        "Nectar from flowers",
        "Pollen",
        "Leaves",
    ]
    assert text["items"][2]["headings"][:2] == ["Surviving winter", "Making honey"]
    # A teacher's Gold label serves the disputed item.
    with env["pool"].connection() as conn:
        label(conn, "bees-completion-1", "expert_teacher", reviewer_id=env["teacher"])
    text = c.get("/reading/texts/bees", params={"learner_id": learner}).json()
    assert "bees-completion-1" in [i["id"] for i in text["items"]]


def test_the_owners_approval_alone_never_serves(env: dict[str, Any]) -> None:
    """Code checks and the owner, with no checker label (its reply was unusable): Bronze."""
    c, learner = env["client"], env["learner"]
    with env["pool"].connection() as conn:
        conn.execute("delete from labels where content_id='bees-tfng-2' and role='model'")
        conn.execute("update reading_items set status='approved' where id='bees-tfng-2'")
        label(conn, "bees-tfng-2", "owner_developer")
    text = c.get("/reading/texts/bees", params={"learner_id": learner}).json()
    assert "bees-tfng-2" not in [i["id"] for i in text["items"]]
    assert c.post("/reading/items/bees-tfng-2/answer",
                  json={"learner_id": learner, "answer": "TRUE"}).status_code == 404  # fmt: skip


def test_answers_are_graded_from_the_key_and_move_the_competency(env: dict[str, Any]) -> None:
    c, learner, pool = env["client"], env["learner"], env["pool"]

    def post(item: str, a: object) -> Any:
        return c.post(f"/reading/items/{item}/answer", json={"learner_id": learner, "answer": a})

    right = post("bees-tfng-1", "TRUE").json()
    assert right["correct"] is True and right["key"] == "TRUE"
    assert right["competency"] == "reading-detail"
    assert right["evidence"] == ["A single colony can hold up to sixty thousand bees."]
    assert right["trace"]["prior"] == 0.2 and right["trace"]["posterior"] > 0.2
    # Options and headings come in the shown order (step 4.3c): "Stored honey", B as generated,
    # is A on the page, and the key reads as the page does.
    wrong = post("bees-mcq-1", 1).json()  # B on the page: "Nectar from flowers"
    assert wrong["correct"] is False and wrong["key"] == "A. Stored honey"
    # The same competency (stored as a 32-bit real, so compared approximately).
    assert wrong["trace"]["prior"] == pytest.approx(right["trace"]["posterior"], abs=1e-6)
    assert post("bees-mcq-1", 0).json()["correct"] is True
    # Headings on the page: 0 Surviving winter, 1 Making honey, 2 Enemies of bees, 3 Life in a
    # colony, 4 Bee dances. Answering in paragraph order (0, 1, 2) no longer scores.
    in_order = post("bees-headings-1", {"0": 0, "1": 1, "2": 2}).json()
    assert in_order["score"] == 0.333  # only paragraph 2 ("Making honey" is shown second)
    heads = post("bees-headings-1", {"0": 3, "1": 1, "2": 4}).json()
    assert heads["correct"] is False and heads["score"] == 0.667  # 2 of 3 paragraphs
    assert heads["key"] == "1: 4, 2: 2, 3: 1"  # paragraphs and headings from 1, as on the page
    with pool.connection() as conn:
        rows = conn.execute(
            "select item_id, correct, answer from reading_answers where learner_id=%s order by id",
            (learner,),
        ).fetchall()
    # Kept in the stored order: the MCQ's right answer is the stored key (1), the headings
    # answer the generator's indices.
    assert rows == [
        ("bees-tfng-1", True, "TRUE"),
        ("bees-mcq-1", False, 0),
        ("bees-mcq-1", True, 1),
        ("bees-headings-1", False, {"0": 2, "1": 1, "2": 4}),
        ("bees-headings-1", False, {"0": 0, "1": 1, "2": 3}),
    ]
    assert post("bees-tfng-2", "TRUE").status_code == 404  # not served
    assert post("bees-headings-1", {"x": 1}).status_code == 422
    unknown = c.get("/reading/texts", params={"learner_id": "00000000-0000-4000-8000-000000000999"})
    assert unknown.status_code == 404


def test_reading_becomes_available_and_measured_in_today(env: dict[str, Any]) -> None:
    pool, learner = env["pool"], env["learner"]
    grammar = GrammarService(
        lambda: pool, DATA / "courses", DATA / "items", DATA / "vocabulary", ""
    )
    today = TodayService(grammar, clock=lambda: NOW, reading=env["practice"])
    comps = {c["slug"]: c for s in today.maps(learner)["skills"] for c in s["competencies"]}
    assert comps["reading-detail"]["available"] is True
    assert comps["reading-detail"]["status"] == "unmeasured"
    for _ in range(3):
        env["practice"].answer(learner, "bees-tfng-1", "TRUE")
    comps = {c["slug"]: c for s in today.maps(learner)["skills"] for c in s["competencies"]}
    assert (
        comps["reading-detail"]["evidence"] == 3
        and comps["reading-detail"]["status"] != "unmeasured"
    )
    kinds = [(a["kind"], a["target"]) for a in today.today(learner, 50)["activities"]]
    assert ("diagnostic", "reading-detail") not in kinds  # measured now


def test_a_text_file_in_another_unicode_form_is_still_served(env: dict[str, Any]) -> None:
    """The fingerprint is of the NFC text, as the bank stores it (app/reading/pipeline.sha256)."""
    import unicodedata

    from app.reading.pipeline import sha256

    word = "café"
    assert sha256(unicodedata.normalize("NFD", word)) == sha256(word)
    # The served file rewritten in NFD (as some editors save it): the questions stay served.
    texts = env["practice"].texts_dir
    nfd = unicodedata.normalize("NFD", PASSAGE + " Café.")
    nfc = unicodedata.normalize("NFC", nfd)
    assert nfd != nfc
    with env["pool"].connection() as conn:
        conn.execute(
            "update reading_items set passage_sha256=%s where text_slug='bees'", (sha256(nfc),)
        )
    (texts / "bees.yaml").write_text(
        yaml.safe_dump({"slug": "bees", "title": "Honey bees", "text": nfd}), "utf-8"
    )
    served = env["client"].get("/reading/texts", params={"learner_id": env["learner"]}).json()
    assert served["texts"][0]["questions"] == 3


def test_a_timed_test_grades_once_counts_blanks_wrong_without_evidence(
    env: dict[str, Any],
) -> None:
    """Step 4.3b: the start fixes questions and time; one submission; a blank gives no evidence."""
    from datetime import timedelta

    from app.services.reading_practice import TEST_SECONDS

    pool, learner = env["pool"], env["learner"]
    now = [NOW]
    practice = ReadingPractice(lambda: pool, env["practice"].texts_dir, lambda: now[0])
    app = FastAPI()
    app.include_router(routes.create_router(practice))
    c = TestClient(app)
    started = c.post("/reading/texts/bees/tests", json={"learner_id": learner}).json()
    assert started["limit_seconds"] == TEST_SECONDS == 1200
    ids = [i["id"] for i in started["items"]]
    assert ids == ["bees-tfng-1", "bees-mcq-1", "bees-headings-1"]
    assert all("key" not in i and "evidence" not in i for i in started["items"])
    now[0] = NOW + timedelta(minutes=12)
    submit = f"/reading/tests/{started['test_id']}/submit"
    body = {"learner_id": learner, "answers": {
        "bees-tfng-1": {"answer": "TRUE", "at_seconds": 95},
        "bees-mcq-1": {"answer": 1, "at_seconds": 300},
    }}  # fmt: skip
    out = c.post(submit, json=body).json()
    assert (out["correct"], out["total"], out["answered"]) == (1, 3, 2)
    mcq = next(i for i in out["items"] if i["id"] == "bees-mcq-1")
    assert (mcq["answer"], mcq["key"]) == (1, "A. Stored honey")  # as on the page
    assert out["over_time"] is False and out["seconds"] == 720
    by_id = {i["id"]: i for i in out["items"]}
    assert by_id["bees-tfng-1"]["correct"] and by_id["bees-tfng-1"]["at_seconds"] == 95
    assert by_id["bees-headings-1"] == {
        "id": "bees-headings-1", "answer": None, "correct": False,
        "key": by_id["bees-headings-1"]["key"], "evidence": [], "at_seconds": None,
    }  # fmt: skip
    with pool.connection() as conn:
        rows = conn.execute(
            "select item_id, test_id::text from reading_answers where learner_id=%s order by id",
            (learner,),
        ).fetchall()
    # Two answers as evidence, both tied to the test; the blank gave none.
    assert rows == [("bees-tfng-1", started["test_id"]), ("bees-mcq-1", started["test_id"])]
    assert c.post(submit, json=body).status_code == 409  # one submission per test


def test_a_late_test_is_graded_but_marked_and_foreign_answers_are_refused(
    env: dict[str, Any],
) -> None:
    from datetime import timedelta

    from app.services.reading_practice import GRACE_SECONDS, TEST_SECONDS

    pool, learner = env["pool"], env["learner"]
    now = [NOW]
    practice = ReadingPractice(lambda: pool, env["practice"].texts_dir, lambda: now[0])
    app = FastAPI()
    app.include_router(routes.create_router(practice))
    c = TestClient(app)
    started = c.post("/reading/texts/bees/tests", json={"learner_id": learner}).json()
    submit = f"/reading/tests/{started['test_id']}/submit"
    foreign = {"learner_id": learner, "answers": {"bees-tfng-2": {"answer": "TRUE"}}}
    assert c.post(submit, json=foreign).status_code == 422  # not served, so not in the test
    now[0] = NOW + timedelta(seconds=TEST_SECONDS + GRACE_SECONDS + 1)
    late = c.post(submit, json={"learner_id": learner, "answers": {}}).json()
    assert late["over_time"] is True and late["correct"] == 0 and late["answered"] == 0
    other = "00000000-0000-4000-8000-000000000999"
    assert c.post("/reading/texts/bees/tests", json={"learner_id": other}).status_code == 404
    assert c.post("/reading/texts/none/tests", json={"learner_id": learner}).status_code == 404
