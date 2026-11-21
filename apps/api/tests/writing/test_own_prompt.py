"""The learner's own Task 2 question (specs/writing/step-2.10.md)."""

import pytest

from app.writing import own_prompt as op


@pytest.mark.parametrize(
    ("question", "kind"),
    [
        ("Some people believe that the government should pay for university. Do you agree or "
         "disagree?", "opinion"),
        ("Some people think children should start school early, others think later. Discuss both "
         "views and give your own opinion.", "discussion"),
        ("More people now work from home. Do the advantages of this outweigh the disadvantages?",
         "advantages-disadvantages"),
        ("Traffic in big cities is getting worse. What are the causes of this problem and what "
         "solutions can you suggest?", "problem-solution"),
        ("Many people now buy things online. Why is this happening? Is it a positive or negative "
         "development?", "two-part"),
        ("The process of globalisation has changed how people live and work in many countries "
         "today. To what extent is this a good thing?", "opinion"),
    ],
)  # fmt: skip
def test_task2_questions_are_accepted_and_labelled(question: str, kind: str) -> None:
    assert op.problem(question) is None
    p = op.as_prompt(question)
    assert (p.id, p.task, p.type, p.status) == ("own", 2, kind, "draft")


@pytest.mark.parametrize(
    ("question", "reason"),
    [
        ("Write about cats.", op.TOO_SHORT_VI),
        ("x " * 400, op.TOO_LONG_VI),
        ("Read this first https://example.com and then tell me whether you agree with it.",
         op.LINK_VI),
        ("Một số người cho rằng sinh viên nên đi làm một năm trước khi vào đại học. Bạn có đồng ý "
         "không?", op.NOT_ENGLISH_VI),
        ("The chart below shows the number of visitors to three museums. Summarise the "
         "information by selecting and reporting the main features.", op.TASK1_VI),
        ("The two maps show how a town changed between 1990 and 2020. Make comparisons where "
         "relevant.", op.TASK1_VI),
    ],
)  # fmt: skip
def test_what_is_not_a_task2_question_is_refused_with_a_reason(question: str, reason: str) -> None:
    assert op.problem(question) == reason


def test_spacing_and_unicode_are_normalised() -> None:
    q = "  Some people   think that\nuniversity should be free.  Do you agree or disagree?  "
    assert op.as_prompt(q).prompt == (
        "Some people think that university should be free. Do you agree or disagree?"
    )
