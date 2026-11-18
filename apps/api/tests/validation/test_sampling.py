"""Step V2: stratified samples."""

import pytest

from app.validation.sampling import everything, stratified


def test_all_disagreed_then_agreed_fill() -> None:
    s = stratified(["d1", "d2"], [f"a{i}" for i in range(10)], 5, seed=1)
    assert len(s.item_ids) == 5 and set(s.item_ids) >= {"d1", "d2"}
    assert sum(v == "agreed" for v in s.strata.values()) == 3
    assert s.population == {"disagreed": 2, "agreed": 10}


def test_same_seed_same_sample_and_order() -> None:
    args = (["d1"], [f"a{i}" for i in range(20)], 6)
    assert stratified(*args, seed=3) == stratified(*args, seed=3)
    assert stratified(*args, seed=3).item_ids != stratified(*args, seed=4).item_ids


def test_too_many_disagreed_are_sampled() -> None:
    s = stratified([f"d{i}" for i in range(9)], ["a"], 4, seed=1)
    assert len(s.item_ids) == 4 and set(s.strata.values()) == {"disagreed"}


def test_an_item_in_both_lists_counts_as_disagreed() -> None:
    s = stratified(["x"], ["x", "y"], 5, seed=1)
    assert s.strata == {"x": "disagreed", "y": "agreed"}
    assert s.population == {"disagreed": 1, "agreed": 1}


def test_everything_and_bad_size() -> None:
    assert sorted(everything(["b", "a", "a"], 1).item_ids) == ["a", "b"]
    with pytest.raises(ValueError):
        stratified([], [], 0, seed=1)
