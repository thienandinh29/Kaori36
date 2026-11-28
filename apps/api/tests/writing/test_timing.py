"""Seconds per stage of an essay's analysis (app/writing/timing.py)."""

import pytest

from app.writing.timing import KEY, timed


def test_a_stage_adds_its_seconds_and_repeats_add_up() -> None:
    result: dict[str, object] = {}
    with timed(result, "a"):
        pass
    with timed(result, "a"):
        pass
    with timed(result, "b"):
        pass
    stages = result[KEY]
    assert isinstance(stages, dict) and set(stages) == {"a", "b"}
    assert all(isinstance(v, float) and v >= 0 for v in stages.values())


def test_a_stage_that_raises_is_still_timed_and_the_error_passes() -> None:
    result: dict[str, object] = {}
    with pytest.raises(ValueError), timed(result, "boom"):
        raise ValueError("x")
    assert "boom" in result[KEY]  # type: ignore[operator]


def test_the_key_starts_with_an_underscore_so_it_never_reaches_the_browser() -> None:
    assert KEY.startswith("_")
