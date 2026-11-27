"""Step V4: the progress study (pure parts) and the separation rule."""

import re
from datetime import date
from pathlib import Path

import pytest

from app.progress.study import (
    Result,
    check_criteria,
    lowest,
    parse_criteria,
    report,
    schedule,
    truth_of,
)

APP = Path(__file__).resolve().parents[2] / "app"


def snap(p: float) -> dict[str, object]:
    return {"subjects": {"english-ielts": {"concepts": 10, "mean_p_known": p, "known": 2}}}


def test_schedule_counts_from_the_last_sitting() -> None:
    assert schedule(None, None, date(2026, 11, 20))["note"].startswith("Take the baseline")
    s = schedule(date(2026, 11, 20), None, date(2026, 12, 1))
    assert (s["next_due"], s["overdue_days"]) == ("2026-12-18", 0)
    late = schedule(date(2026, 11, 20), date(2026, 12, 18), date(2027, 1, 20))
    assert (late["next_due"], late["overdue_days"]) == ("2027-01-15", 5)


def test_truth_of_marking() -> None:
    assert truth_of("answer_key") == ("gold", True)
    assert truth_of("trained_rater") == ("gold", True)
    assert truth_of("self") == ("bronze", False)
    with pytest.raises(ValueError):
        truth_of("friend")


def test_report_changes_intervals_and_disagreement() -> None:
    def r(day: date, raw: tuple[int, int] | None, band: float, p: float, **kw: object) -> Result:
        k, n = raw or (None, None)
        args: dict[str, object] = {"skill": "reading", "timed": True, "marked_by": "answer_key"}
        args |= kw
        return Result(day, str(args["skill"]), "P", bool(args["timed"]), str(args["marked_by"]),
                      bool(args.get("baseline", False)), k, n, band, snap(p))  # fmt: skip

    rows = [
        r(date(2026, 11, 20), (24, 40), 6.0, 0.40, baseline=True),
        r(date(2026, 12, 18), (29, 40), 6.5, 0.55),
        r(date(2027, 1, 15), (27, 40), 6.0, 0.70, timed=False),
        r(date(2026, 11, 20), None, 6.0, 0.40, skill="writing", marked_by="self", baseline=True),
    ]
    out = report(rows)
    reading = out["skills"]["reading"]["sittings"]
    assert (
        reading[0]["raw"]["share"] == 0.6
        and reading[0]["raw"]["low"] < 0.6 < reading[0]["raw"]["high"]
    )
    assert "change_from_baseline" not in reading[0]
    assert reading[1]["change_from_baseline"] == 0.5 and reading[1]["nodetrail_change"] == 0.15
    assert "disagreement" not in reading[1]
    # The test went down while NodeTrail's estimate went up: flagged, and the test is trusted.
    assert reading[2]["change_from_previous"] == -0.5 and "disagreement" in reading[2]
    assert reading[2]["caution"] == "not under exam conditions"
    assert reading[0]["basis"]["truth"] == "gold" and reading[0]["basis"]["declared"]
    writing = out["skills"]["writing"]["sittings"][0]
    assert writing["basis"]["truth"] == "bronze" and writing["basis"]["gate"] == "not_measured"
    assert "N-of-1" in out["note"]


def test_only_the_progress_package_touches_progress_tests() -> None:
    """Evaluation data stays apart: no engine, service or route reads the progress results."""
    offenders = [
        str(p.relative_to(APP))
        for p in APP.rglob("*.py")
        if "progress" not in p.relative_to(APP).parts[:1]
        and re.search(r"\bprogress_tests\b", p.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_criteria_are_parsed_and_checked() -> None:
    assert parse_criteria("FC=7, lr=7,gra=6,p=7") == {"fc": 7, "lr": 7, "gra": 6, "p": 7}
    for bad in ("fc7", "fc=seven", "fc=6.5", "fc=7,fc=6", ""):
        with pytest.raises(ValueError):
            parse_criteria(bad)
    ok = check_criteria("speaking", "trained_rater", {"p": 7, "gra": 6, "lr": 7, "fc": 7})
    assert list(ok) == ["fc", "lr", "gra", "p"]  # always in the descriptors' order
    assert check_criteria("writing", "self", {"tr": 6, "cc": 6, "lr": 7, "gra": 6})
    for skill, by, crit in (
        ("reading", "trained_rater", {"fc": 7}),  # no criteria for Reading or Listening
        ("speaking", "answer_key", {"fc": 7, "lr": 7, "gra": 6, "p": 7}),
        ("speaking", "trained_rater", {"fc": 7, "lr": 7, "gra": 6}),  # all four
        ("speaking", "trained_rater", {"tr": 7, "lr": 7, "gra": 6, "p": 7}),  # writing's key
        ("writing", "trained_rater", {"tr": 10, "cc": 6, "lr": 7, "gra": 6}),
    ):
        with pytest.raises(ValueError):
            check_criteria(skill, by, crit)
    assert lowest({"fc": 7, "lr": 6, "gra": 6, "p": 7}) == ["lr", "gra"]


def test_report_names_the_lowest_criterion_and_its_change_but_never_a_band() -> None:
    rows = [
        Result(date(2026, 12, 1), "speaking", "Mock 1", True, "trained_rater", True,
               band=6.5, criteria={"fc": 7, "lr": 7, "gra": 6, "p": 7}),
        Result(date(2026, 12, 29), "speaking", "Mock 2", True, "trained_rater", band=6.5),
        Result(date(2027, 1, 26), "speaking", "Mock 3", True, "trained_rater",
               band=7.0, criteria={"fc": 7, "lr": 8, "gra": 7, "p": 6}),
    ]  # fmt: skip
    sittings = report(rows)["skills"]["speaking"]["sittings"]
    assert sittings[0]["lowest"] == ["gra"] and "criteria_change" not in sittings[0]
    assert "criteria" not in sittings[1]  # a sitting without criteria shows none
    assert sittings[2]["lowest"] == ["p"]
    # compared with the last sitting that had criteria (Mock 1), not Mock 2
    assert sittings[2]["criteria_change"] == {"fc": 0, "lr": 1, "gra": 1, "p": -1}
    assert sittings[2]["band"] == 7.0  # the rater's band, as given
