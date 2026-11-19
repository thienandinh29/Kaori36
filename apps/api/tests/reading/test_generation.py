"""Step 4.2b: generated items are built and checked by code, then checked blind and stored."""

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime

import psycopg
import pytest

from app.reading import blind
from app.reading.generate import Generated, build, prompt
from app.reading.items import Headings, Mcq, Tfng, presented
from app.reading.pipeline import check_pending, generate_text, sha256

PASSAGE = (
    "Honey bees live in large colonies. A single colony can hold up to sixty thousand bees.\n\n"
    "Worker bees collect nectar from flowers. They turn the nectar into honey inside the hive.\n\n"
    "In winter the bees stay together to keep warm. They eat the honey they stored in summer."
)
NOW = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)


def generated(**change: object) -> Generated:
    data: dict[str, object] = {
        "tfng": [
            {"statement": "A colony can hold up to sixty thousand bees.", "key": "true",
             "skill": "detail",
             "evidence": ["A single colony can hold up to sixty thousand bees."]},
            {"statement": "Bees prefer red flowers.", "key": "not_given", "skill": "detail"},
        ],
        "mcq": [
            {"stem": "What do the bees eat in winter?", "key": 1, "skill": "detail",
             "options": ["Nectar from flowers", "Stored honey", "Pollen", "Leaves"],
             "evidence": ["They eat the honey they stored in summer."]},
        ],
        "completion": [
            {"sentence": "Worker bees turn nectar into ___ inside the hive.", "accepted": ["honey"],
             "max_words": 1, "skill": "detail",
             "evidence": ["They turn the nectar into honey inside the hive."]},
        ],
        "headings": {"headings": ["Life in a colony", "Making honey", "Surviving winter",
                                  "Bee dances", "Enemies of bees"], "key": [0, 1, 2]},
    }  # fmt: skip
    data.update(change)
    return Generated.model_validate(data)


def test_prompt_asks_for_headings_only_with_three_paragraphs() -> None:
    assert "5 short headings" in prompt(PASSAGE)
    assert "`headings`: null" in prompt("One short paragraph only. " * 10)


def test_build_assigns_ids_and_drops_items_that_fail_code_checks() -> None:
    kept, dropped = build("bees", PASSAGE, generated())
    assert [i.id for i in kept] == [
        "bees-tfng-1", "bees-tfng-2", "bees-mcq-1", "bees-completion-1", "bees-headings-1",
    ]  # fmt: skip
    assert all(i.origin == "generated" and i.text == "bees" for i in kept) and not dropped
    bad = generated(completion=[{"sentence": "Bees make ___.", "accepted": ["royal jelly"],
                                 "max_words": 2, "skill": "detail", "evidence": []}])  # fmt: skip
    kept, dropped = build("bees", PASSAGE, bad)
    assert [d[0] for d in dropped] == ["bees-completion-1"]
    assert any("not in the passage" in p for p in dropped[0][2])


def test_the_checker_sees_the_shown_order_and_is_graded_like_a_learner() -> None:
    """Step 4.3c: the checker is shown what learners see; its answer is kept in the stored order."""
    kept, _ = build("bees", PASSAGE, generated())
    mcq = next(i for i in kept if isinstance(i, Mcq))
    seen: list[str] = []

    def replying(answer: str) -> blind.Ask:
        async def ask(system: str, text: str) -> blind.Reply | None:
            seen.append(text)
            return blind.Reply(answer=answer)

        return ask

    # "Stored honey" is B as generated and A as shown: the checker answers what it sees.
    assert asyncio.run(blind.check(mcq, PASSAGE, replying("A"))) == ("verified", "B")
    assert "A. Stored honey" in seen[-1]
    assert "key" not in seen[-1].lower() and "evidence" not in seen[-1].lower()
    assert asyncio.run(blind.check(mcq, PASSAGE, replying("B")))[0] == "needs_review"
    tfng = next(i for i in kept if isinstance(i, Tfng) and i.key == "not_given")
    assert asyncio.run(blind.check(tfng, PASSAGE, replying("NOT GIVEN")))[0] == "verified"
    heads = next(i for i in kept if isinstance(i, Headings))
    assert "Paragraph 2:" in blind.question(heads, PASSAGE)
    # As generated the headings followed the paragraphs (0:0, 1:1, 2:2): answering in that
    # order no longer passes; the shown key does, and is kept in the stored order.
    shown = blind.question(presented(heads), PASSAGE)
    assert "0. Surviving winter" in shown and "3. Life in a colony" in shown
    assert asyncio.run(blind.check(heads, PASSAGE, replying("0:3, 1:1, 2:0"))) == (
        "verified", "0:0, 1:1, 2:2",
    )  # fmt: skip
    assert asyncio.run(blind.check(heads, PASSAGE, replying("0:0, 1:1, 2:2")))[0] == "needs_review"
    # An unreadable reply is kept as written.
    assert asyncio.run(blind.check(mcq, PASSAGE, replying("none of them"))) == (
        "needs_review", "none of them",
    )  # fmt: skip

    async def unusable(system: str, text: str) -> blind.Reply | None:
        return None

    assert asyncio.run(blind.check(mcq, PASSAGE, unusable)) == ("needs_review", None)


