"""Step 5.5: invite links, sessions and switching a tester off, against a real database."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import psycopg
import pytest

from app.testers import store
from app.testers.limits import day_start, load_limits

NOW = datetime(2026, 12, 1, 9, 0, tzinfo=UTC)


@pytest.fixture
def conn(database_url: str) -> Iterator[psycopg.Connection]:
    with psycopg.connect(database_url) as c:
        yield c
        c.rollback()


def test_an_invite_works_once_and_gives_a_session_that_names_the_learner(conn) -> None:  # type: ignore[no-untyped-def]
    tester, learner = store.create_tester(conn, "Mai (bạn cùng lớp)")
    token = store.invite(conn, tester, NOW)
    got = store.redeem(conn, token, NOW + timedelta(hours=1))
    assert got is not None and got[0] == learner and got[2] == "Mai (bạn cùng lớp)"
    assert store.redeem(conn, token, NOW + timedelta(hours=2)) is None  # once only
    assert store.session_learner(conn, got[1], NOW + timedelta(days=2)) == learner
    assert store.is_tester(conn, learner)
    stored = conn.execute("select token_hash from tester_invites").fetchall()
    assert all(token not in h and len(h) == 64 for (h,) in stored)  # only a hash is kept


def test_an_expired_unknown_or_malformed_link_does_not_work(conn) -> None:  # type: ignore[no-untyped-def]
    tester, _ = store.create_tester(conn, "An")
    token = store.invite(conn, tester, NOW, days=7)
    assert store.redeem(conn, token, NOW + timedelta(days=7, seconds=1)) is None  # expired
    assert store.redeem(conn, "not-a-real-token-at-all-xxxxxxxx", NOW) is None
    assert store.redeem(conn, "", NOW) is None
    assert store.session_learner(conn, None, NOW) is None
    assert store.session_learner(conn, "x" * 43, NOW) is None


def test_a_session_ends_after_30_days_and_when_the_tester_is_switched_off(conn) -> None:  # type: ignore[no-untyped-def]
    tester, learner = store.create_tester(conn, "Binh")
    got = store.redeem(conn, store.invite(conn, tester, NOW), NOW)
    assert got is not None
    assert store.session_learner(conn, got[1], NOW + timedelta(days=29)) == learner
    assert store.session_learner(conn, got[1], NOW + timedelta(days=31)) is None  # expired
    again = store.redeem(conn, store.invite(conn, tester, NOW), NOW)
    assert again is not None
    assert store.revoke(conn, tester, NOW)
    assert store.session_learner(conn, again[1], NOW) is None  # ended at once
    with pytest.raises(ValueError, match="switched off"):
        store.invite(conn, tester, NOW)  # and no new link
    other, _ = store.create_tester(conn, "Chi")
    link = store.invite(conn, other, NOW)
    store.revoke(conn, other, NOW)
    assert store.redeem(conn, link, NOW) is None  # a link made before it was switched off


def test_the_research_notice_is_recorded_only_for_the_known_version(conn) -> None:  # type: ignore[no-untyped-def]
    tester, learner = store.create_tester(conn, "Dung")
    assert store.info(conn, learner)["research_consented"] is False  # type: ignore[index]
    with pytest.raises(ValueError):
        store.research_consent(conn, learner, "research-v9", NOW)
    store.research_consent(conn, learner, store.RESEARCH_NOTICE, NOW)
    assert store.info(conn, learner)["research_consented"] is True  # type: ignore[index]
    assert store.info(conn, tester) is None  # a tester id is not a learner id
    with pytest.raises(ValueError):
        store.create_tester(conn, "  ")


def test_the_day_is_the_vietnam_day_and_the_limits_file_loads() -> None:
    # 18:00 UTC on 1 Dec is 01:00 on 2 Dec in Vietnam (UTC+7): that day began at 17:00 UTC
    late = datetime(2026, 12, 1, 18, 0, tzinfo=UTC)
    assert day_start(late) == datetime(2026, 12, 1, 17, 0, tzinfo=UTC)
    early = datetime(2026, 12, 1, 16, 0, tzinfo=UTC)  # 23:00 on the 1st in Vietnam
    assert day_start(early) == datetime(2026, 11, 30, 17, 0, tzinfo=UTC)
    limits = load_limits()
    assert (limits.mock_tests_per_day, limits.practice_tries_per_day) == (3, 20)
