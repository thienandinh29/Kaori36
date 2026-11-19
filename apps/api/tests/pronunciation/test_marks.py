"""Steps 3.4a and 3.6a: marks and evidence only for applied groups; three outcomes."""

import json
from pathlib import Path

from app.pronunciation.evidence import Rates
from app.pronunciation.marks import Applied, applicable, load_applied, marks, observations, outcomes

GROUPS = {"th-voiced": "th", "final-t": "final-consonants"}
RATES = Rates(right_if_right=0.7, wrong_if_right=0.05, right_if_wrong=0.1, wrong_if_wrong=0.6)


def target(sound: str, gop: float, competitor: str | None = "d") -> dict[str, object]:
    return {"sound": sound, "gop": gop, "competitor": competitor}


def test_no_applied_thresholds_means_no_marks(tmp_path: Path) -> None:
    assert load_applied(tmp_path / "thresholds.json") == {}
    assert marks([target("th-voiced", -9.0)], GROUPS, {}) == []


def test_a_mark_needs_an_applied_group_a_low_score_and_a_competitor() -> None:
    applied = {"th": Applied(threshold=-1.0, accept=-0.2, rates=RATES, labelled=80)}
    targets = [
        target("th-voiced", -2.0),  # marked
        target("th-voiced", -0.5),  # between the thresholds: not sure
        target("th-voiced", -2.0, None),  # nothing else was heard: not sure
        target("final-t", -5.0),  # group not applied: nothing said
        target("th-voiced", 0.3),  # at or above accept: right
    ]
    assert marks(targets, GROUPS, applied) == [0]
    assert outcomes(targets, GROUPS, applied) == [
        "wrong", "inconclusive", "inconclusive", None, "right",
    ]  # fmt: skip


def test_only_pass_groups_are_applied_with_their_rates_and_the_file_round_trips(
    tmp_path: Path,
) -> None:
    by_truth = {
        "said_right": {"right": 14, "wrong": 1, "inconclusive": 5},
        "said_wrong": {"right": 1, "wrong": 6, "inconclusive": 3},
    }
    report = {
        "groups": {
            "th": {
                "verdict": "pass",
                "threshold": -1.2,
                "accept": -0.1,
                "tune": {"n": 40},
                "check": {"n": 38, "outcomes": by_truth},
            },
            "final-consonants": {"verdict": "fail", "threshold": -0.5},
            "clusters-vowels": {"verdict": "too_few", "threshold": None},
        }
    }
    out = applicable(report, "2026-12-01")
    assert out == {
        "applied": "2026-12-01",
        "groups": {"th": {"threshold": -1.2, "accept": -0.1, "rates": RATES.__dict__,
                          "labelled": 78}},
    }  # fmt: skip
    path = tmp_path / "thresholds.json"
    path.write_text(json.dumps(out))
    assert load_applied(path) == {"th": Applied(-1.2, -0.1, RATES, 78)}


def test_one_conclusive_observation_per_group_from_its_first_target() -> None:
    coin = Rates(0.5, 0.5, 0.5, 0.5)
    applied = {
        "th": Applied(-1.0, -0.2, RATES, 80),
        "final-consonants": Applied(-1.0, -0.2, coin, 40),  # applied, but says nothing
    }
    targets = [target("final-t", -3.0), target("th-voiced", 2.0), target("th-voiced", -3.0)]
    assert observations(targets, GROUPS, applied) == [("th", 1, True)]
    assert observations(targets, GROUPS, {}) == []  # the gate: nothing moves
    # The group's first target is not sure: nothing from this recording, even though a later
    # one is conclusive (choosing it would choose the evidence).
    unsure_first = [target("th-voiced", -0.5), target("th-voiced", -3.0)]
    assert observations(unsure_first, GROUPS, applied) == []
    # A mark is a wrong observation; nothing is said right merely for not being marked.
    assert observations([target("th-voiced", -3.0)], GROUPS, applied) == [("th", 0, False)]
