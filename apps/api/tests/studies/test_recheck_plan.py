"""FORGET-001: which grammar nodes are re-checked, and with which item (pure)."""

from datetime import UTC, datetime, timedelta

from app.studies.recheck import Known, due, pick_item

NOW = datetime(2026, 11, 20, 9, 0, tzinfo=UTC)


def k(node: str, p: float, days_ago: float) -> Known:
    return Known(node, p, NOW - timedelta(days=days_ago))


def test_known_old_enough_not_recently_checked_oldest_first_capped() -> None:
    known = [k("a", 0.95, 6), k("b", 0.95, 12), k("c", 0.85, 30), k("d", 0.92, 3),
             k("e", 0.99, 9), k("f", 0.9, 7)]  # fmt: skip
    assert [x.node for x in due(known, {}, 0, NOW)] == ["b", "e", "f"]  # cap of 3
    assert [x.node for x in due(known, {}, 2, NOW)] == ["b"]  # room for one this week
    assert due(known, {}, 3, NOW) == []
    recent = {"b": NOW - timedelta(days=10), "e": NOW - timedelta(days=40)}
    assert [x.node for x in due(known, recent, 0, NOW)] == ["e", "f", "a"]


def test_pick_item_prefers_fresh_then_least_recent() -> None:
    t = NOW - timedelta(days=1)
    assert pick_item(["i1", "i2", "i3"], {"i1": t}) == "i2"
    assert pick_item(["i1", "i2"], {"i1": t, "i2": t - timedelta(days=5)}) == "i2"
    assert pick_item([], {}) is None
