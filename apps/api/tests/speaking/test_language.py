"""Step 5.3a (specs/speaking/step-5.3.md): grammar hints, endings, vocabulary numbers, guard."""

from pathlib import Path
from typing import Any

import errant
import pytest
import spacy

from app.lessons.graded import WordIndex
from app.speaking.language import (
    LanguageStep,
    ending_only,
    hints,
    seconds_of,
    spans,
    vocabulary,
)
from app.writing.error_map import load_error_map
from app.writing.grammar import Issue
from app.writing.languagetool import Match

WRITING = Path(__file__).resolve().parents[4] / "data" / "writing"


def issue(text: str, suggestion: str | None, category: str = "GRAMMAR", start: int = 0) -> Issue:
    return Issue(
        id=0, sentence="s", sentence_start=0, start=start, end=start + len(text), text=text,
        suggestion=suggestion, category=category, rule_id="R", message_en="msg", errant_type=None,
        node=None, explain_vi=None,
    )  # fmt: skip


@pytest.mark.parametrize(
    ("original", "suggestion", "expected"),
    [
        ("cat", "cats", True), ("go", "goes", True), ("walk", "walked", True),
        ("like", "liked", True), ("study", "studies", True), ("study", "studied", True),
        ("go", "went", False),  # an irregular form is a grammar hint, not a missing ending
        ("student", "the student", False), ("a", "an", False), ("cat", "cat", False),
        ("have been", "have beens", False), ("", "s", False), ("cat", None, False),
    ],
)  # fmt: skip
def test_the_ending_rule(original: str, suggestion: str | None, expected: bool) -> None:
    assert ending_only(original, suggestion) is expected


WORDS = [
    {"word": "Um,", "start": 0.5, "end": 0.9},
    {"word": "my", "start": 1.0, "end": 1.2},
    {"word": "sister", "start": 1.2, "end": 1.7},
    {"word": "have", "start": 1.7, "end": 2.0},
    {"word": "two", "start": 2.0, "end": 2.2},
    {"word": "cat.", "start": 2.2, "end": 2.8},
]
TEXT = " ".join(str(w["word"]) for w in WORDS)


def test_offsets_become_the_seconds_of_the_words_they_touch() -> None:
    assert spans(["Um,", "my"]) == [(0, 3), (4, 6)]
    start = TEXT.index("have")
    assert seconds_of(WORDS, start, start + 4) == (1.7, 2.0)
    start = TEXT.index("two cat")
    assert seconds_of(WORDS, start, start + 7) == (2.0, 2.8)  # a span across two words
    assert seconds_of(WORDS, 500, 510) is None


def test_hints_keep_grammar_and_word_choice_and_split_out_endings() -> None:
    found = [
        issue("have", "has", "GRAMMAR", TEXT.index("have")),
        issue("cat", "cats", "GRAMMAR", TEXT.index("cat.")),
        issue("sister", "sistre", "TYPOS", TEXT.index("sister")),  # the recogniser spells
        issue("Um", "um", "CASING", 0),
        issue("cat.", "cat", "PUNCTUATION", TEXT.index("cat.")),
        issue("two", "too", "CONFUSED_WORDS", TEXT.index("two")),
    ]
    out = hints(found, WORDS)
    assert [(h["kind"], h["text"]) for h in out] == [
        ("grammar", "have"), ("word", "two"), ("ending", "cat")
    ]  # fmt: skip
    assert (out[0]["start_s"], out[0]["end_s"]) == (1.7, 2.0)
    assert out[2]["suggestion"] == "cats"
    assert len(hints(found * 5, WORDS)) == 10  # capped


def test_vocabulary_numbers_leave_fillers_out() -> None:
    index = WordIndex({"my": "A1", "sister": "A1", "have": "A1", "two": "A1", "cat": "A1",
                       "ubiquitous": "C1", "um": "A1"})  # fmt: skip
    text = "Um my sister have two cat and ubiquitous cat cat cat uh blorp"
    v = vocabulary(text, index)
    assert v["words"] == 11 and v["mtld"] is None  # under 50 words: no value
    assert v["beyond_b1_share"] == pytest.approx(1 / 9, abs=0.001)  # 9 known tokens, 1 at C1
    assert v["unknown_share"] == pytest.approx(2 / 11, abs=0.001)  # "and" and "blorp"
    assert v["repeated"] == [{"word": "cat", "count": 4}]
    # a word that is common in questions ("people") still counts when the learner leans on it
    many = vocabulary("people like it and people say it and people go and the people", index)
    assert many["repeated"] == [{"word": "people", "count": 4}]


def scripted(text: str) -> list[Match]:
    """A LanguageTool that flags what it finds in the text."""
    rules = [
        ("have", "AGREEMENT", "GRAMMAR", "Use has.", ("has",)),
        ("cat", "PLURAL", "GRAMMAR", "Plural.", ("cats",)),
        ("Um", "CASE", "CASING", "Case.", ("um",)),
    ]
    return [Match(text.index(w), len(w), r, c, m, rep) for w, r, c, m, rep in rules if w in text]


@pytest.fixture(scope="module")
def step() -> LanguageStep:
    nlp = spacy.load("en_core_web_sm")
    index = WordIndex({"my": "A1", "sister": "A1", "have": "A1", "two": "A1", "cat": "A1"})
    return LanguageStep(
        nlp=nlp,
        annotator=errant.load("en", nlp),
        error_map=load_error_map(WRITING / "error-map.yaml"),
        index=index,
        templates=("in this day and age",),
        matches=scripted,
    )


def measures(seconds: float) -> dict[str, Any]:
    return {"speaking_seconds": seconds}


def test_the_whole_check_with_the_real_parser_and_errant(step: LanguageStep) -> None:
    out = step.analyse({"words": WORDS}, "Do you have a sister?", measures(20))
    assert out["skipped"] is None and out["guard"]["templates"] == []
    kinds = {(h["text"], h["kind"]) for h in out["hints"]}
    assert ("have", "grammar") in kinds and ("cat", "ending") in kinds
    assert ("Um", "grammar") not in kinds and len(out["hints"]) == 2  # casing is not a hint
    assert out["vocabulary"]["words"] == 5  # "Um," left out
    assert not {"band", "score", "node", "evidence"} & set(out)
    assert all("node" not in h for h in out["hints"])  # never evidence, never a mastery node


def test_a_short_answer_gets_no_language_feedback(step: LanguageStep) -> None:
    assert step.analyse({"words": WORDS}, "Q?", measures(14.9)) == {"skipped": "short"}
    assert step.analyse({"words": []}, "Q?", measures(30)) == {"skipped": "short"}


def test_without_languagetool_there_are_no_hints_but_the_rest_still_runs(
    step: LanguageStep,
) -> None:
    bare = LanguageStep(step.nlp, step.annotator, step.error_map, step.index, step.templates, None)
    out = bare.analyse({"words": WORDS}, "Do you have a sister?", measures(20))
    assert out["hints"] is None and out["vocabulary"]["words"] == 5


def test_a_memorised_phrase_is_found_and_listed_first(step: LanguageStep) -> None:
    said = [
        {"word": w, "start": i * 0.3, "end": i * 0.3 + 0.2}
        for i, w in enumerate(["In", "this", "day", "and", "age", "many", "people", "travel"])
    ]
    out = step.analyse({"words": said}, "Do you like travel?", measures(20))
    assert out["guard"]["templates"] == ["in this day and age"]
    assert out["guard"]["template_words"] == 5
