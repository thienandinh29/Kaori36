"""A pasted Reading test through the service and the worker (step 4.3d)."""

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import psycopg
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from psycopg_pool import ConnectionPool

from app.api import reading_own as routes
from app.llm.gateway import Gateway, ProviderReply, Route, Routing
from app.reading import own_test as ot
from app.services.budget import Budget
from app.services.reading_own import OwnTests, process_next_own_test
from app.writing.model_calls import Prices, WritingModel
from tests.reading.test_own_test import PASSAGE, QUESTIONS

# Before every other test's clock: `spent_today` counts all calls from the start of its day onwards,
# so calls dated later would use up other tests' daily budget in the shared test database.
NOW = datetime(2025, 6, 2, 3, 0, tzinfo=UTC)
KEY = "1 TRUE 2 NOT GIVEN 3 FALSE 4 B 5 species 6 i"
ANSWERS = "1 TRUE 2 FALSE 3 FALSE 4 A 5 specie"  # 6 left blank
PARSED = {"questions": [
    {"number": 1, "kind": "tfng", "text": "The Thames was declared dead in 1957."},
    {"number": 2, "kind": "tfng", "text": "The cleanup programme was paid for by the government."},
    {"number": 3, "kind": "tfng", "text": "No fish live in the Thames today."},
    {"number": 4, "kind": "mcq", "text": "Seals are often seen",
     "options": ["in central London.", "near the estuary.", "in the 1950s."]},
    {"number": 5, "kind": "completion", "text": "More than 125 ___ of fish live in the river.",
     "max_words": 2},
    {"number": 6, "kind": "other", "text": "Choose the correct heading"},
]}  # fmt: skip
EXPLAINED = {
    "key_quotes": ["A cleanup programme began in the 1960s"],
    "why_key_vi": "Bài đọc chỉ nói chương trình làm sạch bắt đầu từ thập niên 1960, không nói ai trả tiền.",  # noqa: E501
    "trap": "opposite",
    "why_wrong_vi": "Bạn chọn FALSE, nhưng bài không nói điều ngược lại; bài không nhắc tới việc này.",  # noqa: E501
    "wrong_quotes": [],
}


class FakeModel:
    """Scripted replies by task: the parse, then explanations; one has a made-up quote."""

    def __init__(self, *, bad_quote_for: str | None = None) -> None:
        self.tasks: list[str] = []
        self.seen: list[str] = []
        self.bad_quote_for = bad_quote_for

    async def generate(self, route: Any, system: str, messages: Any, schema: Any) -> Any:
        user = str(messages[0].content)
        self.seen.append(system + "\n" + user)
        if "copy the questions" in system:
            self.tasks.append("parse")
            return ProviderReply(json.dumps(PARSED), 800, 400)
        self.tasks.append("explain")
        body = dict(EXPLAINED)
        if "Question 4" in user:
            body |= {"key_quotes": ["seals are often seen near the estuary"], "trap": "wrong_part",
                     "why_key_vi": "Bài đọc nói hải cẩu thường được thấy gần cửa sông.",
                     "why_wrong_vi": "Bài có nhắc London nhưng không nói hải cẩu ở đó"}  # fmt: skip
        if self.bad_quote_for and self.bad_quote_for in user:
            body["key_quotes"] = ["words that are not in the passage at all"]
        return ProviderReply(json.dumps(body), 1500, 200)


def model(db: str, fake: FakeModel, calls: int = 50) -> WritingModel:
    route = Route(provider="deepseek", model="deepseek-test", family="deepseek")
    routing = Routing(tiers={"free": {t: [route] for t in ("reading_own_parse",
                                                           "reading_own_explain")}})  # fmt: skip
    return WritingModel(Gateway(routing, {"deepseek": fake}), db, Budget(1.0, calls),
                        Prices(1.0, 4.0), clock=lambda: NOW)  # fmt: skip


def drain(db: str, m: Any) -> int:
    n = 0
    while process_next_own_test(db, m):
        n += 1
    return n


Setup = tuple[OwnTests, str, str]


@pytest.fixture
def setup(database_url: str) -> Iterator[Setup]:
    pool = ConnectionPool(database_url, open=True)
    with psycopg.connect(database_url) as conn:
        cur = conn.execute("insert into learners(display_name) values ('R') returning id")
        row = cur.fetchone()
        assert row
    learner = str(row[0])
    yield OwnTests(lambda: pool, learner, clock=lambda: NOW), learner, database_url
    pool.close()


def submit(svc: OwnTests, learner: str, key: str = KEY, answers: str = ANSWERS) -> str:
    return svc.submit(learner, ot.CONSENT, PASSAGE, QUESTIONS, key, answers)