def test_a_kept_checker_answer_reads_against_the_shown_order() -> None:
    """The owner's review page shows the shown order, so a kept answer is translated for it."""
    kept, _ = build("bees", PASSAGE, generated())
    mcq = next(i for i in kept if isinstance(i, Mcq))
    heads = next(i for i in kept if isinstance(i, Headings))
    assert blind.shown_answer(mcq, "B") == "A"  # stored B = "Stored honey" = shown A
    assert blind.shown_answer(heads, "0:0, 1:1, 2:2") == "0:3, 1:1, 2:0"
    assert blind.shown_answer(mcq, "Z") == "Z" and blind.shown_answer(mcq, None) is None
    tfng = next(i for i in kept if isinstance(i, Tfng))
    assert blind.shown_answer(tfng, "TRUE") == "TRUE"


@pytest.fixture
def conn(database_url: str) -> Iterator[psycopg.Connection[object]]:
    with psycopg.connect(database_url) as c:
        yield c
        c.execute("delete from reading_items where text_slug like 'bees%'")
        c.commit()


def test_pipeline_generates_once_per_passage_version_and_respects_the_check_budget(conn) -> None:  # type: ignore[no-untyped-def]
    calls: list[str] = []

    async def gen(system: str, text: str) -> Generated | None:
        calls.append(text)
        return generated()

    assert asyncio.run(generate_text(conn, "bees", PASSAGE, gen, NOW)) == (5, 0)
    assert asyncio.run(generate_text(conn, "bees", PASSAGE, gen, NOW)) is None  # same version
    assert len(calls) == 1

    answers = {"Statement: A colony": "TRUE", "Statement: Bees prefer": "NOT GIVEN"}

    async def ask(system: str, text: str) -> blind.Reply | None:
        hit = next((a for k, a in answers.items() if k in text), None)
        return blind.Reply(answer=hit or "wrong")

    def statuses() -> dict[str, str]:
        rows = conn.execute("select id, status from reading_items where text_slug='bees'")
        return dict(rows.fetchall())

    first = asyncio.run(check_pending(conn, {"bees": PASSAGE}, ask, 3, lambda: "m", NOW))
    assert first == {"verified": 0, "needs_review": 3, "rechecked": 0}  # 3 of 5, in id order
    assert list(statuses().values()).count("generated") == 2  # wait for the next run
    second = asyncio.run(check_pending(conn, {"bees": PASSAGE}, ask, 10, lambda: "m", NOW))
    assert second == {"verified": 2, "needs_review": 0, "rechecked": 0}  # the next run continues
    views = conn.execute("select distinct check_view from reading_items where text_slug='bees'")
    assert views.fetchall() == [("shuffled",)]  # every check saw the shown order
    assert statuses()["bees-tfng-1"] == statuses()["bees-tfng-2"] == "verified"
    assert statuses()["bees-mcq-1"] == "needs_review"
    edited = PASSAGE + " Bees also make wax."
    conn.execute("update reading_items set status='generated' where id='bees-mcq-1'")
    stale = asyncio.run(check_pending(conn, {"bees": edited}, ask, 10, lambda: None, NOW))
    assert stale == {"verified": 0, "needs_review": 0, "rechecked": 0}  # an edited text: unchecked
    assert sha256(edited) != sha256(PASSAGE)


