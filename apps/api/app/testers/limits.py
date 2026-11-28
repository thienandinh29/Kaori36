"""Daily limits for invited testers (specs/speaking/step-5.5.md), per Vietnam day."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

import psycopg
import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field

LIMITS_FILE = Path(__file__).resolve().parents[1] / "speaking" / "limits.yaml"
VIETNAM = ZoneInfo("Asia/Ho_Chi_Minh")


class DailyLimits(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    mock_tests_per_day: int = Field(ge=0)
    practice_tries_per_day: int = Field(ge=0)


class Limits(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    tester: DailyLimits


def load_limits(path: Path = LIMITS_FILE) -> DailyLimits:
    return Limits.model_validate(yaml.safe_load(path.read_text(encoding="utf-8"))).tester


def day_start(now: datetime) -> datetime:
    """The start of the Vietnam day containing `now`, as an aware UTC time."""
    local = now.astimezone(VIETNAM)
    return datetime(local.year, local.month, local.day, tzinfo=VIETNAM).astimezone(UTC)


def used_today(conn: psycopg.Connection[Any], learner: UUID, now: datetime) -> tuple[int, int]:
    """(mock tests, practice tries) the learner started today, Vietnam time."""
    start = day_start(now)
    row = conn.execute(
        "select count(*) filter (where mode='exam'), count(*) filter (where mode='guided') "
        "from speaking_tests where learner_id=%s and started_at >= %s and started_at < %s",
        (learner, start, start + timedelta(days=1)),
    ).fetchone()
    assert row is not None
    return int(row[0]), int(row[1])
