"""Plans and their daily limits (specs/plans): free, pro, owner. Decided by the server only.

python -m app.services.plans show <learner_id>
python -m app.services.plans set <learner_id> free|pro
"""

import sys
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

import psycopg
import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field

Plan = Literal["free", "pro", "owner"]
STORED: tuple[str, ...] = (
    "free",
    "pro",
)  # owner comes from DRAFT_ITEM_LEARNERS, never the database
PLANS_FILE = Path(__file__).resolve().parents[1] / "plans.yaml"
NAMES_VI: dict[Plan, str] = {"free": "Miễn phí", "pro": "Pro", "owner": "Chủ dự án"}


class Limits(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    essays_per_day: int = Field(ge=0)
    model_calls_per_day: int = Field(ge=0)


class PlanLimits(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    free: Limits
    pro: Limits
    owner: Limits

    def of(self, plan: Plan) -> Limits:
        return {"free": self.free, "pro": self.pro, "owner": self.owner}[plan]


def load_limits(
    path: Path = PLANS_FILE,
    *,
    free_essays: int | None = None,
    free_calls: int | None = None,
) -> PlanLimits:
    """The limits file, with the free plan's numbers overridden when the owner set them in .env."""
    limits = PlanLimits.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    free = limits.free.model_copy(
        update={
            k: v
            for k, v in (("essays_per_day", free_essays), ("model_calls_per_day", free_calls))
            if v is not None
        }
    )
    return limits.model_copy(update={"free": free})


@dataclass(frozen=True)
class Plans:
    limits: PlanLimits
    owners: frozenset[UUID]

    def plan_of(self, conn: psycopg.Connection[Any], learner: UUID) -> Plan:
        if learner in self.owners:
            return "owner"
        row = conn.execute("select plan from learners where id=%s", (learner,)).fetchone()
        return "pro" if row is not None and row[0] == "pro" else "free"

    def limits_of(self, conn: psycopg.Connection[Any], learner: UUID) -> tuple[Plan, Limits]:
        plan = self.plan_of(conn, learner)
        return plan, self.limits.of(plan)


def owners_from(listed: str) -> frozenset[UUID]:
    """The owner list (DRAFT_ITEM_LEARNERS), comma-separated; non-ids are ignored."""
    out = set()
    for x in listed.split(","):
        try:
            out.add(UUID(x.strip()))
        except ValueError:
            continue
    return frozenset(out)


def plans_from_settings(settings: Any) -> Plans:
    """Plans from the app settings; .env values override the free plan only when actually set."""
    explicit: Collection[str] = settings.model_fields_set
    return Plans(
        load_limits(
            free_essays=settings.writing_daily_essays
            if "writing_daily_essays" in explicit
            else None,
            free_calls=settings.llm_daily_calls_per_learner
            if "llm_daily_calls_per_learner" in explicit
            else None,
        ),
        owners_from(settings.draft_item_learners),
    )


def set_plan(conn: psycopg.Connection[Any], learner: UUID, plan: str) -> None:
    if plan not in STORED:
        raise ValueError(
            f"plan must be one of {', '.join(STORED)} (owner comes from DRAFT_ITEM_LEARNERS)"
        )
    row = conn.execute(
        "update learners set plan=%s where id=%s returning id", (plan, learner)
    ).fetchone()
    if row is None:
        raise LookupError(f"no learner {learner}")


def main(argv: list[str] | None = None, *, database_url: str | None = None) -> int:
    from app.config import get_settings

    args = sys.argv[1:] if argv is None else argv
    if len(args) < 2 or args[0] not in ("show", "set") or (args[0] == "set" and len(args) != 3):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    settings = get_settings()
    try:
        learner = UUID(args[1])
    except ValueError:
        print(f"not a learner id: {args[1]}", file=sys.stderr)
        return 2
    plans = plans_from_settings(settings)
    with psycopg.connect(database_url or settings.database_url) as conn:
        try:
            if args[0] == "set":
                set_plan(conn, learner, args[2])
        except (ValueError, LookupError) as exc:
            print(exc, file=sys.stderr)
            return 1
        plan, limits = plans.limits_of(conn, learner)
    print(f"{learner}: {plan} ({NAMES_VI[plan]}): {limits.essays_per_day} essays/day, "
          f"{limits.model_calls_per_day} model calls/day")  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