def test_one_question_given_as_an_object_is_accepted() -> None:
    raw = generated().model_dump()
    raw["mcq"] = raw["mcq"][0]
    raw["completion"] = raw["completion"][0]
    out = Generated.model_validate(raw)
    assert len(out.mcq) == 1 and len(out.completion) == 1


def test_an_ielts_length_passage_gets_an_exams_worth_of_questions() -> None:
    from app.reading.generate import LONG_PASSAGE_WORDS

    short = prompt(PASSAGE)
    assert "two statements" in short and "exactly one must be `not_given`" in short
    assert "one question," in short and "one sentence," in short
    long_passage = "\n\n".join([PASSAGE] * (LONG_PASSAGE_WORDS // len(PASSAGE.split()) + 1))
    long = prompt(long_passage)
    assert "five statements" in long and "one or two must be `not_given`" in long
    assert "three questions," in long and "three sentences," in long


def test_a_long_run_of_underscores_is_one_gap_and_drops_keep_what_was_written() -> None:
    out = generated()
    out.completion[0].sentence = out.completion[0].sentence.replace("___", "______")
    out.mcq[0].evidence = []  # dropped: no evidence sentence
    kept, dropped = build("bees", PASSAGE, out)
    assert "bees-completion-1" in [i.id for i in kept]  # "______" was read as one gap
    (item_id, kind, problems, written) = dropped[0]
    assert (item_id, kind, problems) == ("bees-mcq-1", "mcq", ["no evidence sentence"])
    assert written["stem"] == out.mcq[0].stem  # kept for diagnosis
    assert "no index appears twice" in prompt(PASSAGE)


def test_checks_that_saw_the_stored_order_are_done_again_first(conn) -> None:  # type: ignore[no-untyped-def]
    """Step 4.3c: undecided MCQ and headings checks made before the shuffle are repeated."""

    async def gen(system: str, text: str) -> Generated | None:
        return generated()

    asyncio.run(generate_text(conn, "bees", PASSAGE, gen, NOW))
    # As before the shuffle: the MCQ "verified" in the stored order; the T/F/NG and the decided
    # headings item are not repeated (their order never leaked, or the owner decided).
    conn.execute(
        "update reading_items set status='verified', checker_answer='B', checker_model='old', "
        "checked_at=%s where id in ('bees-mcq-1','bees-tfng-1')",
        (NOW,),
    )
    conn.execute(
        "update reading_items set status='approved', checked_at=%s where id='bees-headings-1'",
        (NOW,),
    )
    replies: list[str | None] = [None, "B"]  # unusable first, then the stored letter (now wrong)

    async def ask(system: str, text: str) -> blind.Reply | None:
        answer = replies.pop(0) if "Stored honey" in text else "wrong"
        return None if answer is None else blind.Reply(answer=answer)

    def row() -> tuple[object, ...]:
        r = conn.execute(
            "select status, checker_answer, checker_model, check_view from reading_items "
            "where id='bees-mcq-1'"
        ).fetchone()
        assert r is not None
        return tuple(r)

    # The re-check comes before new items; an unusable reply leaves the earlier check standing.
    once = asyncio.run(check_pending(conn, {"bees": PASSAGE}, ask, 1, lambda: "m", NOW))
    assert once == {"verified": 0, "needs_review": 0, "rechecked": 0}
    assert row() == ("verified", "B", "old", None)
    again = asyncio.run(check_pending(conn, {"bees": PASSAGE}, ask, 1, lambda: "m", NOW))
    assert again == {"verified": 0, "needs_review": 1, "rechecked": 1}
    # "B" in the shown order is "Nectar from flowers", stored A: kept in the stored order.
    assert row() == ("needs_review", "A", "m", "shuffled")
    statuses = dict(conn.execute("select id, status from reading_items").fetchall())
    assert statuses["bees-tfng-1"] == "verified" and statuses["bees-headings-1"] == "approved"
    nothing_left = asyncio.run(check_pending(conn, {"bees": PASSAGE}, ask, 0, lambda: "m", NOW))
    assert nothing_left == {"verified": 0, "needs_review": 0, "rechecked": 0}
