"""Step 4.4b: dictation and gap-fill items built by code from the Reading bank."""

from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]

from app.listening.items import (
    BLANK,
    PER_KIND,
    build,
    gap_word,
    grade,
    mark_dictation,
    safe,
    sentences,
    words,
)

TEXTS = Path(__file__).resolve().parents[4] / "data" / "english" / "texts"
PASSAGE = (
    "Honey bees live in large colonies near flowers and trees. A colony can hold 60,000 bees.\n\n"
    "Worker bees collect nectar and turn it into honey inside the hive. The Queen lays eggs.\n\n"
    "In winter the bees stay together to keep each other warm. They eat the honey they stored."
)


@pytest.mark.parametrize(
    ("sentence", "ok"),
    [
        ("Honey bees live in large colonies near flowers and trees.", True),
        ("A colony can hold 60,000 bees.", False),  # digits
        ("The Queen lays eggs.", False),  # too short, and a capital after the first word
        ("Worker bees from Brazil collect nectar in the warm season.", False),  # a name
        ("Bees (and wasps) collect nectar from many flowers every day.", False),  # brackets
        ("Bees collect nectar; wasps hunt other insects in the garden.", False),  # semicolon
        ("Do bees really sleep at night in the middle of winter?", True),
    ],
)
def test_only_sentences_the_voice_says_exactly_qualify(sentence: str, ok: bool) -> None:
    assert safe(sentence) is ok


def test_items_alternate_dictation_and_gaps_and_hide_the_answer() -> None:
    items = build("bees", PASSAGE)
    assert [i.id for i in items] == [
        "bees-dictation-1", "bees-gap-1", "bees-dictation-2", "bees-gap-2",
    ]  # fmt: skip
    gap = items[1]
    assert gap.prompt is not None and BLANK in gap.prompt and gap.answer not in gap.prompt
    assert gap.prompt.replace(BLANK, gap.answer) == gap.sentence
    assert items[0].prompt is None and items[0].answer == items[0].sentence
    assert {i.competency for i in items} == {"listening-dictation", "listening-detail"}


def test_the_gap_is_a_long_content_word() -> None:
    assert (
        gap_word("Worker bees collect nectar and turn it into honey inside the hive.") == "collect"
    )
    assert gap_word("They eat it all the time and they are fine.") is None


def test_dictation_is_exact_word_by_word_but_ignores_case_and_punctuation() -> None:
    s = "Worker bees collect nectar and turn it into honey."
    assert mark_dictation(s, "worker bees collect nectar, and turn it into honey")[:2] == (
        1.0,
        True,
    )
    score, ok, marks = mark_dictation(s, "Worker bee collect nectar and turned it honey.")
    assert not ok and score == pytest.approx(6 / 9)
    assert [m for m in marks if m["status"] != "right"] == [
        {"word": "bees", "status": "wrong"},
        {"word": "turn", "status": "wrong"},
        {"word": "into", "status": "missed"},
    ]
    assert mark_dictation(s, "")[:2] == (0.0, False)
    assert words("It\N{RIGHT SINGLE QUOTATION MARK}s ours.") == ["it's", "ours"]


def test_a_gap_is_one_word_exact_after_normalising() -> None:
    gap = build("bees", PASSAGE)[1]
    assert grade(gap, f"  {gap.answer.upper()} ")[1] is True
    assert grade(gap, gap.answer[:-1])[1] is False  # a misspelling is wrong


def test_the_real_bank_gives_safe_items_with_unique_ids() -> None:
    total = 0
    ids: set[str] = set()
    for path in sorted(TEXTS.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        items = build(doc["slug"], doc["text"])
        assert sum(i.kind == "dictation" for i in items) <= PER_KIND
        assert sum(i.kind == "gap" for i in items) <= PER_KIND
        for i in items:
            assert safe(i.sentence) and i.sentence in sentences(doc["text"])
            assert i.id not in ids
            ids.add(i.id)
        total += len(items)
    assert total >= 100  # 143 on 19 Nov: enough to practise while the recogniser is chosen
