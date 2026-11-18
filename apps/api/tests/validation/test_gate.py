"""Step V3: what a gate report rests on."""

import pytest

from app.validation.gate import basis, measured, process_supports, rated_by


def test_only_gold_or_construction_with_enough_cases_is_measured() -> None:
    assert measured(basis("gold", 50, 50))
    assert measured(basis("construction", 100, 40))
    few = basis("gold", 49, 50)
    assert not measured(few) and "49/50" in few["why_vi"] and "49 of 50" in few["why_en"]
    for truth in ("silver", "bronze", "feedback"):
        b = basis(truth, 500, 50)
        assert not measured(b) and b["why_en"]
    with pytest.raises(ValueError):
        basis("opinion", 1, 1)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        basis("gold", 1, 0)


def test_a_sheet_rated_by_a_teacher_is_declared_gold() -> None:
    assert rated_by("owner") == ("bronze", False)
    assert rated_by("teacher") == ("gold", True)
    assert basis("gold", 60, 50, declared=True)["declared"] is True
    with pytest.raises(ValueError):
        rated_by("friend")


def test_the_process_rule_uses_the_upper_bound() -> None:
    assert not process_supports(0, 50)["supports"]  # 0/50: upper bound about 7%
    assert process_supports(0, 72)["supports"]  # the smallest clean sample that passes
    assert not process_supports(0, 71)["supports"]
    assert not process_supports(3, 100)["supports"]
    assert process_supports(0, 0)["upper_95"] is None