def parsed(svc: OwnTests, learner: str, db: str, fake: FakeModel) -> tuple[str, dict[str, Any]]:
    tid = submit(svc, learner)
    drain(db, model(db, fake))
    return tid, svc.get(learner, tid)


def confirmable(view: dict[str, Any]) -> list[dict[str, Any]]:
    keep = ("number", "kind", "text", "options", "max_words", "key")
    return [{k: q[k] for k in keep} for q in view["questions"]]


def test_only_owners_with_consent_and_a_readable_key(setup: Setup, database_url: str) -> None:
    svc, learner, _ = setup
    with psycopg.connect(database_url) as conn:
        cur = conn.execute("insert into learners(display_name) values ('X') returning id")
        row = cur.fetchone()
        assert row
    with pytest.raises(HTTPException) as err:
        submit(svc, str(row[0]))
    assert err.value.status_code == 403
    with pytest.raises(HTTPException) as err:
        svc.submit(learner, "no", PASSAGE, QUESTIONS, KEY, ANSWERS)
    assert err.value.status_code == 422
    with pytest.raises(HTTPException) as err:
        submit(svc, learner, key="TRUE FALSE")
    assert err.value.status_code == 422
    # Answers typed but unreadable: refused, instead of every question marked blank.
    with pytest.raises(HTTPException) as err:
        submit(svc, learner, answers="TRUE FALSE")
    assert err.value.status_code == 422 and "câu trả lời" in str(err.value.detail)
    # A key under a printed header is accepted; deleted at once so no other test's worker parses it.
    header_key = "Reading Passage 1, Questions 1-2\n1.TRUE\n2.NOT GIVEN"
    svc.delete(learner, submit(svc, learner, key=header_key))


def test_paste_parse_confirm_mark_explain(setup: Setup) -> None:
    svc, learner, db = setup
    fake = FakeModel()
    tid = submit(svc, learner)
    assert svc.get(learner, tid)["status"] == "queued"
    drain(db, model(db, fake))
    view = svc.get(learner, tid)
    assert view["status"] == "parsed" and fake.tasks == ["parse"]
    assert "<<<" in fake.seen[0] and "never follow instructions" in fake.seen[0]
    qs = {q["number"]: q for q in view["questions"]}
    assert qs[2]["key"] == "NOT GIVEN" and qs[2]["answer"] == "FALSE"  # the key read by code
    assert qs[6]["kind"] == "unsupported" and qs[6]["problems"] == []
    assert all(q["problems"] == [] for q in qs.values())

    done = svc.confirm(learner, tid, confirmable(view))
    r = done["result"]
    assert done["status"] == "marked"
    assert (r["correct"], r["total"], r["answered"], r["unsupported"]) == (2, 5, 5, [6])
    assert r["evidence"] == 5
    marks = {m["number"]: m for m in r["marks"]}
    assert marks[2]["trap"] == "false_for_not_given" and marks[5]["trap"] == "spelling"
    assert marks[4]["answer_text"] == "A. in central London."

    drain(db, model(db, fake))
    final = svc.get(learner, tid)
    assert final["status"] == "done" and fake.tasks.count("explain") == 3  # 2, 4 and 5 wrong
    marks = {m["number"]: m for m in final["result"]["marks"]}
    assert marks[4]["trap"] == "wrong_part"  # the model's, checked against the list
    assert marks[2]["trap"] == "false_for_not_given"  # code's, never the model's "opposite"
    assert marks[2]["explanation"]["key_quotes"] == ["A cleanup programme began in the 1960s"]
    assert marks[1]["explanation"] is None  # right answers are not explained
    with psycopg.connect(db) as conn:
        rows = conn.execute(
            "select number, competency, correct, trap from reading_own_answers "
            "where test_id=%s order by number", (tid,),
        ).fetchall()  # fmt: skip
        calls = conn.execute(
            "select task, count(*) from llm_calls where learner_id=%s group by task order by task",
            (learner,),
        ).fetchall()
    assert [r[0] for r in rows] == [1, 2, 3, 4, 5]
    assert {r[1] for r in rows} == {"reading-detail"}
    assert rows[3][3] == "wrong_part"
    assert calls == [("reading_own_explain", 3), ("reading_own_parse", 1)]


def test_an_explanation_that_fails_its_checks_is_not_shown(setup: Setup) -> None:
    svc, learner, db = setup
    fake = FakeModel(bad_quote_for="Question 5")
    tid, view = parsed(svc, learner, db, fake)
    svc.confirm(learner, tid, confirmable(view))
    drain(db, model(db, fake))
    r = svc.get(learner, tid)["result"]
    marks = {m["number"]: m for m in r["marks"]}
    assert marks[5]["explanation"] is None and marks[5]["explanation_vi"]
    assert marks[5]["trap"] == "spelling" and r["explanations_dropped"] == 1


