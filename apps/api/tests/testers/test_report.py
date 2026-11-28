"""Step 5.5 (specs/speaking/step-5.5.md): the tester report. Pure."""

from datetime import date, timedelta
from uuid import uuid4

from app.testers.report import Enrolled, Number, Sitting, iso_week, report

TODAY = date(2026, 12, 20)


def sittings(learner, days: list[int], mode: str = "exam") -> list[Sitting]:  # type: ignore[no-untyped-def]
    return [Sitting(learner, TODAY - timedelta(days=d), mode) for d in days]


def test_counts_per_tester_and_no_audio_or_words() -> None:
    a, b = uuid4(), uuid4()
    out = report(
        [Enrolled(a, "Mai", False, False), Enrolled(b, "An", True, False)],
        sittings(a, [20, 20, 5]) + sittings(a, [19], "guided") * 4 + sittings(b, [3]),
        [],
        TODAY,
    )
    mai = next(t for t in out["testers"] if t["label"] == "Mai")
    assert (mai["days_active"], mai["mock_tests"], mai["practice_tries"]) == (3, 3, 4)
    assert mai["first_day"] == "2026-11-30" and mai["last_day"] == "2026-12-15"
    assert next(t for t in out["testers"] if t["label"] == "An")["switched_off"] is True
    assert [t["label"] for t in out["testers"]] == ["An", "Mai"]  # by label
    text = str(out).lower()
    assert not {"audio", "transcript"} & set(out) and "weekly_numbers" not in text


def test_retention_counts_testers_active_on_or_after_day_14() -> None:
    ids = [uuid4() for _ in range(5)]
    testers = [Enrolled(i, f"t{n}", False, False) for n, i in enumerate(ids)]
    rows = (
        sittings(ids[0], [30, 10])  # first 30 days ago, back at day 20: retained
        + sittings(ids[1], [30, 25])  # only the first fortnight: not retained
        + sittings(ids[2], [14])  # first exactly 14 days ago, no later day: eligible, not retained
        + sittings(ids[3], [13, 1])  # first 13 days ago: too new to count
        # ids[4] never started
    )
    r = report(testers, rows, [], TODAY)["retention"]
    assert (r["eligible"], r["retained"], r["share"]) == (3, 1, 0.333)
    assert 0 < r["low"] < 0.333 < r["high"] < 1  # an exact interval, wide with so few
    assert "Fewer than 10" in r["note"] and r["gate"].startswith("at least 5 of 10")


def test_no_eligible_testers_gives_no_share() -> None:
    r = report([], [], [], TODAY)["retention"]
    assert (r["eligible"], r["share"], r["low"], r["high"]) == (0, None, None, None)


def test_numbers_appear_only_for_testers_who_accepted_the_research_notice() -> None:
    yes, no = uuid4(), uuid4()
    week = iso_week(date(2026, 12, 1))
    numbers = [
        Number(yes, week, 100.0, 10.0),
        Number(yes, week, 120.0, 6.0),
        Number(yes, week, 110.0, None),
        Number(yes, iso_week(date(2026, 12, 8)), 130.0, 5.0),
        Number(no, week, 90.0, 12.0),
    ]
    out = report(
        [Enrolled(yes, "Yes", False, True), Enrolled(no, "No", False, False)], [], numbers, TODAY
    )
    by = {t["label"]: t for t in out["testers"]}
    assert "weekly_numbers" not in by["No"]  # never, whatever the data says
    w = by["Yes"]["weekly_numbers"]
    assert [x["week"] for x in w] == [week, iso_week(date(2026, 12, 8))]
    assert w[0] == {
        "week": week, "answers": 3, "median_speech_rate": 110.0, "median_pauses_per_minute": 8.0,
    }  # fmt: skip
    assert iso_week(date(2026, 12, 31)) == "2026-W53"
