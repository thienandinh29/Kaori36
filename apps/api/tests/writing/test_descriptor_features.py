"""Features chosen from the band descriptors (specs/writing/step-2.12.md, 2.12b). Pure functions."""

from app.lessons.graded import WordIndex
from app.writing.descriptor_features import (
    CANDIDATES,
    DescriptorFeatures,
    error_free_share,
    errors_per_100_by_kind,
    linking,
    measure,
    mtld,
    prompt_words_per_100,
    word_levels,
)
from app.writing.grammar import Complexity, Issue


def issue(sentence: str, category: str, source: str = "languagetool") -> Issue:
    return Issue(0, sentence, 0, 0, 1, "x", "y", category, "R", "m", None, None, None,
                 source=source)  # fmt: skip


def test_mtld_needs_enough_words_and_rises_with_variety() -> None:
    assert mtld(["word"] * 49) is None
    repetitive = mtld(["the", "cat", "sat"] * 30)
    varied = mtld([f"w{i}" for i in range(60)] + ["the", "cat", "sat"] * 10)
    assert repetitive is not None and varied is not None and varied > repetitive
    assert repetitive < 10  # three words over and over: short runs before the ratio falls


def test_mtld_of_all_distinct_words_is_their_number() -> None:
    assert mtld([f"w{i}" for i in range(80)]) == 80.0


def test_error_kinds_follow_languagetool_and_never_count_the_model() -> None:
    issues = [issue("a", "GRAMMAR"), issue("a", "TYPOS"), issue("b", "GRAMMAR"),
              issue("b", "GRAMMAR", source="llm"), issue("c", "STYLE")]  # fmt: skip
    assert errors_per_100_by_kind(issues, 200) == {"grammar": 1.0, "other": 0.5, "spelling": 0.5}


def test_error_free_share_ignores_spelling_and_counts_repeated_sentences_once_each() -> None:
    sents = ["a", "b", "c", "a"]
    issues = [issue("a", "GRAMMAR"), issue("c", "TYPOS"), issue("b", "GRAMMAR", source="llm")]
    assert error_free_share(sents, issues) == 0.75  # one "a" flagged; spelling and AI aside
    assert error_free_share([], issues) is None


def test_word_levels_keep_unknown_words_apart_from_advanced_ones() -> None:
    index = WordIndex({"study": "A1", "students": "A1", "crucial": "B2", "the": "A1"})
    lv = word_levels("The students study crucial things", index)
    assert (lv.known, lv.beyond_basic, lv.unknown) == (4, 1, 1)
    assert lv.beyond_basic_share == 0.25 and lv.unknown_share == 0.2
    empty = word_levels("", index)
    assert empty.beyond_basic_share is None and empty.unknown_share is None


def test_prompt_words_are_counted_per_100_essay_words() -> None:
    prompt = "Some people think technology makes children lazy."
    assert (
        prompt_words_per_100("Technology helps. Children learn with technology today.", prompt)
        == 42.86
    )


def test_linking_variety_rate_and_overuse() -> None:
    groups = {"addition": ("moreover", "also"), "contrast": ("however",)}
    link = linking("Moreover, it works. Moreover, it is cheap. However, it is slow.", groups)
    # 3 linking words in 11 words; "moreover" is 2 of the 3
    assert link.groups_used == 2 and link.top_share == 0.667 and link.per_100_words == 27.27
    none = linking("It works.", groups)
    assert none.groups_used == 0 and none.top_share is None


def test_measure_fills_every_candidate_feature() -> None:
    text = "Technology helps students.\n\nHowever, it can distract them."
    f = measure(
        text,
        "Does technology help students?",
        issues=[issue("Technology helps students.", "GRAMMAR")],
        sentences=["Technology helps students.", "However, it can distract them."],
        complexity=Complexity(2, 1.5, 0.5),
        index=WordIndex({"technology": "B1", "helps": "A1", "students": "A1"}),
        linking_groups={"contrast": ("however",)},
        own_words=9,
        prompt_overlap=0.5,
    )
    assert isinstance(f, DescriptorFeatures)
    assert f.paragraphs == 2 and f.error_free_sentence_share == 0.5 and f.mtld is None
    assert f.grammar_errors_per_100 == 12.5 and f.linking_groups_used == 1  # 1 error in 8 words
    names = set(f.as_dict())
    for criterion, chosen in CANDIDATES.items():
        assert set(chosen) <= names, criterion
        assert len(chosen) <= 5
