"""Step 5.4a (specs/speaking/step-5.4a.md): the authored test files, question ids and limits."""

from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError

from app.speaking.tests import (
    GRACE_SECONDS,
    LONG_TURN_SECONDS,
    PART1_SECONDS,
    SpeakingTest,
    load_tests,
    max_answer_seconds,
    questions,
)

FOLDER = Path(__file__).resolve().parents[4] / "data" / "speaking" / "tests"


def test_the_authored_tests_load_and_are_drafts_until_reviewed() -> None:
    tests = load_tests(FOLDER)
    assert len(tests) >= 5
    for loaded in tests.values():
        t = loaded.test
        assert t.status == "draft"  # a teacher reads a sample before any is "reviewed"
        assert len(t.part1) == 3 and 4 <= len(t.part3.questions) <= 6
        assert len(loaded.sha256) == 64


def test_questions_come_in_the_examiners_order_with_their_limits() -> None:
    t = load_tests(FOLDER)["t01"].test
    qs = questions(t)
    assert [q.id for q in qs[:2]] == ["p1-1-1", "p1-1-2"]
    assert [q.part for q in qs] == sorted(q.part for q in qs)  # Part 1, then 2, then 3
    long = next(q for q in qs if q.id == "p2-long")
    assert long.text == t.part2.task and long.seconds == LONG_TURN_SECONDS == 120
    assert next(q for q in qs if q.id == "p2-closing").text == t.part2.closing
    assert qs[-1].id == f"p3-{len(t.part3.questions)}"
    assert all(q.seconds == PART1_SECONDS for q in qs if q.part == 1)
    assert max_answer_seconds(long) == 120 + GRACE_SECONDS


def _raw() -> dict:  # type: ignore[type-arg]
    return yaml.safe_load((FOLDER / "t01-home-and-journeys.yaml").read_text(encoding="utf-8"))  # type: ignore[no-any-return]


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        (lambda d: d["part1"].pop(), "three Part 1 topics"),
        (lambda d: d["part1"][0]["questions"].__setitem__(0, "Where do you live"), "ends with ?"),
        (lambda d: d["part1"][0]["questions"].__setitem__(0, "Bạn sống ở đâu?"), "plain English"),
        (lambda d: d["part2"]["points"].pop(), "three or four points"),
        (lambda d: d["part3"]["questions"].__delitem__(slice(1, None)), "four to six"),
        (lambda d: d.__setitem__("status", "approved"), "draft or reviewed"),
        (lambda d: d.__setitem__("extra", 1), "no unknown fields"),
    ],
)
def test_a_malformed_test_is_refused(change, reason: str) -> None:  # type: ignore[no-untyped-def]
    data = _raw()
    change(data)
    with pytest.raises(ValidationError):
        SpeakingTest.model_validate(data)


def test_repeated_ids_or_questions_stop_the_load(tmp_path: Path) -> None:
    text = (FOLDER / "t01-home-and-journeys.yaml").read_text(encoding="utf-8")
    (tmp_path / "t01-a.yaml").write_text(text, encoding="utf-8")
    (tmp_path / "t01-b.yaml").write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="repeats"):
        load_tests(tmp_path)
    (tmp_path / "t01-b.yaml").unlink()
    (tmp_path / "t02-x.yaml").write_text(text, encoding="utf-8")  # file name and id disagree
    with pytest.raises(ValueError, match="file name"):
        load_tests(tmp_path)
    (tmp_path / "t02-x.yaml").unlink()
    data = _raw()
    data["part3"]["questions"][0] = data["part1"][0]["questions"][0]
    (tmp_path / "t01-a.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ValueError, match="question repeats"):
        load_tests(tmp_path)


# --- Step 5.4b: guided practice ---


def test_the_time_shrinks_to_three_quarters_then_half_and_a_fourth_try_is_refused() -> None:
    from app.speaking.tests import Question, try_seconds

    part2 = Question("p2-long", 2, "Describe a journey.", 120)
    part3 = Question("p3-1", 3, "Why?", 60)
    part1 = Question("p1-1-1", 1, "Where?", 40)
    assert [try_seconds(part2, n) for n in (1, 2, 3)] == [120, 90, 60]
    assert [try_seconds(part3, n) for n in (1, 2, 3)] == [60, 45, 30]
    assert [try_seconds(part1, n) for n in (1, 2, 3)] == [40, 30, 20]
    assert try_seconds(Question("x", 1, "Q?", 12), 3) == 10  # never under ten seconds
    for bad in (0, 4):
        with pytest.raises(ValueError):
            try_seconds(part2, bad)


def test_every_topic_word_is_in_the_word_list_and_the_words_are_plain() -> None:
    from app.lessons.graded import build_index
    from app.vocabulary.wordlist import load_wordlist

    root = Path(__file__).resolve().parents[4]
    authored = load_wordlist(root / "data" / "vocabulary" / "core-seed.yaml")
    index = build_index(
        root / "data-sa" / "vocabulary" / "forms.yaml", [(w.lemma, w.level) for w in authored.words]
    )
    for loaded in load_tests(FOLDER).values():
        for words in (loaded.test.part2.words, loaded.test.part3.words):
            assert 5 <= len(words) <= 8
            missing = [w for w in words if index.level_of(w) is None]
            assert not missing, f"{loaded.test.id}: not in the word list: {missing}"


@pytest.mark.parametrize("bad", [["Journey", "a", "b", "c", "d"], ["two words", "a", "b", "c", "d"],
                                 ["a", "a", "b", "c", "d"], ["a", "b", "c", "d"]])  # fmt: skip
def test_malformed_topic_words_are_refused(bad: list[str]) -> None:
    data = _raw()
    data["part2"]["words"] = bad
    with pytest.raises(ValidationError):
        SpeakingTest.model_validate(data)
