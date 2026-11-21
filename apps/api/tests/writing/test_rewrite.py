"""The rewrite's pure rules (specs/writing/step-2.4.md, point 4)."""

from app.writing import rewrite as rw
from app.writing.rewrite import (
    Change,
    ChangeOut,
    attach_reasons,
    diff,
    length_ok,
    sentence_with,
    split_paragraphs,
    target_band,
)

ORIGINAL = "Plastic bags is cheap. They pollute rivers and hurts animals."
REWRITE = "Plastic bags are cheap. However, they pollute rivers and harm wildlife."


def test_the_code_computes_what_changed() -> None:
    assert diff(ORIGINAL, REWRITE) == [
        Change("is", "are"),
        Change("They", "However, they"),
        Change("hurts animals", "harm wildlife"),
    ]
    assert diff(ORIGINAL, ORIGINAL) == []


def test_a_reason_is_kept_only_next_to_a_real_change() -> None:
    claimed = [
        ChangeOut(original="is", revised="are", why_vi="Chủ ngữ số nhiều dùng 'are'."),
        ChangeOut(
            original="hurts animals", revised="harm wildlife", why_vi="'wildlife' trang trọng hơn."
        ),
        ChangeOut(original="cheap", revised="inexpensive", why_vi="Từ này không hề được đổi."),
    ]
    changes, unmatched = attach_reasons(diff(ORIGINAL, REWRITE), claimed)
    assert [c.why_vi for c in changes] == [
        "Chủ ngữ số nhiều dùng 'are'.",
        None,  # the model did not explain "However": shown without a reason
        "'wildlife' trang trọng hơn.",
    ]
    assert unmatched == 1  # "inexpensive" never happened: its reason is dropped


def test_a_rewrite_must_stay_a_rewrite() -> None:
    assert length_ok(ORIGINAL, REWRITE)
    assert not length_ok(ORIGINAL, REWRITE + " " + REWRITE)  # twice as long
    assert not length_ok(ORIGINAL, "Bags.")


def test_the_target_band() -> None:
    assert target_band(None) == 6.5
    assert target_band({"band_low": 5.5, "band_high": 6.0, "uncertain": False}) == 6.5
    assert target_band({"band_low": 8.0, "band_high": 9.0, "uncertain": False}) == 9.0
    assert target_band({"band_low": 4.0, "band_high": 7.5, "uncertain": True}) == 6.5


def test_paragraphs_and_the_sentence_of_a_phrase() -> None:
    assert split_paragraphs("One two.\n\n  \n\nThree four.\n") == ["One two.", "Three four."]
    assert sentence_with(REWRITE, "harm wildlife") == (
        "However, they pollute rivers and harm wildlife."
    )
    assert sentence_with(REWRITE, "never there") is None


def test_one_reason_for_several_edits_becomes_one_combined_real_change() -> None:
    # The pattern seen live (15 Nov): the model explained three edits in one entry.
    original = "Many people think that plastic bags is very bad for environment."
    rewrite = "Many people believe that plastic bags are very harmful to the environment."
    claimed = [
        ChangeOut(
            original="plastic bags is very bad for environment",
            revised="plastic bags are very harmful to the environment",
            why_vi="Chia động từ 'are', thêm 'the', dùng 'harmful'.",
        ),
        ChangeOut(original="think", revised="believe", why_vi="'believe' trang trọng hơn."),
    ]
    changes, unmatched = attach_reasons(diff(original, rewrite), claimed, original, rewrite)
    assert changes == [
        Change("think", "believe", "'believe' trang trọng hơn."),
        Change(
            "plastic bags is very bad for environment",
            "plastic bags are very harmful to the environment",
            "Chia động từ 'are', thêm 'the', dùng 'harmful'.",
        ),
    ]
    assert unmatched == 0


def test_a_combined_change_must_really_be_in_both_texts() -> None:
    original = "Many people think that plastic bags is very bad for environment."
    rewrite = "Many people think that plastic bags are very harmful to environment."
    invented = ChangeOut(
        original="bags is very bad for",
        revised="bags are extremely harmful to",  # not what the rewrite says
        why_vi="Lý do cho một thay đổi không có thật.",
    )
    changes, unmatched = attach_reasons(diff(original, rewrite), [invented], original, rewrite)
    assert all(c.why_vi is None for c in changes) and unmatched == 1
    # whole words only: "is" is not found inside "this"
    this = attach_reasons([Change("is", "are")], [ChangeOut(
        original="this", revised="are", why_vi="Không liên quan.")])[0]  # fmt: skip
    assert this == [Change("is", "are")]


# Step 2.9: the rewrite must still be the learner's argument.
PARA = (
    "Some people think that university should be free for everyone. I agree with this because "
    "many students from poor families cannot pay the fees, so they lose the chance to study."
)


def test_a_paraphrase_that_keeps_the_argument_passes() -> None:
    better = (
        "Some people believe that university education should be free for all. I support this "
        "view, since many students from low-income families cannot afford the fees and therefore "
        "lose the opportunity to study."
    )
    assert rw.meaning_problems(PARA, better) == []


def test_new_numbers_names_or_evidence_are_refused() -> None:
    stat = PARA.replace("many students", "around 40% of students")
    assert "new_facts" in rw.meaning_problems(PARA, stat)
    named = PARA + " For example, Harvard offers free places to some students."
    assert "new_facts" in rw.meaning_problems(PARA, named)
    word = PARA.replace("many students", "two million students")
    assert "new_facts" in rw.meaning_problems(PARA, word)
    # A number the learner already wrote may stay.
    with_number = PARA.replace("many students", "40% of students")
    assert "new_facts" not in rw.meaning_problems(with_number, with_number.replace("so", "and so"))


def test_a_flipped_statement_is_refused() -> None:
    flipped = PARA.replace("I agree with this", "I do not agree with this")
    assert "negation" in rw.meaning_problems(PARA, flipped)
    contracted = PARA.replace("cannot pay", "can pay")
    assert "negation" in rw.meaning_problems(PARA, contracted)


def test_a_different_paragraph_is_refused() -> None:
    other = (
        "Online learning has become popular in recent years. Learners enjoy flexible timetables "
        "and choose their own pace, which suits adults with jobs."
    )
    assert "content" in rw.meaning_problems(PARA, other)
