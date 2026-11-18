# ruff: noqa: RUF001
import math
from pathlib import Path

import pytest

from nodetrail_pron.evaluate import (
    ARPABET,
    Utterance,
    auc,
    evaluate,
    pearson,
    pearson_interval,
    to_ipa,
)


def test_arpabet_maps_to_the_recognisers_phones() -> None:
    assert [to_ipa(p) for p in ["DH", "IH0", "S", "AH0", "AH1", "ER0", "IY1"]] == [
        "ð",
        "ɪ",
        "s",
        "ə",
        "ʌ",
        "ɚ",
        "iː",
    ]
    assert len(ARPABET) == 38  # the 39 ARPAbet phones, AH handled by stress


def test_pearson_and_its_interval() -> None:
    assert pearson([1, 2, 3, 4], [2, 4, 6, 8]) == pytest.approx(1.0)
    assert pearson([1, 2, 3, 4], [8, 6, 4, 2]) == pytest.approx(-1.0)
    low, high = pearson_interval(0.5, 100)
    assert low < 0.5 < high and high - low < 0.4


def test_auc_counts_wrong_phones_scored_lower() -> None:
    assert auc([-5, -4], [1, 2]) == 1.0  # every wrong phone lower
    assert auc([1, 2], [-5, -4]) == 0.0
    assert auc([0, 0], [0, 0]) == 0.5  # ties count half


def test_evaluate_scores_sentences_and_phones_and_skips_failures() -> None:
    utts = [
        Utterance("a", Path("a"), 10, ["s", "iː"], [2.0, 2.0]),
        Utterance("b", Path("b"), 2, ["s", "iː"], [0.0, 2.0]),
        Utterance("c", Path("c"), 6, ["s", "iː"], [2.0, 0.4]),
        Utterance("d", Path("d"), 5, ["s"], [2.0]),
    ]
    gops = {"a": [3.0, 3.0], "b": [-6.0, 2.0], "c": [2.0, -3.0], "d": None}
    report = evaluate(utts, lambda wav, phones: gops[str(wav)])
    assert report["sentences"] == 3 and report["skipped"] == 1
    assert report["sentence_pcc"] > 0.5
    assert report["phone_auc"] == 1.0 and report["phones_wrong"] == 2
    zero = next(t for t in report["thresholds"] if t["threshold"] == 0.0)
    assert zero["recall"] == 1.0 and zero["precision"] == 1.0
    assert not math.isnan(zero["false_alarm_share"])
