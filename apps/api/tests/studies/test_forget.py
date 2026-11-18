"""FORGET-001: the replay, calibration and re-check reports (pure)."""

from datetime import UTC, datetime, timedelta

from fsrs import Card

from app.engine import srs
from app.studies.forget import (
    Prediction,
    Recheck,
    Review,
    delayed,
    recheck_report,
    replay,
    report,
    retention,
    scores,
    weakest_words,
)

T0 = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)


def test_replay_matches_the_service_and_skips_the_first_answer() -> None:
    reviews = [
        Review("core/a:noun", "meaning", True, T0),
        Review("core/a:noun", "gapfill", True, T0 + timedelta(days=3)),
        Review("core/a:noun", "meaning", False, T0 + timedelta(days=9)),
        Review("core/b:verb", "meaning", True, T0 + timedelta(hours=1)),
    ]
    preds = replay(reviews)
    assert [(p.card, p.kind, p.correct) for p in preds] == [
        ("core/a:noun", "gapfill", True),
        ("core/a:noun", "meaning", False),
    ]
    assert [round(p.elapsed_days, 3) for p in preds] == [3.0, 6.0]
    # The same numbers by hand: new card, review, then the recall FSRS predicts 3 days later.
    state = srs.review(srs.new_card(T0).state, True, T0).state
    expected = srs.make_scheduler().get_card_retrievability(
        Card.from_dict(state), current_datetime=T0 + timedelta(days=3)
    )
    assert abs(preds[0].predicted - expected) < 1e-9
    # A correct review at day 3 raised stability, so day 9 need not be lower: only a valid range.
    assert all(0 < x.predicted <= 1 for x in preds)


def p(
    predicted: float, correct: bool, days: float = 6, card: str = "c", kind: str = "meaning"
) -> Prediction:
    return Prediction(card, kind, predicted, days, correct)


def test_scores_by_decile_brier_log_loss_and_ece() -> None:
    preds = [p(0.95, True), p(0.95, True), p(0.95, False), p(0.55, True), p(0.55, False)]
    s = scores(preds)
    assert s["n"] == 5 and s["recall"]["k"] == 3
    top, mid = s["deciles"][1], s["deciles"][0]
    assert (top["range"], top["mean_predicted"], top["actual"]["k"], top["actual"]["n"]) == (
        [0.9, 1.0], 0.95, 2, 3)  # fmt: skip
    assert (mid["range"], mid["actual"]["k"], mid["actual"]["n"]) == ([0.5, 0.6], 1, 2)
    # Brier by hand: (0.05^2*2 + 0.95^2 + 0.45^2 + 0.55^2) / 5
    assert s["brier"]["fsrs"] == round((0.0025 * 2 + 0.9025 + 0.2025 + 0.3025) / 5, 4)
    assert s["brier"]["constant"] == round((0.16 * 3 + 0.36 * 2) / 5, 4)  # constant 0.6
    # ECE: 3/5*|0.95-2/3| + 2/5*|0.55-0.5|
    assert s["ece"] == round(3 / 5 * abs(0.95 - 2 / 3) + 2 / 5 * 0.05, 4)
    assert scores([]) == {"n": 0}


def test_delayed_retention_and_weakest() -> None:
    preds = [p(0.9, True, 4), p(0.9, False, 6, "w1"), p(0.9, False, 7, "w1"),
             p(0.9, True, 8, "w1"), p(0.9, True, 9, "w2", "gapfill"), p(0.9, True, 11)]  # fmt: skip
    week = delayed(preds)
    assert len(week) == 4
    by_kind = retention(week, lambda x: x.kind)
    assert (by_kind["meaning"]["k"], by_kind["meaning"]["n"]) == (1, 3)
    weak = weakest_words(week)
    assert [w["card"] for w in weak] == ["w1"] and weak[0]["k"] == 1


def test_recheck_report_and_minimum() -> None:
    few = recheck_report([Recheck("n", True, 6), Recheck("n", False, 20)])
    assert few["reading"] == "not enough re-checks yet"
    assert set(few["by_days_since_evidence"]) == {"5-7", "15+"}
    low = recheck_report([Recheck("n", i < 8, 6) for i in range(25)])  # 8/25
    assert low["reading"].startswith("below the bar")
    out = report([], {}, [])
    assert out["minimum_met"] is False and out["vocabulary"]["after_a_week"] == {"n": 0}
