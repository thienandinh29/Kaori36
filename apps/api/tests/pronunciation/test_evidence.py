"""Step 3.6a: three outcomes and the two-layer observation model (app/pronunciation/evidence.py)."""

import pytest

from app.engine import bkt
from app.pronunciation.evidence import LEARNER_GUESS, LEARNER_SLIP, Rates, effective, outcome


def test_outcomes_need_a_competitor_to_be_wrong_and_a_high_score_to_be_right() -> None:
    assert outcome({"gop": -3.0, "competitor": "t"}, -1.0, -0.2) == "wrong"
    assert outcome({"gop": -3.0, "competitor": None}, -1.0, -0.2) == "inconclusive"
    assert outcome({"gop": -0.5, "competitor": "t"}, -1.0, -0.2) == "inconclusive"
    assert outcome({"gop": -0.2, "competitor": None}, -1.0, -0.2) == "right"


def test_a_perfect_detector_gives_back_the_learners_own_slip_and_guess() -> None:
    perfect = Rates(right_if_right=1, wrong_if_right=0, right_if_wrong=0, wrong_if_wrong=1)
    assert effective(perfect) == (LEARNER_SLIP, LEARNER_GUESS)


def test_detector_errors_add_to_the_learners_and_inconclusive_ones_drop_out() -> None:
    # 70% of right sounds accepted, 5% falsely marked (25% inconclusive);
    # 10% of wrong sounds accepted, 60% caught (30% inconclusive).
    r = Rates(right_if_right=0.70, wrong_if_right=0.05, right_if_wrong=0.10, wrong_if_wrong=0.60)
    s, g = 0.10, 0.25
    wrong_k, right_k = 0.9 * 0.05 + 0.1 * 0.60, 0.9 * 0.70 + 0.1 * 0.10
    right_n, wrong_n = 0.25 * 0.70 + 0.75 * 0.10, 0.25 * 0.05 + 0.75 * 0.60
    out = effective(r, s, g)
    assert out == (round(wrong_k / (wrong_k + right_k), 4), round(right_n / (right_n + wrong_n), 4))
    assert out is not None and out[0] > s and out[1] > g  # noisier than the learner alone
    # The old rule (detector rates as slip and guess) said a mark is far stronger evidence:
    old = bkt.update(0.5, False, bkt.BKTParams(0.2, 0.05, 0.05, 0.4))
    new = bkt.update(0.5, False, bkt.BKTParams(0.2, 0.05, out[0], out[1]))
    assert new > old


def test_an_uninformative_detector_gives_no_evidence() -> None:
    coin = Rates(right_if_right=0.5, wrong_if_right=0.5, right_if_wrong=0.5, wrong_if_wrong=0.5)
    assert effective(coin) is None
    never_sure = Rates(0, 0, 0, 0)
    assert effective(never_sure) is None


def test_rates_from_outcome_counts() -> None:
    r = Rates.from_counts({"right": 14, "wrong": 1, "inconclusive": 5},
                          {"right": 1, "wrong": 6, "inconclusive": 3})  # fmt: skip
    assert r == Rates(0.7, 0.05, 0.1, 0.6)
    assert Rates.from_counts({}, {}) == Rates(0.0, 0.0, 0.0, 0.0)
    with pytest.raises(TypeError):
        Rates(1, 0, 0)  # type: ignore[call-arg]


def test_a_dropped_sound_is_wrong_whatever_its_score() -> None:
    from app.pronunciation.evidence import DROPPED_PEAK, is_dropped

    gone = {"gop": 0.0, "competitor": None, "peak": 0.01, "other_peak": 0.02}
    assert is_dropped(gone) and outcome(gone, -1.0, -0.2) == "wrong"
    swapped = {"gop": -3.0, "competitor": "t", "peak": 0.01, "other_peak": 0.95}
    assert not is_dropped(swapped)  # another phone peaked: said, but something else
    old = {"gop": 0.5, "competitor": None}  # an analysis from before step 3.6b
    assert not is_dropped(old) and outcome(old, -1.0, -0.2) == "right"
    edge = {"gop": 0.5, "competitor": None, "peak": DROPPED_PEAK, "other_peak": 0.0}
    assert not is_dropped(edge)  # the rule is strictly below
