"""Step 2.8: a fix must repair the error; errors repeated across essays."""

from typing import Any

from app.writing.repair import judge
from app.writing.tracker import patterns

SENTENCE = "Plastic bags is cheap for most shoppers."
AT = SENTENCE.index("is")


def test_a_real_fix_goes_to_the_usual_check() -> None:
    assert judge(SENTENCE, AT, AT + 2, "Plastic bags are cheap for most shoppers.") == "check"
    # a different wording keeps the sentence: still the usual rule decides
    assert judge(SENTENCE, AT, AT + 2, "Plastic bags are very cheap for most shoppers.") == "check"


def test_removing_the_error_is_not_a_fix() -> None:
    assert judge(SENTENCE, AT, AT + 2, "Plastic is cheap.") == "deleted"  # "bags" gone
    assert judge(SENTENCE, AT, AT + 2, "Bags.") == "deleted"
    assert judge(SENTENCE, AT, AT + 2, "Plastic bags cheap for most shoppers.") == "check"
    assert judge("Is.", 0, 2, "") == "deleted"
    # a wrong change of the error ("go to" -> "went") is not a deletion: the usual rule decides
    s = "She go to school every day."
    assert judge(s, 4, 6, "She went school every day.") == "check"


def test_leaving_the_error_as_it_was_is_unchanged() -> None:
    assert judge(SENTENCE, AT, AT + 2, "plastic bags is cheap for most people.") == "unchanged"
    missing = "She went to university in Hanoi."  # a missing article: an empty span
    at = missing.index("university")
    assert judge(missing, at, at, "She went to university in Hanoi.") == "unchanged"
    assert judge(missing, at, at, "She went to a university in Hanoi.") == "check"


def issue(node: str | None, sentence: str, source: str = "languagetool") -> dict[str, Any]:
    return {"node": node, "node_vi": f"Nút {node}" if node else None, "errant_type": "R:VERB:SVA",
            "sentence": sentence, "suggestion": "are", "source": source}  # fmt: skip


def essay(*issues: dict[str, Any]) -> dict[str, Any]:
    return {"grammar": {"issues": list(issues)}}


def test_a_pattern_is_an_error_in_two_essays_newest_example_first() -> None:
    results = [  # newest first
        essay(issue("sva", "Bags is cheap."), issue("articles", "I went to university.")),
        essay(issue("sva", "Rivers is dirty."), issue("sva", "Cars is loud.")),
        essay(issue("articles", "She is teacher."), issue("plural", "many informations")),
    ]
    got = patterns(results)
    assert [(p.key, p.essays, p.errors) for p in got] == [("sva", 2, 3), ("articles", 2, 2)]
    sva = next(p for p in got if p.key == "sva")
    assert sva.example == "Bags is cheap." and sva.in_latest and sva.recent == 2
    assert sva.name_vi == "Nút sva"


def test_ai_suggestions_and_one_off_errors_are_never_patterns() -> None:
    results = [
        essay(issue("sva", "a", "llm")),
        essay(issue("sva", "b", "llm")),
        essay(issue("x", "c")),
    ]
    assert patterns(results) == []
    assert patterns([]) == [] and patterns([{"grammar": None}, {}]) == []
