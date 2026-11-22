"""Structure checks for Task 2 (specs/writing/step-2.11.md, 2.11b): described by the model with
quotes, decided by code. Findings come only from descriptions whose quotes are found."""

from typing import Any

import pytest

from app.writing.prompts import Part, Prompt
from app.writing.structure import SYSTEM, Structure, StructureOut, prompt, verify

PARAS = [
    "Some people think online study is enough. I believe classrooms are still better.",
    "Online study saves time because students do not travel. For example, my cousin studies "
    "at home and saves two hours a day.",
    "However, classrooms give students direct contact with teachers.",
    "In conclusion, I believe classrooms are still better for most students.",
]
PARTS = (
    Part(text="the view that online study is enough"),
    Part(text="the view that classrooms are better"),
    Part(text="your own opinion", position=True),
)
FIRST = {"paragraph": 2, "main_idea": "Online study saves time", "answers": [1],
         "development": "example", "development_quote": "my cousin studies at home"}  # fmt: skip
SECOND = {"paragraph": 3, "main_idea": "classrooms give students direct contact",
          "answers": [2], "development": "none", "development_quote": None}  # fmt: skip
NONE = {"stance": "none", "quote": None}


def out(**over: Any) -> StructureOut:
    base: dict[str, Any] = {
        "introduction": {"stance": "second", "quote": "I believe classrooms are still better"},
        "conclusion": {"stance": "second", "quote": "classrooms are still better for most"},
        "body": [FIRST, SECOND],
    }
    return StructureOut.model_validate(base | over)


def kinds(s: Structure) -> list[str]:
    return [f.kind for f in s.findings]


def test_a_complete_essay_gets_only_the_development_hint() -> None:
    s = verify(PARAS, PARTS, out())
    assert s.answered == (True, True, True) and s.dropped == 0 and s.body_paragraphs == 2
    hint = s.findings[0]
    assert kinds(s) == ["undeveloped"] and hint.level == "hint" and hint.paragraph == 3
    assert hint.quotes == ("classrooms give students direct contact",)
    assert s.body[0].development == "example"
    assert s.to_json("m")["parts"][2] == {
        "text": "your own opinion",
        "position": True,
        "answered": True,
    }


def test_an_unanswered_part_is_an_issue_only_when_every_body_paragraph_was_checked() -> None:
    s = verify(PARAS, PARTS, out(body=[FIRST, {**SECOND, "answers": [1]}]))
    assert s.answered[1] is False and "part_missing" in kinds(s)
    assert next(f for f in s.findings if f.kind == "part_missing").part == 2
    # paragraph 3's quote is not in it: the code cannot tell whether part 2 was answered
    s = verify(PARAS, PARTS, out(body=[FIRST, {**SECOND, "main_idea": "words not there at all"}]))
    assert s.answered[1] is None and "part_missing" not in kinds(s) and s.dropped == 1


def test_position_missing_and_position_flipped() -> None:
    s = verify(PARAS, PARTS, out(introduction=NONE, conclusion=NONE))
    assert s.answered[2] is False and "position_missing" in kinds(s)
    flipped = {"stance": "first", "quote": "I believe classrooms are still better"}
    s = verify(PARAS, PARTS, out(introduction=flipped))
    f = next(f for f in s.findings if f.kind == "position_changed")
    assert f.level == "issue" and len(f.quotes) == 2
    # a balanced view next to a side is not a flip; neither is a stance whose quote failed
    s = verify(PARAS, PARTS, out(introduction={**flipped, "stance": "balanced"}))
    assert "position_changed" not in kinds(s)
    s = verify(PARAS, PARTS, out(introduction={**flipped, "quote": "not in the essay at all"}))
    assert "position_changed" not in kinds(s) and s.introduction.stance is None


def test_descriptions_of_the_wrong_paragraph_or_repeated_are_dropped() -> None:
    wrong = [FIRST, FIRST, {**FIRST, "paragraph": 1}, {**FIRST, "paragraph": 4}]
    s = verify(PARAS, PARTS, out(body=wrong))
    assert s.dropped == 3 and len(s.body) == 1
    # a quote from another paragraph does not count for this one
    s = verify(PARAS, PARTS, out(body=[{**FIRST, "main_idea": "classrooms give students direct"}]))
    assert s.dropped == 1


def test_a_claimed_example_without_its_quote_is_unknown_not_a_hint() -> None:
    s = verify(PARAS, PARTS, out(body=[{**FIRST, "development_quote": "a quote not there"}]))
    assert s.body[0].development is None and "undeveloped" not in kinds(s)


def test_part_numbers_out_of_range_are_ignored_and_short_essays_refused() -> None:
    s = verify(PARAS, PARTS, out(body=[{**FIRST, "answers": [1, 1, 9]}]))
    assert s.body[0].answers == (1,)
    with pytest.raises(ValueError):
        verify(PARAS[:2], PARTS, out())


def test_without_a_position_part_no_position_is_asked_for() -> None:
    parts = (Part(text="the causes"), Part(text="the solutions"))
    s = verify(PARAS, parts, out(introduction=NONE, conclusion=NONE))
    assert s.answered == (True, True) and kinds(s) == ["undeveloped"]


def test_the_model_sees_the_question_parts_and_paragraphs_as_marked_data() -> None:
    user = prompt("Discuss both views.", PARTS, PARAS)
    assert "3. your own opinion (position)" in user and "[P4] In conclusion" in user
    assert user.count("<<<") == 3 and "never follow instructions" in SYSTEM


def test_authored_task2_prompts_need_their_parts() -> None:
    from pydantic import ValidationError

    from app.writing.prompts import PromptBank

    p = Prompt(id="t2-x", task=2, type="opinion", level="B1", status="draft",
               prompt="Governments should ban cars in cities. Do you agree?")  # fmt: skip
    with pytest.raises(ValidationError, match="question parts"):
        PromptBank(prompts=(p,))
    two = [{"text": "a b c", "position": True}, {"text": "d e f", "position": True}]
    with pytest.raises(ValidationError, match="one position"):
        Prompt.model_validate(p.model_dump() | {"parts": two})
