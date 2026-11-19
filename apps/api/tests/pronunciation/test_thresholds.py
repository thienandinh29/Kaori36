"""Step 3.3b: thresholds per sound group, chosen on one half and checked on the other."""

import pytest

from app.pronunciation.thresholds import (
    Labelled,
    choose,
    from_rows,
    half,
    report,
    report_group,
    wilson,
)


def recordings(which: str, n: int) -> list[str]:
    """n recording ids that land in the given half."""
    out: list[str] = []
    i = 0
    while len(out) < n:
        if half(f"r{i}") == which:
            out.append(f"r{i}")
        i += 1
    return out


def test_the_split_is_by_recording_fixed_and_about_even() -> None:
    ids = [f"rec-{i}" for i in range(1000)]
    assert [half(r) for r in ids] == [half(r) for r in ids]
    assert 430 < sum(half(r) == "tune" for r in ids) < 570


def test_wilson_matches_known_values() -> None:
    lo, hi = wilson(1, 10)
    assert lo == pytest.approx(0.0179, abs=1e-3) and hi == pytest.approx(0.4042, abs=1e-3)
    assert wilson(0, 0) == (0.0, 1.0)


def test_choose_catches_the_most_wrong_sounds_within_the_false_alarm_limit() -> None:
    wrong = [Labelled("a", "g", g, True) for g in (-3.0, -2.5, -2.0, -1.0)]
    right = [Labelled("a", "g", g, False) for g in (-1.5, *[0.5 + i for i in range(20)])]
    # below -1.0 also flags the right -1.5 (1 of 5 = 20%); below -2.0 catches 3 with none false
    assert choose(wrong + right) == pytest.approx(-1.999)
    assert choose(wrong + right, max_false=0.25) == pytest.approx(-0.999)
    assert choose(right) is None  # nothing wrong to catch


def test_a_group_passes_only_with_few_false_alarms_and_enough_flags_on_the_check_half() -> None:
    tune, check = recordings("tune", 30), recordings("check", 30)

    def sounds(ids: list[str], false_at: int) -> list[Labelled]:
        out = []
        for i, r in enumerate(ids):
            out.append(Labelled(r, "th", -3.0, True))  # a clearly wrong sound per recording
            out.append(Labelled(r, "th", -3.0 if i < false_at else 2.0, False))
        return out

    good = report_group(sounds(tune, 0) + sounds(check, 2))
    assert good["threshold"] == pytest.approx(-2.999)
    assert good["check"]["flagged"] == 32 and good["check"]["false_alarms"] == 2
    assert good["verdict"] == "pass" and good["check"]["recall"] == 1.0
    assert report_group(sounds(tune, 0) + sounds(check, 10))["verdict"] == "fail"
    few = report_group(sounds(tune, 0) + sounds(check[:5], 0))
    assert few["verdict"] == "too_few"


def test_report_groups_rows_and_leaves_unsure_out() -> None:
    analysis = {
        "targets": [
            {"sound": "th-voiced", "gop": -2.0},
            {"sound": "final-t", "gop": 1.0},
        ]
    }
    rows = [
        ("r1", analysis, 0, "wrong"),
        ("r1", analysis, 1, "unsure"),
        ("r2", analysis, 1, "right"),
    ]
    items = from_rows(rows, {"th-voiced": "th", "final-t": "final-consonants"})
    assert items == [
        Labelled("r1", "th", -2.0, True),
        Labelled("r2", "final-consonants", 1.0, False),
    ]
    assert set(report(items)["groups"]) == {"th", "final-consonants"}


def test_thresholds_stay_at_or_below_zero_where_a_competitor_is_always_heard() -> None:
    # Wrong sounds that still score above 0 cannot be flagged by the product's rule, so the
    # chosen threshold never rises above 0 to catch them.
    wrong = [Labelled("a", "g", g, True) for g in (-2.0, 0.4, 0.5)]
    right = [Labelled("a", "g", g, False) for g in (1.0 + i for i in range(30))]
    t = choose(wrong + right)
    assert t is not None and t <= 0


def test_accept_is_the_lowest_score_with_few_wrong_sounds_accepted() -> None:
    from app.pronunciation.thresholds import choose_accept

    items = [Labelled("a", "g", g, w) for g, w in
             [(-3.0, True), (-0.8, True), (-0.5, False), (-0.4, True), *[(0.1 * i, False)
              for i in range(10)]]]  # fmt: skip
    # From -0.5 up: 12 accepted, 1 wrong (8%); from -0.8: 13 accepted, 2 wrong (15%).
    assert choose_accept(items, threshold=-2.0) == -0.5
    assert choose_accept(items, threshold=-2.0, max_wrong=0.0) == 0.0
    assert choose_accept([Labelled("a", "g", 1.0, True)], threshold=-2.0) is None


def test_three_outcomes_by_truth_and_the_new_ways_to_fail() -> None:
    from app.pronunciation.thresholds import outcomes

    tune, check = recordings("tune", 30), recordings("check", 30)

    def sounds(ids: list[str], unsure: int = 0, accepted_wrong: int = 0) -> list[Labelled]:
        out = []
        for i, r in enumerate(ids):
            wrong_gop = 2.0 if i < accepted_wrong else -1.5 if i < unsure else -3.0
            out.append(Labelled(r, "th", wrong_gop, True))
            out.append(Labelled(r, "th", -1.5 if i < unsure else 2.0, False))
        return out

    base = sounds(tune)
    good = report_group(base + sounds(check))
    assert good["accept"] == 2.0 and good["verdict"] == "pass"
    assert good["check"]["outcomes"] == {
        "said_right": {"right": 30, "wrong": 0, "inconclusive": 0},
        "said_wrong": {"right": 0, "wrong": 30, "inconclusive": 0},
    }
    assert good["check"]["conclusive_share"] == 1.0
    # Mostly unsure (40 of 60 between the thresholds): rarely wrong, but rarely sure either.
    unsure = report_group(base + sounds(check, unsure=20))
    assert unsure["check"]["conclusive_share"] < 0.5 and unsure["verdict"] == "fail"
    # Accepting wrong sounds as right fails too (a different layer from false alarms).
    loose = report_group(base + sounds(check, accepted_wrong=8))  # 8 wrong ones scored high
    assert loose["check"]["accepted_wrong_share"] > 0.10 and loose["verdict"] == "fail"
    counted = outcomes([Labelled("a", "g", -1.5, False)], threshold=-2.0, accept=0.0)
    assert counted["said_right"]["inconclusive"] == 1
