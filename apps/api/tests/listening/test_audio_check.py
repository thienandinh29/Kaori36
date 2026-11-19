"""The Listening audio check (specs/listening-reading/step-4.4a.md)."""

import json
from pathlib import Path

import pytest

from app.listening.audio_check import MAX_ATTEMPTS, Result, check, decide, normalise, recovered

ROOT = Path(__file__).resolve().parents[4]

# A Whisper-style transcript of the study's dialogue, constructed for this test from the slips the
# study reported (docs/v2/listening-sources.md): the phone number lost a digit, "this Saturday" →
# "the Saturday"; the rest came back, with digits, "£" and "%" written as Whisper writes them.
TRANSCRIPT = {
    1: "Hi, I'd like to book a badminton court for the Saturday, please.",
    3: "Around 10 in the morning, if possible.",
    4: "Let me check. 10 o'clock is taken, I'm afraid, but there's a court free at 11.30.",
    6: "Courts are booked by the hour, so until half past 12. "
    "It's £8.50 for members and £12 for non-members.",
    8: "If you play every week, yes. Membership is £40 a year, "
    "and you also get 10% off in the cafe.",
    11: "It's Henderson. H-E-N-D-E-R-S-O-N.",
    13: "077-44-5123.",
    14: "Lovely. Please arrive 15 minutes early and bring your own rackets. "
    "We only have a few to borrow.",
}


def _dialogue() -> tuple[list[str], list[str]]:
    turns = json.loads(
        (ROOT / "docs/v2/listening-sources/dialogue.json").read_text(encoding="utf-8")
    )
    lines = [text for _, text in turns]
    return lines, [TRANSCRIPT.get(k, line) for k, line in enumerate(lines)]


def test_the_study_dialogue_loses_only_the_phone_number() -> None:
    lines, transcripts = _dialogue()
    answers = [
        "eleven thirty",
        "half past twelve",
        "eight pounds fifty",
        "twelve pounds",
        "forty pounds",
        "ten per cent",
        "Henderson",
        "H, E, N, D, E, R, S, O, N",
        "oh seven seven, double four, five one, two nine three",
        "fifteen minutes",
    ]
    results = check(lines, answers, transcripts)
    unheard = [r.answer for r in results if not r.ok]
    assert unheard == ["oh seven seven, double four, five one, two nine three"]
    phone = results[answers.index(unheard[0])]
    assert phone.line == 13 and phone.reason == "not_heard"
    assert decide(results, attempt=1).resynthesise == (13,)


@pytest.mark.parametrize(
    ("spoken", "written"),
    [
        ("twenty-one", "21"),
        ("three hundred and five", "305"),
        ("two thousand and twenty six", "2026"),
        ("the fifth of May", "the 5th of May"),
        ("the thirty first", "the 31st"),
        ("eight pounds fifty", "£8.50"),
        ("ten percent", "10%"),
        ("eleven thirty", "11:30"),
        ("oh seven seven double four", "07744"),
        ("triple oh", "000"),
        ("one thousand", "1,000"),
        ("It's Smith, S M I T H", "its smith smith"),
    ],
)
def test_spoken_and_written_forms_read_the_same(spoken: str, written: str) -> None:
    assert normalise(spoken) == normalise(written)


def test_a_lost_or_extra_digit_fails() -> None:
    assert recovered("oh seven seven, double four, five one, two nine three", "07744 51293")
    assert not recovered("oh seven seven, double four, five one, two nine three", "077-44-5123")
    assert not recovered("double four", "444")


def test_oh_is_zero_only_next_to_a_number() -> None:
    assert normalise("Oh, I see") == ["oh", "i", "see"]
    assert normalise("oh seven") == ["07"]
    assert normalise("a double room") == ["a", "double", "room"]


def test_separate_numbers_are_not_merged_with_words_between() -> None:
    assert normalise("twelve pounds fifty") == ["12", "pounds", "50"]
    assert normalise("eleven thirty") == ["1130"]


def test_answers_must_be_contiguous_and_in_order() -> None:
    assert recovered("Riverside Sports Centre", "Good morning, Riverside Sports Centre.")
    assert not recovered("Riverside Sports Centre", "Riverside Centre for Sports")
    assert not recovered("", "anything")


def test_vietnamese_text_is_compared_in_nfc() -> None:
    decomposed = "Nguyễn"
    assert normalise(decomposed) == normalise("Nguyễn")


def test_an_answer_missing_from_the_script_is_dropped_at_once() -> None:
    results = check(["Book a court for Saturday."], ["Sunday"], ["Book a court for Saturday."])
    assert results == [Result("Sunday", None, "not_in_script")]
    assert decide(results, attempt=1).dropped == ("Sunday",)


def test_unheard_answers_are_retried_once_then_dropped() -> None:
    results = [
        Result("a", 2, "not_heard"),
        Result("b", 2, "not_heard"),
        Result("c", 5, "recovered"),
    ]
    first = decide(results, attempt=1)
    assert first.resynthesise == (2,) and first.dropped == () and not first.passed
    last = decide(results, attempt=MAX_ATTEMPTS)
    assert last.resynthesise == () and last.dropped == ("a", "b")
    assert decide([Result("c", 5, "recovered")], attempt=1).passed


def test_lines_and_transcripts_must_match() -> None:
    with pytest.raises(ValueError, match="2 script lines but 1 transcripts"):
        check(["a", "b"], ["a"], ["a"])
