"""A simulated run of the whole Reading path on the real bank (no model calls).

Every text in `data/english/texts/` goes through generation (a fake generator that writes
questions from the passage's own sentences, with deliberate defects), the code checks, the blind
check (a fake checker that is sometimes wrong), the item file round trip, the owner's review, the
labels, the practice routes and "Hôm nay". It looks for the errors a real run would hit: items
that cannot be served or graded, paragraph numbering that differs between API and web, keys
leaking to the learner, labels counted twice, stale fingerprints, and (step 4.3c) answers given in
the shown order but graded or kept in another.
"""

import asyncio
import re
from collections import Counter
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg_pool import ConnectionPool
from pydantic import TypeAdapter

from app.api import reading_practice as practice_routes
from app.reading import blind
from app.reading.generate import (
    LONG_PASSAGE_WORDS,
    GenCompletion,
    Generated,
    GenHeadings,
    GenMcq,
    GenTfng,
)
from app.reading.itemfile import export, import_
from app.reading.items import BLANK, Item, presented
from app.reading.pipeline import check_pending, generate_text, sha256
from app.services.grammar import GrammarService
from app.services.reading_practice import ReadingPractice, key_text
from app.services.reading_review import Decision, ReadingReview
from app.services.today import TodayService
from app.sources.candidates import load_candidates
from app.texts.bank import DEFAULT_CANDIDATES, load_bank
from app.validation.cli import backfill
from app.writing.analysis import paragraphs

REPO = Path(__file__).resolve().parents[4]
TEXTS = REPO / "data" / "english" / "texts"
DATA = REPO / "data"
NOW = datetime(2026, 11, 20, 9, 0, tzinfo=UTC)
OWNER = "00000000-0000-4000-8000-00000000a11c"
_ITEM: TypeAdapter[Any] = TypeAdapter(Item)
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def web_paragraphs(passage: str) -> list[str]:
    """`paragraphsOf` in apps/web/lib/reading/practice.ts, line for line."""
    return [p.strip() for p in re.split(r"\n\s*\n", passage) if p.strip()]


def sentences(passage: str) -> list[str]:
    return [s for p in paragraphs(passage) for s in SENTENCE.split(p) if len(s.split()) >= 8]


def fake_output(i: int, passage: str) -> Generated:
    """Questions a generator might write, from the passage's own sentences; some defective."""
    ss = sentences(passage)
    long = len(passage.split()) >= LONG_PASSAGE_WORDS
    n_tf = 5 if long else 2
    tfng = []
    for k in range(n_tf - 1):
        s = ss[(3 * k + i) % len(ss)]
        if k % 2 == 0:
            tfng.append(GenTfng(statement=s, key="true", skill="detail", evidence=[s]))
        else:
            tfng.append(
                GenTfng(statement="It is not true that " + s[0].lower() + s[1:], key="false",
                        skill="detail", evidence=[s])
            )  # fmt: skip
    tfng.append(
        GenTfng(statement="The author visited Vietnam in 2019.", key="not_given", skill="detail")
    )
    mcq, completion = [], []
    for k in range(3 if long else 1):
        s = ss[(5 * k + 2 * i + 1) % len(ss)]
        word = max(re.findall(r"[A-Za-z]{6,}", s), key=len)
        others = [w for w in re.findall(r"[a-z]{7,}", passage) if w.lower() != word.lower()]
        options = [word, *dict.fromkeys(others[k : k + 40 : 13])][:4]
        key = (i + k) % len(options)
        options.insert(key, options.pop(0))
        mcq.append(GenMcq(stem=f"Which word completes: {s.replace(word, '___', 1)}",
                          options=options, key=key, skill="detail", evidence=[s]))  # fmt: skip
        completion.append(GenCompletion(sentence=s.replace(word, BLANK, 1), accepted=[word],
                                        max_words=1, skill="detail", evidence=[s]))  # fmt: skip
    n = len(paragraphs(passage))
    headings = None
    if n >= 3:
        order = [(j * 3 + i) % (n + 2) for j in range(n)]
        if len(set(order)) != n:  # keep it a valid assignment unless a defect asks otherwise
            order = list(range(n))
        names = [f"Heading {h}: " + " ".join(paragraphs(passage)[0].split()[:3]) for h in
                 range(n + 2)]  # fmt: skip
        headings = GenHeadings(headings=names, key=order)
    out = Generated(tfng=tfng, mcq=mcq, completion=completion, headings=headings)
    # Deliberate defects, as a real generator makes them.
    if i % 4 == 0:
        out.tfng[0].evidence = ["A sentence that is not in the passage at all."]
    if i % 5 == 0:
        out.completion[0].sentence = out.completion[0].sentence.replace(BLANK, "")
    if i % 6 == 0 and out.headings is not None and n >= 3:
        out.headings.key[1] = out.headings.key[0]
    return out


