import pytest
from pydantic import TypeAdapter, ValidationError

from app.reading.items import (
    Completion,
    Headings,
    Item,
    Mcq,
    Tfng,
    check,
    grade,
    learner_view,
    servable,
)

PASSAGE = (
    "The town of Riverside was founded in 1820 by farmers from the north.\n\n"
    "Its bridge, built from local stone, took eleven years to finish. "
    "Today the bridge carries about 4,000 cars a day.\n\n"
    "Most visitors come in summer, when the river festival is held."
)
BASE = {"text": "riverside", "skill": "detail"}


def tfng(**over: object) -> Tfng:
    data = {**BASE, "id": "t1", "statement": "The bridge took eleven years to build.",
            "key": "true", "evidence": ["took eleven years to finish"]}  # fmt: skip
    return Tfng.model_validate({**data, **over})


def completion(**over: object) -> Completion:
    data = {**BASE, "id": "c1", "sentence": "The bridge was built from local ___.",
            "accepted": ["stone"], "max_words": 1,
            "evidence": ["Its bridge, built from local stone, took eleven years"]}  # fmt: skip
    return Completion.model_validate({**data, **over})


def mcq(**over: object) -> Mcq:
    data = {**BASE, "id": "m1", "stem": "When do most visitors come?",
            "options": ["In winter", "In summer", "In spring"], "key": 1,
            "evidence": ["Most visitors come in summer"]}  # fmt: skip
    return Mcq.model_validate({**data, **over})


def headings(**over: object) -> Headings:
    data = {**BASE, "id": "h1", "skill": "main_idea",
            "headings": ["How it began", "A long building project", "Festival season", "Trade"],
            "key": {0: 0, 1: 1, 2: 2}}  # fmt: skip
    return Headings.model_validate({**data, **over})


def test_valid_items_pass_every_check() -> None:
    for item in (tfng(), completion(), mcq(), headings()):
        assert check(item, PASSAGE) == [], item.id


def test_evidence_must_be_in_the_passage_and_present() -> None:
    assert "evidence not in" in check(tfng(evidence=["took twelve years"]), PASSAGE)[0]
    assert check(tfng(evidence=[]), PASSAGE) == ["no evidence sentence"]
    assert check(tfng(key="not_given", evidence=[]), PASSAGE) == []  # nothing to point at
    curly = tfng(evidence=["Its  bridge, built from\nlocal stone"])
    assert check(curly, PASSAGE) == []  # whitespace normalised


def test_completion_checks() -> None:
    assert any("longer than" in p for p in check(completion(accepted=["local stone"]), PASSAGE))
    assert any("not in the passage" in p for p in check(completion(accepted=["wood"]), PASSAGE))
    off = completion(evidence=["Most visitors come in summer"])
    assert any("not in the evidence" in p for p in check(off, PASSAGE))
    leak = completion(sentence="The stone bridge was built from local ___.")
    assert any("already contains" in p for p in check(leak, PASSAGE))
    with pytest.raises(ValidationError):
        completion(sentence="No blank here.")


def test_mcq_checks() -> None:
    assert "not distinct" in check(mcq(options=["In summer", "in summer", "Never"]), PASSAGE)[0]
    leak = mcq(stem="Do most visitors come in summer or at another time?")
    assert "the stem contains the key option" in check(leak, PASSAGE)
    with pytest.raises(ValidationError):
        mcq(key=3)


def test_headings_checks() -> None:
    assert any("does not exist" in p for p in check(headings(key={0: 0, 5: 1}), PASSAGE))
    assert "two paragraphs share a heading" in check(headings(key={0: 1, 1: 1}), PASSAGE)
    with pytest.raises(ValidationError):
        headings(headings=["A", "B", "C"])  # not more headings than paragraphs


def test_grading_from_the_key() -> None:
    for answer in ("True", "T", " true "):
        assert grade(tfng(), answer) == 1.0
    assert grade(tfng(key="not_given", evidence=[]), "NG") == 1.0
    assert grade(tfng(key="not_given", evidence=[]), "not-given") == 1.0
    assert grade(tfng(), "false") == 0.0 and grade(tfng(), "maybe") == 0.0
    assert grade(mcq(), 1) == 1.0 and grade(mcq(), 0) == 0.0
    assert grade(mcq(), True) == 0.0 and grade(mcq(), "1") == 0.0
    assert grade(completion(), " Stone ") == 1.0
    assert grade(completion(), "stoen") == 0.0  # a misspelling is wrong
    assert grade(completion(accepted=["stone"], max_words=1), "local stone") == 0.0
    assert grade(headings(), {0: 0, 1: 1, 2: 3}) == pytest.approx(2 / 3)
    assert grade(headings(), "nope") == 0.0


def test_learner_view_leaks_nothing() -> None:
    for item in (tfng(), completion(), mcq(), headings()):
        view = learner_view(item)
        assert not {"key", "accepted", "evidence", "status", "origin"} & view.keys()
    assert "stone" not in str(learner_view(completion()))


def test_only_approved_items_that_pass_are_servable() -> None:
    assert not servable(tfng(), PASSAGE)  # draft
    assert not servable(tfng(status="verified"), PASSAGE)  # verified but not reviewed
    assert servable(tfng(status="approved"), PASSAGE)
    assert not servable(tfng(status="approved", evidence=["not there"]), PASSAGE)


def test_items_parse_by_kind() -> None:
    adapter: TypeAdapter[Tfng | Mcq | Completion | Headings] = TypeAdapter(Item)
    parsed = adapter.validate_python({**BASE, "kind": "mcq", "id": "x", "stem": "Which one is it?",
                                      "options": ["a b", "c d", "e f"], "key": 0})  # fmt: skip
    assert isinstance(parsed, Mcq)
