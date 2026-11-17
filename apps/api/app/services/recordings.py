"""Pronunciation recordings (specs/pronunciation/step-3.1.md): check, store, list, delete, purge.

The strict voice policy (owner, 17 Nov 2026): audio stays on our own database, is never sent to a
third party, is deleted after analysis (step 3.2) or after a day until then, unless the learner
chose to keep it. Only the learners in DRAFT_ITEM_LEARNERS may record until a privacy review.
"""

from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
import yaml  # type: ignore[import-untyped]
from fastapi import HTTPException
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, ConfigDict, Field

from app.pronunciation.quality import Quality, check
from app.services.backend import learner_uuid

CONSENT = "voice-v1"  # the notice the learner accepts (messages/vi.ts, pronunciation.consent)
RETENTION = timedelta(hours=24)  # until step 3.2 analyses and deletes recordings
MAX_BYTES = 600_000


class Sound(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    group: str
    ipa: str
    name_vi: str


class Prompt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^p\d{2,3}$")
    level: str
    targets: tuple[str, ...] = Field(min_length=1)
    text: str = Field(min_length=10, max_length=200)


def load_prompts(folder: Path) -> tuple[dict[str, Sound], list[Prompt]]:
    """Sounds and prompts; every prompt's targets must be known sounds."""
    sounds = {
        s.id: s
        for s in (
            Sound.model_validate(x)
            for x in yaml.safe_load((folder / "sounds.yaml").read_text(encoding="utf-8"))["sounds"]
        )
    }
    prompts = [
        Prompt.model_validate(x)
        for x in yaml.safe_load((folder / "prompts.yaml").read_text(encoding="utf-8"))["prompts"]
    ]
    for p in prompts:
        unknown = set(p.targets) - set(sounds)
        if unknown:
            raise ValueError(f"prompt {p.id}: unknown sounds {sorted(unknown)}")
    if len({p.id for p in prompts}) != len(prompts):
        raise ValueError("prompt ids must be unique")
    return sounds, prompts


def purge_expired(conn: psycopg.Connection[Any], now: datetime | None = None) -> int:
    """Delete recordings past their time; returns how many."""
    cur = conn.execute(
        "delete from speech_recordings where delete_after is not null and delete_after <= %s",
        (now or datetime.now(UTC),),
    )
    return cur.rowcount


class Recordings:
    def __init__(
        self,
        pool: Callable[[], ConnectionPool],
        folder: Path,
        draft_learners: str,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.pool = pool
        self.sounds, self.prompts = load_prompts(folder)
        self.owners = {learner_uuid(x.strip()) for x in draft_learners.split(",") if x.strip()}
        self.clock = clock

    def _owner(self, learner_id: str) -> UUID:
        learner = learner_uuid(learner_id)
        if learner not in self.owners:
            raise HTTPException(
                403,
                "Ghi âm hiện chỉ mở cho chủ dự án, cho đến khi việc lưu giữ giọng nói được xem xét "
                "về quyền riêng tư.",
            )
        return learner

    def can_record(self, learner_id: str) -> bool:
        return learner_uuid(learner_id) in self.owners

    def store(
        self, learner_id: str, prompt_id: str, consent: str, keep: bool, audio: bytes
    ) -> dict[str, Any]:
        learner = self._owner(learner_id)
        if consent != CONSENT:
            raise HTTPException(409, "Cần đồng ý với thông báo về ghi âm trước.")
        if prompt_id not in {p.id for p in self.prompts}:
            raise HTTPException(404, "Không tìm thấy câu đọc.")
        if len(audio) > MAX_BYTES:
            raise HTTPException(413, "Bản ghi quá dài.")
        quality: Quality = check(audio)
        out: dict[str, Any] = {"quality": asdict(quality), "id": None, "delete_after": None}
        if not quality.ok:
            return out  # advice only: a bad recording is never stored
        now = self.clock()
        delete_after = None if keep else now + RETENTION
        with self.pool().connection() as conn:
            purge_expired(conn, now)
            if not conn.execute("select 1 from learners where id=%s", (learner,)).fetchone():
                raise HTTPException(404, "Không tìm thấy người học.")
            row = conn.execute(
                "insert into speech_recordings(learner_id,prompt_id,consent,keep,audio,seconds,"
                "quality,created_at,delete_after) values (%s,%s,%s,%s,%s,%s,%s,%s,%s) returning id",
                (
                    learner,
                    prompt_id,
                    consent,
                    keep,
                    audio,
                    quality.seconds,
                    Jsonb(asdict(quality)),
                    now,
                    delete_after,
                ),
            ).fetchone()
        assert row is not None
        out["id"] = str(row[0])
        out["delete_after"] = delete_after.isoformat() if delete_after else None
        return out

    def list(self, learner_id: str) -> list[dict[str, Any]]:
        learner = learner_uuid(learner_id)
        with self.pool().connection() as conn:
            purge_expired(conn, self.clock())
            rows = conn.execute(
                "select id,prompt_id,keep,seconds,status,created_at,delete_after "
                "from speech_recordings where learner_id=%s order by created_at desc limit 50",
                (learner,),
            ).fetchall()
        return [
            {
                "id": str(r[0]),
                "prompt_id": r[1],
                "keep": r[2],
                "seconds": r[3],
                "status": r[4],
                "created_at": r[5].isoformat(),
                "delete_after": r[6].isoformat() if r[6] else None,
            }
            for r in rows
        ]

    def delete(self, learner_id: str, recording_id: str) -> None:
        learner = learner_uuid(learner_id)
        try:
            rid = UUID(recording_id)
        except ValueError:
            raise HTTPException(404, "Không tìm thấy bản ghi.") from None
        with self.pool().connection() as conn:
            cur = conn.execute(
                "delete from speech_recordings where id=%s and learner_id=%s", (rid, learner)
            )
        if cur.rowcount == 0:
            raise HTTPException(404, "Không tìm thấy bản ghi.")