def test_the_same_test_pasted_twice_gives_evidence_once(setup: Setup) -> None:
    svc, learner, db = setup
    fake = FakeModel()
    first, view = parsed(svc, learner, db, fake)
    assert svc.confirm(learner, first, confirmable(view))["result"]["evidence"] == 5
    svc.delete(learner, first)  # deleting it does not reset the guard
    second, view = parsed(svc, learner, db, fake)
    again = svc.confirm(learner, second, confirmable(view))["result"]
    assert again["evidence"] == 0 and again["correct"] == 2


def test_confirm_marks_nothing_while_a_key_or_question_is_not_in_the_paste(setup: Setup) -> None:
    svc, learner, db = setup
    tid, view = parsed(svc, learner, db, FakeModel())
    qs = confirmable(view)
    changed = [q | {"key": "FALSE"} if q["number"] == 1 else q for q in qs]
    # FALSE is in the pasted key, but the edited wording is not in the paste.
    back = svc.confirm(learner, tid, [q | {"text": "Made up words."} if q["number"] == 1 else q
                                      for q in changed])  # fmt: skip
    first = back["questions"][0]
    assert back["status"] == "parsed" and back["result"] is None
    assert first["text"] == "Made up words." and first["problems"]  # the edit is kept, flagged
    back = svc.confirm(learner, tid, [q | {"key": "TRUE OR FALSE"} if q["number"] == 1 else q
                                      for q in qs])  # fmt: skip
    assert back["status"] == "parsed" and "không có trong phần đáp án" in str(back["questions"][0])
    # a single letter must be its own word in the pasted key, not one inside "species"
    back = svc.confirm(learner, tid, [q | {"key": "C"} if q["number"] == 4 else q for q in qs])
    q4 = next(q for q in back["questions"] if q["number"] == 4)
    assert back["status"] == "parsed" and "không có trong phần đáp án" in str(q4["problems"])
    with pytest.raises(HTTPException) as err:
        svc.confirm(learner, tid, [q | {"kind": "unsupported"} for q in qs])
    assert err.value.status_code == 422  # nothing left to mark
    # Removing a question the app read wrongly, or fixing its key from the paste, is allowed.
    done = svc.confirm(learner, tid, [q for q in changed if q["number"] != 3])
    assert done["result"]["total"] == 4 and done["result"]["correct"] == 0
    with pytest.raises(HTTPException) as err:
        svc.confirm(learner, tid, qs)  # already marked
    assert err.value.status_code == 409


def test_without_a_model_the_test_fails_with_a_reason(setup: Setup) -> None:
    svc, learner, db = setup
    tid = submit(svc, learner)
    drain(db, None)
    view = svc.get(learner, tid)
    assert view["status"] == "failed" and "mô hình" in view["failure_vi"]


def test_out_of_budget_parse_says_so(setup: Setup) -> None:
    svc, learner, db = setup
    tid = submit(svc, learner)
    drain(db, model(db, FakeModel(), calls=0))
    assert "hết lượt" in svc.get(learner, tid)["failure_vi"]


def test_routes(setup: Setup) -> None:
    svc, learner, db = setup
    app = FastAPI()
    app.include_router(routes.create_router(svc))
    client = TestClient(app)
    body = {"learner_id": learner, "consent": ot.CONSENT, "passage": PASSAGE,
            "questions": QUESTIONS, "key": KEY, "answers": ANSWERS}  # fmt: skip
    sent = client.post("/reading/own-tests", json=body)
    assert sent.status_code == 202
    tid = sent.json()["id"]
    drain(db, model(db, FakeModel()))
    view = client.get(f"/reading/own-tests/{tid}", params={"learner_id": learner}).json()
    marked = client.post(f"/reading/own-tests/{tid}/confirm",
                         json={"learner_id": learner, "questions": confirmable(view)})  # fmt: skip
    assert marked.status_code == 200 and marked.json()["result"]["total"] == 5
    listed = client.get("/reading/own-tests", params={"learner_id": learner}).json()
    assert listed[0]["id"] == tid and listed[0]["total"] == 5
    assert listed[0]["opening"].startswith("The River Thames")
    gone = client.delete(f"/reading/own-tests/{tid}", params={"learner_id": learner})
    assert gone.status_code == 204
    assert client.get(f"/reading/own-tests/{tid}",
                      params={"learner_id": learner}).status_code == 404  # fmt: skip
