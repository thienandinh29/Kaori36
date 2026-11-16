"""Plans and their daily limits (specs/plans): free, pro, owner, decided by the server."""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import psycopg
import pytest
from fastapi import HTTPException
from psycopg_pool import ConnectionPool

from app.services import plans as plans_module
from app.services.budget import Budget
from app.services.plans import (
    PLANS_FILE,
    Plans,
    load_limits,
    owners_from,
    plans_from_settings,
    set_plan,
)
from app.services.writing import CONSENT, WritingService

WRITING = Path(__file__).resolve().parents[3] / "data" / "writing"
NOW = datetime(2026, 11, 20, 3, 0, tzinfo=UTC)


def test_the_committed_limits_load_and_rise_with_the_plan() -> None:
    limits = load_limits()
    assert limits.free.essays_per_day < limits.pro.essays_per_day < limits.owner.essays_per_day
    calls = (limits.free, limits.pro, limits.owner)
    assert [c.model_calls_per_day for c in calls] == sorted(c.model_calls_per_day for c in calls)


def test_env_numbers_override_only_the_free_plan_and_only_when_set() -> None:
    base = load_limits()
    over = load_limits(free_essays=20, free_calls=50)
    assert (over.free.essays_per_day, over.free.model_calls_per_day) == (20, 50)
    assert over.pro == base.pro and over.owner == base.owner
    unset = SimpleNamespace(
        model_fields_set=set(), writing_daily_essays=99, llm_daily_calls_per_learner=99,
        draft_item_learners="",
    )  # fmt: skip
    assert plans_from_settings(unset).limits.free == base.free  # defaults are not overrides
    explicit = SimpleNamespace(**{**vars(unset), "model_fields_set": {"writing_daily_essays"}})
    assert plans_from_settings(explicit).limits.free.essays_per_day == 99


def test_a_broken_limits_file_is_refused(tmp_path: Path) -> None:
    bad = tmp_path / "plans.yaml"
    bad.write_text(PLANS_FILE.read_text().replace("essays_per_day: 3", "essays_per_day: -1"))
    with pytest.raises(ValueError):
        load_limits(bad)


def test_the_owner_list_ignores_anything_that_is_not_an_id() -> None:
    a = "00000000-0000-4000-8000-000000000001"
    assert owners_from(f" {a} , nonsense,,") == frozenset({UUID(a)})


@pytest.fixture
def db(database_url: str) -> Iterator[tuple[str, UUID, UUID, UUID]]:
    with psycopg.connect(database_url) as conn:
        ids = [
            conn.execute(
                "insert into learners(display_name) values (%s) returning id", (name,)
            ).fetchone()[0]  # type: ignore[index]
            for name in ("Free", "Pro", "Owner")
        ]
    yield database_url, ids[0], ids[1], ids[2]


def test_plans_are_resolved_by_the_server(db: tuple[str, UUID, UUID, UUID]) -> None:
    url, free, pro, owner = db
    plans = Plans(load_limits(), frozenset({owner}))
    with psycopg.connect(url, autocommit=True) as conn:
        set_plan(conn, pro, "pro")
        assert plans.plan_of(conn, free) == "free"
        assert plans.plan_of(conn, pro) == "pro"
        assert plans.plan_of(conn, owner) == "owner"
        assert plans.plan_of(conn, UUID(int=12345)) == "free"  # unknown learner: the safest plan
        with pytest.raises(ValueError, match="owner comes from"):
            set_plan(conn, free, "owner")
        with pytest.raises(ValueError):
            set_plan(conn, free, "gold")
        with pytest.raises(LookupError):
            set_plan(conn, UUID(int=12345), "pro")


def test_the_essay_limit_follows_the_plan(db: tuple[str, UUID, UUID, UUID]) -> None:
    url, free, pro, owner = db
    limits = load_limits(free_essays=1)
    plans = Plans(limits, frozenset({owner}))
    pool = ConnectionPool(url, open=True)
    with psycopg.connect(url, autocommit=True) as conn:
        set_plan(conn, pro, "pro")
    # The prompts are drafts, visible only to listed learners: list all three for this test; only
    # one of them is the owner for the plans.
    seen = ",".join(map(str, (free, pro, owner)))
    svc = WritingService(lambda: pool, WRITING, draft_learners=seen, plans=plans)
    try:
        svc.submit(str(free), "t2-plastic-ban", "One essay.", CONSENT, now=NOW)
        with pytest.raises(HTTPException) as err:
            svc.submit(str(free), "t2-plastic-ban", "Two essays.", CONSENT, now=NOW)
        assert err.value.status_code == 429 and "gói Miễn phí" in str(err.value.detail)
        for learner in (pro, owner):  # pro and owner are not stopped at the free limit
            svc.submit(str(learner), "t2-plastic-ban", "One essay.", CONSENT, now=NOW)
            svc.submit(str(learner), "t2-plastic-ban", "Two essays.", CONSENT, now=NOW)
    finally:
        pool.close()


def test_the_model_call_limit_follows_the_plan(db: tuple[str, UUID, UUID, UUID]) -> None:
    from app.writing.model_calls import BudgetExceeded, Prices, WritingModel

    url, free, _, owner = db
    plans = Plans(load_limits(free_calls=1), frozenset({owner}))
    with psycopg.connect(url, autocommit=True) as conn:
        for learner in (free, owner):
            conn.execute(
                "insert into llm_calls(tier,model,latency_ms,cost_usd,success,learner_id,task,"
                "input_tokens,output_tokens,created_at) values ('free','m',1,0,true,%s,'t',1,1,%s)",
                (learner, NOW),
            )

    class NoGateway:
        routing = adapters = task_limits = None

    model = WritingModel(
        NoGateway(),  # type: ignore[arg-type]
        url, Budget(10.0, 1000), Prices(0, 0), clock=lambda: NOW, plans=plans,
    )  # fmt: skip
    with pytest.raises(BudgetExceeded):  # free: 1 call a day, already used
        model.complete(free, "t", "s", "u", Budget)  # type: ignore[type-var]
    # the owner is past the budget check (the fake gateway then fails, which is not the budget)
    with pytest.raises(Exception) as err:
        model.complete(owner, "t", "s", "u", Budget)  # type: ignore[type-var]
    assert not isinstance(err.value, BudgetExceeded)


def test_the_owners_tool_sets_and_shows_a_plan(
    db: tuple[str, UUID, UUID, UUID], capsys: pytest.CaptureFixture[str]
) -> None:
    url, free, _, _ = db
    assert plans_module.main(["set", str(free), "pro"], database_url=url) == 0
    assert "pro (Pro)" in capsys.readouterr().out
    assert plans_module.main(["show", str(free)], database_url=url) == 0
    assert plans_module.main(["set", str(free), "owner"], database_url=url) == 1
    assert plans_module.main(["show", "not-an-id"], database_url=url) == 2
    assert plans_module.main(["wat"], database_url=url) == 2