@pytest.fixture
def run(database_url: str, tmp_path: Path) -> Iterator[dict[str, Any]]:
    bank = load_bank(TEXTS, load_candidates(DEFAULT_CANDIDATES))
    assert not bank.refused, bank.refused
    passages = {t.entry.slug: t.text for t in bank.texts}
    pool = ConnectionPool(database_url, open=True)
    with pool.connection() as conn:
        conn.execute("delete from reading_answers")
        conn.execute("delete from reading_items")
        conn.execute("delete from labels where content_type='reading_item'")
        learner = conn.execute(
            "insert into learners(id, display_name) values (%s, 'Sim') "
            "on conflict (id) do update set display_name='Sim' returning id::text",
            (OWNER,),
        ).fetchone()
        assert learner is not None
    yield {"pool": pool, "passages": passages, "learner": learner[0], "tmp": tmp_path,
           "url": database_url}  # fmt: skip
    with pool.connection() as conn:
        conn.execute("delete from reading_answers")
        conn.execute("delete from reading_items")
        conn.execute("delete from labels where content_type='reading_item'")
    pool.close()


def test_the_whole_reading_path_on_the_real_bank(run: dict[str, Any]) -> None:
    pool, passages, learner = run["pool"], run["passages"], run["learner"]
    keys: dict[str, Any] = {}

    # 1. API and web number paragraphs the same way (headings answers depend on it).
    for slug, passage in passages.items():
        assert paragraphs(passage) == web_paragraphs(passage), slug

    # 2. Generation and the code checks.
    with pool.connection() as conn:
        for i, (slug, passage) in enumerate(sorted(passages.items())):

            async def gen(system: str, text: str, i: int = i, p: str = passage) -> Generated:
                return fake_output(i, p)

            assert asyncio.run(generate_text(conn, slug, passage, gen, NOW)) is not None
        rows = conn.execute("select id, status, item from reading_items").fetchall()
    status = Counter(r[1] for r in rows)
    assert status["dropped"] > 0 and status["generated"] > 0
    for item_id, s, data in rows:
        if s == "generated":
            keys[item_id] = _ITEM.validate_python(data)

    # 3. The blind check: the fake checker answers from the key of the question it is shown (the
    #    shown order), wrong on about one in seven and unusable on about one in eleven.
    by_question: dict[str, Any] = {}
    for item in keys.values():
        by_question[blind.question(presented(item), passages[item.text])] = item

    async def ask(system: str, text: str) -> blind.Reply | None:
        item = by_question[text]
        shown = presented(item)
        if sum(map(ord, item.id)) % 11 == 0:
            return None  # an unusable reply, as free models give: flagged with no checker answer
        right = key_text(item)
        if shown.kind == "mcq":
            right = "ABCD"[shown.key]
        elif shown.kind == "headings":
            right = ", ".join(f"{p}:{h}" for p, h in shown.key.items())
        elif shown.kind == "completion":
            right = shown.accepted[0]
        wrong = sum(map(ord, item.id)) % 7 == 0
        return blind.Reply(answer="FALSE" if wrong and item.kind == "tfng" else
                           ("Z" if wrong else right))  # fmt: skip

    with pool.connection() as conn:
        counts = asyncio.run(
            check_pending(conn, passages, ask, len(keys), lambda: "sim/checker", NOW)
        )
    assert counts["verified"] + counts["needs_review"] == len(keys)
    assert counts["needs_review"] > 0
    with pool.connection() as conn:
        unanswered = {
            r[0]
            for r in conn.execute(
                "select id from reading_items "
                "where status='needs_review' and checker_answer is null"
            ).fetchall()
        }
    assert unanswered, "the simulation should include unusable checker replies"

    # 4. The item file: export, a fresh database, import; nothing lost or changed.
    with pool.connection() as conn:
        backfill(conn)
        before = conn.execute(
            "select id, status, item, checker_answer from reading_items order by id"
        ).fetchall()
        n = export(conn, {s: ("openstax-reading", p) for s, p in passages.items()}, run["tmp"])
        conn.execute("delete from reading_items")
        conn.execute("delete from labels where content_type='reading_item'")
        assert import_(conn, run["tmp"], passages) == {
            "added": n, "updated": 0, "kept": 0, "stale": 0,
        }  # fmt: skip
        backfill(conn)
        after = conn.execute(
            "select id, status, item, checker_answer from reading_items order by id"
        ).fetchall()
    assert after == before

    # 5. The owner's review: approve every verified item and every other flagged one,
    #    reject the rest; then a second import and backfill (as on the laptop).
    review = ReadingReview(lambda: pool, TEXTS, OWNER, lambda: NOW)
    with pool.connection() as conn:
        pending = conn.execute(
            "select id, status from reading_items where status in ('verified','needs_review') "
            "order by id"
        ).fetchall()
    approved_flagged = set()
    for k, (item_id, s) in enumerate(pending):
        if s == "verified" or k % 2 == 0 or item_id in unanswered:
            review.decide(learner, item_id, Decision(decision="approve"))
            if s == "needs_review":
                approved_flagged.add(item_id)
        else:
            review.decide(learner, item_id, Decision(decision="reject", reason="wrong_key"))
    with pool.connection() as conn:
        import_(conn, run["tmp"], passages)
        backfill(conn)
        backfill(conn)  # safe to rerun
        owner_labels = conn.execute(
            "select content_id, count(*) from labels where content_type='reading_item' "
            "and role='owner_developer' group by 1 having count(*) > 1"
        ).fetchall()
    assert owner_labels == [], f"owner labels counted twice: {owner_labels[:3]}"

    # 6. Practice: only Silver items are served, never a key, every one gradable.
    practice = ReadingPractice(lambda: pool, TEXTS, lambda: NOW)
    app = FastAPI()
    app.include_router(practice_routes.create_router(practice))
    client = TestClient(app)
    listed = client.get("/reading/texts", params={"learner_id": learner}).json()["texts"]
    assert listed, "nothing served after the review"
    served_ids: set[str] = set()
    for t in listed:
        text = client.get(f"/reading/texts/{t['slug']}", params={"learner_id": learner}).json()
        assert text["passage"] == passages[t["slug"]]
        assert sha256(text["passage"]) == sha256(passages[t["slug"]])
        n_paras = len(web_paragraphs(text["passage"]))
        for q in text["items"]:
            assert "key" not in q and "evidence" not in q and "accepted" not in q, q["id"]
            served_ids.add(q["id"])
            shown = presented(keys[q["id"]])  # learners see the shown order
            assert q.get("options") == (list(shown.options) if shown.kind == "mcq" else None)
            assert q.get("headings") == (list(shown.headings) if shown.kind == "headings" else None)
            if q["kind"] == "headings":
                assert all(0 <= p < n_paras for p in q["paragraphs"]), q["id"]
    assert not served_ids & approved_flagged, "an approved but doubted item was served"
    assert unanswered <= approved_flagged  # every one approved by the owner alone ...
    assert not served_ids & unanswered  # ... and none served: the owner never promotes
    for item_id in sorted(served_ids):
        item = keys[item_id]
        shown = presented(item)  # a learner answers what is on the screen
        right: Any
        if shown.kind == "tfng":
            right = {"true": "TRUE", "false": "FALSE", "not_given": "NOT GIVEN"}[shown.key]
            wrong: Any = "TRUE" if right != "TRUE" else "FALSE"
        elif shown.kind == "mcq":
            right, wrong = shown.key, (shown.key + 1) % len(shown.options)
        elif shown.kind == "completion":
            right, wrong = shown.accepted[0], "zzz"
        else:
            right = {str(p): h for p, h in shown.key.items()}
            wrong = {str(p): (h + 1) % len(shown.headings) for p, h in shown.key.items()}
        body = {"learner_id": learner}
        good = client.post(f"/reading/items/{item_id}/answer", json=body | {"answer": right})
        bad = client.post(f"/reading/items/{item_id}/answer", json=body | {"answer": wrong})
        assert good.status_code == 200 and good.json()["correct"] is True, (item_id, good.text)
        assert bad.status_code == 200 and bad.json()["correct"] is False, (item_id, bad.text)
        assert good.json()["key"] == key_text(item)

    # 7. "Hôm nay" and the map see Reading.
    grammar = GrammarService(
        lambda: pool, DATA / "courses", DATA / "items", DATA / "vocabulary", ""
    )
    today = TodayService(grammar, clock=lambda: NOW, reading=practice)
    comps = {c["slug"]: c for s in today.maps(learner)["skills"] for c in s["competencies"]}
    measured = [s for s, c in comps.items() if s.startswith("reading-") and c["evidence"] >= 3]
    assert comps["reading-detail"]["available"] is True and "reading-detail" in measured
    with psycopg.connect(run["url"]) as conn:
        answers = conn.execute("select count(*) from reading_answers").fetchone()
        kept = conn.execute(
            "select item_id, answer from reading_answers where correct order by id"
        ).fetchall()
    assert answers == (2 * len(served_ids),)
    # Every right answer is kept in the stored order: the stored key, whatever was shown.
    for item_id, answer in kept:
        item = keys[item_id]
        if item.kind == "mcq":
            assert answer == item.key, item_id
        elif item.kind == "headings":
            assert {int(p): h for p, h in answer.items()} == item.key, item_id
