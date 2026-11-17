"""Step 3.4a: marks only for applied groups, with a competitor; observation model from rates."""

import json
from pathlib import Path

import pytest

from app.pronunciation.marks import Applied, applicable, load_applied, marks, observation

GROUPS = {"th-voiced": "th", "final-t": "final-consonants"}


def target(sound: str, gop: float, competitor: str | None = "d") -> dict[str, object]:
    return {"sound": sound, "gop": gop, "competitor": competitor}


def test_no_applied_thresholds_means_no_marks(tmp_path: Path) -> None:
    assert load_applied(tmp_path / "thresholds.json") == {}
    assert marks([target("th-voiced", -9.0)], GROUPS, {}) == []


def test_a_mark_needs_an_applied_group_a_low_score_and_a_competitor() -> None:
    applied = {"th": Applied(threshold=-1.0, slip=0.05, guess=0.6, labelled=80)}
    targets = [
        target("th-voiced", -2.0),  # marked
        target("th-voiced", -0.5),  # above the threshold
        target("th-voiced", -2.0, None),  # nothing else was heard
        target("final-t", -5.0),  # group not applied
    ]
    assert marks(targets, GROUPS, applied) == [0]


def test_observation_comes_from_the_check_half_and_refuses_uninformative_marks() -> None:
    good = {"check": {"false_positive_rate": 0.04, "recall": 0.45}}
    assert observation(good) == pytest.approx((0.04, 0.55))
    useless = {"check": {"false_positive_rate": 0.3, "recall": 0.2}}  # 0.3 + 0.8 >= 1
    assert observation(useless) is None
    assert observation({"check": {"recall": None, "false_positive_rate": 0.1}}) is None


def test_only_pass_groups_are_applied_and_the_file_round_trips(tmp_path: Path) -> None:
    report = {
        "groups": {
            "th": {
                "verdict": "pass",
                "threshold": -1.2,
                "tune": {"n": 40},
                "check": {"n": 38, "false_positive_rate": 0.05, "recall": 0.5},
            },
            "final-consonants": {"verdict": "fail", "threshold": -0.5},
            "clusters-vowels": {"verdict": "too_few", "threshold": None},
        }
    }
    out = applicable(report, "2026-12-01")
    assert out == {
        "applied": "2026-12-01",
        "groups": {"th": {"threshold": -1.2, "slip": 0.05, "guess": 0.5, "labelled": 78}},
    }
    path = tmp_path / "thresholds.json"
    path.write_text(json.dumps(out))
    assert load_applied(path) == {"th": Applied(-1.2, 0.05, 0.5, 78)}


def test_one_observation_per_applied_group_from_its_first_target() -> None:
    applied = {
        "th": Applied(-1.0, 0.05, 0.5, 80),
        "final-consonants": Applied(-1.0, None, None, 40),  # applied, but marks say nothing
    }
    targets = [target("final-t", -3.0), target("th-voiced", 2.0), target("th-voiced", -3.0)]
    marked = marks(targets, GROUPS, applied)
    assert marked == [0, 2]
    from app.pronunciation.marks import observations

    assert observations(targets, marked, GROUPS, applied) == [("th", 1, True)]
    assert observations(targets, marked, GROUPS, {}) == []  # the gate: nothing moves
