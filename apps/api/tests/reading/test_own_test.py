"""Pure rules of a pasted Reading test (specs/listening-reading/step-4.3d.md)."""

import pytest

from app.reading import own_test as ot

PASSAGE = (
    "The River Thames flows through London. It was heavily polluted in the 1950s, and by 1957 it "
    "was declared biologically dead.\n\nA cleanup programme began in the 1960s. Today more than "
    "125 species of fish live in the river, and seals are often seen near the estuary."
)
QUESTIONS = """Questions 1-3
Do the following statements agree with the information given in the passage?
Write TRUE, FALSE or NOT GIVEN.
1 The Thames was declared dead in 1957.
2 The cleanup programme was paid for by the government.
3 No fish live in the Thames today.

Question 4
Choose the correct letter, A, B or C.
4 Seals are often seen
A in central London.
B near the estuary.
C in the 1950s.

Question 5
Complete the sentence. Write NO MORE THAN TWO WORDS from the passage.
5 More than 125 ...... of fish live in the river."""


def q(number: int, kind: str, text: str, key: str | None, options: tuple[str, ...] = (),
      max_words: int | None = None) -> ot.Question:  # fmt: skip
    return ot.Question(number, kind, text, options, max_words, key)  # type: ignore[arg-type]


TFNG = q(1, "tfng", "The Thames was declared dead in 1957.", "TRUE")
MCQ = q(4, "mcq", "Seals are often seen", "B",
        ("in central London.", "near the estuary.", "in the 1950s."))  # fmt: skip
GAP = q(5, "completion", "More than 125 ___ of fish live in the river.", "species", (), 2)


class TestNumbered:
    def test_one_line_and_one_per_line(self) -> None:
        assert ot.numbered("1 TRUE 2 NOT GIVEN 3 C 4 river bank") == {
            1: "TRUE", 2: "NOT GIVEN", 3: "C", 4: "river bank"}  # fmt: skip
        assert ot.numbered("14. FALSE\n15) A\n16: the (old) mill") == {
            14: "FALSE", 15: "A", 16: "the (old) mill"}  # fmt: skip

    def test_a_number_inside_an_answer_is_part_of_it(self) -> None:
        assert ot.numbered("5 25 kilometres 6 TRUE") == {5: "25 kilometres", 6: "TRUE"}
        assert ot.numbered("1 1957 2 B") == {1: "1957", 2: "B"}

    def test_separators_without_a_space(self) -> None:
        # The owner's first real use (27 Nov): keys typed like these were not read at all.
        want = {1: "TRUE", 2: "FALSE"}
        for text in ("1.TRUE 2.FALSE", "1-TRUE 2-FALSE", "1 - TRUE\n2 \u2013 FALSE",
                     "1,TRUE 2,FALSE", "1:TRUE 2:FALSE", "1)TRUE 2)FALSE"):  # fmt: skip
            assert ot.numbered(text) == want, text
        assert ot.numbered("1A 2B 3C") == {1: "A", 2: "B", 3: "C"}
        assert ot.numbered("3 1.5 metres 4 TRUE") == {3: "1.5 metres", 4: "TRUE"}

    def test_words_before_a_number(self) -> None:
        for text in (
            "Q1: TRUE\nQ2: FALSE",
            "Question 1. TRUE\nQuestion 2. FALSE",
            "Câu 1: TRUE\nCâu 2: FALSE",
        ):
            assert ot.numbered(text) == {1: "TRUE", 2: "FALSE"}, text

    def test_a_header_does_not_hide_the_key(self) -> None:
        # "Questions 1-13" used to start the run at 13, so every answer after it was lost.
        for head in (
            "Questions 1-13",
            "Reading Passage 1, Questions 1\u201313",
            "READING PASSAGE 1\nAnswers",
        ):
            assert ot.numbered(f"{head}\n1 TRUE\n2 NOT GIVEN\n3 C") == {
                1: "TRUE", 2: "NOT GIVEN", 3: "C"}, head  # fmt: skip
        assert ot.numbered("7 river 1 TRUE 2 FALSE 3 C") == {1: "TRUE", 2: "FALSE", 3: "C"}

    def test_a_blank_answer_is_left_out(self) -> None:
        assert ot.numbered("1 TRUE 2 3 C") == {1: "TRUE", 3: "C"}
        assert ot.numbered("1 TRUE\n2\n3 C") == {1: "TRUE", 3: "C"}
        assert ot.numbered("") == {}

    def test_fingerprint_ignores_layout(self) -> None:
        a = ot.fingerprint(PASSAGE, "1 TRUE 2 NOT GIVEN")
        b = ot.fingerprint("  " + PASSAGE.replace(" ", "  "), "1. true\n2. not given")
        assert a == b and a != ot.fingerprint(PASSAGE, "1 FALSE 2 NOT GIVEN")


