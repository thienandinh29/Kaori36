"""Step 3.5a: features, the learned detector and thresholds chosen on the train half."""

import math
import random

import pytest

from nodetrail_pron.align import Segment
from nodetrail_pron.features import phone_features
from nodetrail_pron.learn import at, compare, design, threshold_for_recall


def test_features_of_a_segment() -> None:
    lp = [[-5.0, -0.1, -2.0], [-5.0, -3.0, -0.5], [-5.0, -0.2, -2.2]]  # col 0 is blank
    gop, lpp, worst, share, log_n = phone_features(lp, Segment(1, 0, 3), 0)
    assert gop == pytest.approx(((-0.1 + 2.0) + (-3.0 + 0.5) + (-0.2 + 2.2)) / 3)
    assert lpp == pytest.approx((-0.1 - 3.0 - 0.2) / 3)
    assert worst == pytest.approx(-2.5) and share == pytest.approx(2 / 3)
    assert log_n == pytest.approx(math.log(3))


def test_threshold_for_recall_and_the_counts_at_it() -> None:
    score = [0.9, 0.8, 0.7, 0.2, 0.1]
    truth = [1, 0, 1, 1, 0]
    cut = threshold_for_recall(score, truth, 0.6)  # 2 of 3 wrong: down to 0.7
    assert cut == 0.7
    assert at(score, truth, cut) == {
        "flagged": 3, "recall": 0.667, "precision": 0.667, "false_alarm_share": 0.333,
    }  # fmt: skip


def test_unseen_phones_get_no_identity() -> None:
    rows = [("t", [1.0, 2.0], 0), ("q", [3.0, 4.0], 1)]
    assert design(rows, ["s", "t"]) == [[1.0, 2.0, 0.0, 1.0], [3.0, 4.0, 0.0, 0.0]]


def test_the_learned_detector_uses_what_gop_misses() -> None:
    # Wrong phones: GOP only a little lower, but a much lower expected-phone probability (lpp).
    rng = random.Random(0)

    def rows(n: int) -> list[tuple[str, list[float], int]]:
        out = []
        for _ in range(n):
            wrong = int(rng.random() < 0.1)
            gop = rng.gauss(-0.5 if wrong else 0.0, 1.0)
            lpp = rng.gauss(-3.0 if wrong else -0.5, 0.5)
            out.append(("t", [gop, lpp, gop - 1, 0.5, 1.0], wrong))
        return out

    report = compare(rows(3000), rows(3000))
    assert report["learned"]["auc"] > report["gop"]["auc"] + 0.1
    half = report["learned"]["at_recall"]["0.5"]
    assert 0.4 < half["recall"] < 0.6  # chosen on train, close on test
    assert half["false_alarm_share"] < report["gop"]["at_recall"]["0.5"]["false_alarm_share"]
