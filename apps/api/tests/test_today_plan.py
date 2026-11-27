"""Today's plan, step M5 (specs/two-layer-map/step-m5.md): done rules, minutes, the week. Pure."""

from datetime import UTC, date, datetime

from app.services.today_plan import (
    Target,
    TodayEvidence,
    estimate_minutes,
    is_done,
    local_day,
    study_week,
    week_bounds,
)

REVIEW = Target("review")
WRITING = Target("competency", skill="writing")
READING = Target("competency", skill="reading")
MILESTONE = Target("grammar", nodes=("tenses", "present-perfect", "past-simple"))


def test_reviews_are_done_when_the_due_cards_are_answered_at_most_one_session() -> None:
    assert not is_done(REVIEW, "vocab", 3, TodayEvidence(reviews={"vocab": 2}))
    assert is_done(REVIEW, "vocab", 3, TodayEvidence(reviews={"vocab": 3}))
    assert is_done(REVIEW, "vocab", 80, TodayEvidence(reviews={"vocab": 20}))  # one session
    assert not is_done(REVIEW, "phrases", 2, TodayEvidence(reviews={"vocab": 9}))


def test_foundations() -> None:
    band = Target("vocab_band")
    assert not is_done(band, "vocab-b1", 0, TodayEvidence(bands={"vocab-b1": 9}))
    assert is_done(band, "vocab-b1", 0, TodayEvidence(bands={"vocab-b1": 10}))
    assert not is_done(band, "vocab-b1", 0, TodayEvidence(bands={"vocab-b2": 30}))  # its own words
    ev = TodayEvidence(grammar={"present-perfect": 3, "past-simple": 2, "other": 9})
    assert is_done(MILESTONE, "tenses", 0, ev)  # the milestone's hidden nodes add up
    assert not is_done(Target("grammar", nodes=("past-simple",)), "past-simple", 0, ev)
    assert is_done(Target("pronunciation"), "final-s", 0, TodayEvidence(recordings=1))
    assert not is_done(Target("pronunciation"), "final-s", 0, TodayEvidence())


def test_competencies() -> None:
    assert is_done(WRITING, "w-task-response", 0, TodayEvidence(essays=1))
    assert not is_done(WRITING, "w-task-response", 0, TodayEvidence())
    assert not is_done(READING, "r-tfng", 0, TodayEvidence(competencies={"r-tfng": 2}))
    assert is_done(READING, "r-tfng", 0, TodayEvidence(competencies={"r-tfng": 3}))
    assert not is_done(READING, "r-tfng", 0, TodayEvidence(competencies={"r-other": 9}))


def test_minutes() -> None:
    assert estimate_minutes(REVIEW, 3) == 2  # at least 2
    assert estimate_minutes(REVIEW, 20) == 5
    assert estimate_minutes(REVIEW, 300) == 5  # one session of 20
    assert estimate_minutes(Target("vocab_band"), 0) == 5
    assert estimate_minutes(MILESTONE, 0) == 10
    assert estimate_minutes(WRITING, 0) == 40
    assert estimate_minutes(WRITING, 0, "writing-task1") == 20
    assert estimate_minutes(READING, 0) == 20
    assert estimate_minutes(Target("competency", skill="listening"), 0) == 15


def test_the_day_and_week_are_in_vietnam_time() -> None:
    late = datetime(2026, 11, 29, 18, 30, tzinfo=UTC)  # Monday 30 Nov, 01:30 in Vietnam
    assert local_day(late) == date(2026, 11, 30)
    begin, end = week_bounds(late)
    assert begin == datetime(2026, 11, 29, 17, 0, tzinfo=UTC)  # Monday 00:00 in Vietnam
    assert end == datetime(2026, 12, 6, 17, 0, tzinfo=UTC)


def test_study_week_counts_answers_per_day_and_never_a_streak() -> None:
    at = datetime(2026, 11, 26, 3, 0, tzinfo=UTC)  # Thursday 26 Nov
    stamps = [
        datetime(2026, 11, 23, 1, 0, tzinfo=UTC),  # Monday
        datetime(2026, 11, 23, 16, 59, tzinfo=UTC),  # Monday 23:59 in Vietnam
        datetime(2026, 11, 23, 17, 0, tzinfo=UTC),  # Tuesday 00:00 in Vietnam
        datetime(2026, 11, 26, 2, 0, tzinfo=UTC),  # today
    ]
    week = study_week(stamps, at)
    assert week[0].day.isoformat() == "2026-11-23"
    assert [d.answers for d in week] == [2, 1, 0, 1, 0, 0, 0]
    assert [d.studied for d in week] == [True, True, False, True, False, False, False]
    assert [d.is_today for d in week] == [False, False, False, True, False, False, False]
    assert [d.is_future for d in week] == [False] * 4 + [True] * 3