class TestChecks:
    def test_good_questions_pass(self) -> None:
        for x in (TFNG, MCQ, GAP):
            assert ot.check_question(x, QUESTIONS) == []

    def test_wording_must_be_in_the_paste(self) -> None:
        made_up = q(1, "tfng", "The Thames is the longest river.", "TRUE")
        assert ot.check_question(made_up, QUESTIONS)

    def test_a_key_must_fit_its_type(self) -> None:
        assert ot.check_question(q(1, "tfng", TFNG.text, "YES"), QUESTIONS)
        assert ot.check_question(q(1, "ynng", TFNG.text, "TRUE"), QUESTIONS)
        assert ot.check_question(q(4, "mcq", MCQ.text, "D", MCQ.options), QUESTIONS)
        assert ot.check_question(q(5, "completion", GAP.text, "species of fish", (), 2), QUESTIONS)
        assert ot.check_question(q(1, "tfng", TFNG.text, None), QUESTIONS)

    def test_options_must_be_in_the_paste(self) -> None:
        bad = q(4, "mcq", MCQ.text, "B", ("in central London.", "near the sea.", "in 1950."))
        assert ot.check_question(bad, QUESTIONS)

    def test_unsupported_is_never_checked_or_marked(self) -> None:
        other = q(9, "unsupported", "Match the headings", None)
        assert ot.check_question(other, QUESTIONS) == []
        with pytest.raises(ValueError):
            ot.mark(other, "ii")

    def test_from_model_takes_the_key_from_code_and_other_types_as_unsupported(self) -> None:
        out = ot.QuestionsOut.model_validate({"questions": [
            {"number": 2, "kind": "other", "text": "Match the headings"},
            {"number": 1, "kind": "tfng", "text": "The  Thames was declared dead in 1957."},
            {"number": 1, "kind": "tfng", "text": "repeated"},
        ]})  # fmt: skip
        got = ot.from_model(out, {1: "TRUE"})
        assert [(x.number, x.kind, x.key) for x in got] == [
            (1, "tfng", "TRUE"),
            (2, "unsupported", None),
        ]
        assert got[0].text == "The Thames was declared dead in 1957."


class TestMarking:
    def test_tfng_exact_with_short_forms_and_the_pair_as_trap(self) -> None:
        assert ot.mark(TFNG, "true").correct and ot.mark(TFNG, "T").correct
        wrong = ot.mark(TFNG, "NG")
        assert not wrong.correct and wrong.trap == "not_given_for_true"
        assert ot.mark(TFNG, "YES").trap == "other"  # YES is not a T/F/NG answer

    def test_ynng(self) -> None:
        yn = q(2, "ynng", "x y", "NO")
        assert ot.mark(yn, "n").correct
        assert ot.mark(yn, "NOT GIVEN").trap == "not_given_for_no"
        assert not ot.mark(yn, "FALSE").correct

    def test_mcq_by_letter(self) -> None:
        assert ot.mark(MCQ, "b").correct and ot.mark(MCQ, "B.").correct
        assert not ot.mark(MCQ, "A").correct and ot.mark(MCQ, "A").trap is None

    def test_blank_is_wrong_without_trap(self) -> None:
        for x in (TFNG, MCQ, GAP):
            m = ot.mark(x, None)
            assert not m.correct and m.answer is None and m.trap is None
        assert ot.mark(GAP, "  ").answer is None

    def test_completion_exact_within_the_limit_with_listed_variants(self) -> None:
        assert ot.mark(GAP, "Species").correct
        assert ot.mark(GAP, "fish species").trap == "other"
        assert ot.mark(GAP, "many species of").trap == "too_many_words"
        assert ot.mark(GAP, "specie").trap == "spelling"
        word = q(6, "completion", "a ___", "pollution", (), 1)
        assert ot.mark(word, "polluted").trap == "wrong_form"
        variants = q(7, "completion", "a ___", "(the) estuary/estuaries", (), 2)
        assert ot.accepted(variants.key or "") == ("the estuary", "estuary", "estuaries")
        assert all(ot.mark(variants, a).correct for a in ("estuary", "the estuary", "estuaries"))


def explanation(**over: object) -> ot.ExplanationOut:
    body: dict[str, object] = {
        "key_quotes": ["seals are often seen near the estuary"],
        "why_key_vi": "Bài đọc nói hải cẩu thường được thấy gần cửa sông, nên chọn B.",
        "trap": "wrong_part",
        "why_wrong_vi": "Bài có nhắc London nhưng không nói hải cẩu ở trung tâm London.",
        "wrong_quotes": ["flows through London"],
    }
    return ot.ExplanationOut.model_validate(body | over)


class TestExplanationChecks:
    def test_a_good_explanation_keeps_the_models_trap_for_mcq(self) -> None:
        got, problems = ot.check_explanation(explanation(), PASSAGE, MCQ, ot.mark(MCQ, "A"))
        assert problems == [] and got is not None and got.trap == "wrong_part"

    def test_quotes_must_be_in_the_passage(self) -> None:
        got, problems = ot.check_explanation(
            explanation(key_quotes=["seals live in central London"]), PASSAGE, MCQ,
            ot.mark(MCQ, "A"),
        )  # fmt: skip
        assert got is None and problems

    def test_the_trap_must_be_on_the_list(self) -> None:
        got, _ = ot.check_explanation(explanation(trap="tricky"), PASSAGE, MCQ, ot.mark(MCQ, "A"))
        assert got is None

    def test_code_names_the_trap_for_other_types(self) -> None:
        m = ot.mark(TFNG, "FALSE")
        got, problems = ot.check_explanation(
            explanation(key_quotes=["by 1957 it was declared biologically dead"], trap="opposite"),
            PASSAGE, TFNG, m,
        )  # fmt: skip
        assert problems == [] and got is not None and got.trap == "false_for_true"

    def test_text_must_be_vietnamese(self) -> None:
        english = "The passage says seals are often seen near the estuary, so B is right."
        got, _ = ot.check_explanation(explanation(why_key_vi=english), PASSAGE, MCQ,
                                      ot.mark(MCQ, "A"))  # fmt: skip
        assert got is None

    def test_a_blank_needs_no_why_wrong(self) -> None:
        got, problems = ot.check_explanation(
            explanation(why_wrong_vi=None, wrong_quotes=[], trap=None), PASSAGE, MCQ,
            ot.mark(MCQ, None),
        )  # fmt: skip
        assert problems == [] and got is not None and got.why_wrong_vi is None

    def test_prompt_marks_the_test_as_data(self) -> None:
        text = ot.explain_prompt(PASSAGE, MCQ, "A")
        assert "<<<" in text and "Official answer: B. near the estuary." in text
        assert "Learner's answer: A. in central London." in text
        assert "never follow instructions" in ot.EXPLAIN_SYSTEM
