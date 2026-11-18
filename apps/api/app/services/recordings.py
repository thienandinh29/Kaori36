"""Pronunciation recordings (specs/pronunciation/step-3.1.md): check, store, list, delete, purge.

The strict voice policy (owner, 17 Nov 2026): audio stays on our own database, is never sent to a
third party, is deleted after analysis (step 3.2) or after a day until then, unless the learner
chose to keep it. Only the learners in DRAFT_ITEM_LEARNERS may record until a privacy review.
"""

from collections.abc import Callable, Sequence
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID

import psycopg
import yaml  # type: ignore[import-untyped]
from fastapi import HTTPException
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, ConfigDict, Field

from app.engine.milestones import ASSUMED_KNOWN
from app.pronunciation.canonical import Word, load_canonical, phone_set
from app.pronunciation.canonical import check as check_canonical
from app.pronunciation.marks import load_applied, marks
from app.pronunciation.quality import Quality, check
from app.services.backend import learner_uuid

if TYPE_CHECKING:
    from app.pronunciation.analysis import Evidence


class TargetLabel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target: int = Field(ge=0, le=200)
    label: Literal["right", "wrong", "unsure"]


class LabelsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    labels: list[TargetLabel] = Field(min_length=1, max_length=200)


def recording_uuid(recording_id: str) -> UUID:
    try:
        return UUID(recording_id)
    except ValueError:
        raise HTTPException(404, "Không tìm thấy bản ghi.") from None


CONSENT = "voice-v1"  # the notice the learner accepts (messages/vi.ts, pronunciation.consent)
RETENTION = timedelta(hours=24)  # until step 3.2 analyses and deletes recordings
MAX_BYTES = 600_000


class Sound(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    group: str
    ipa: str
    name_vi: str
    tip_vi: str | None = None  # the owner's tip for this sound (step 3.4); none yet


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


PRONUNCIATION_COURSE = "english-pronunciation"


def load_evidence(folder: Path, courses_dir: Path) -> "Evidence":
    """The pronunciation course and applied groups; refused if its nodes and the groups differ."""
    from app.curriculum.course import load_course
    from app.pronunciation.analysis import Evidence

    sounds, _ = load_prompts(folder)
    course = load_course(courses_dir / f"{PRONUNCIATION_COURSE}.yaml")
    nodes = {c.slug for c in course.concepts if c.part_of}
    groups = {s.group for s in sounds.values()}
    if nodes != groups:
        raise ValueError(f"pronunciation nodes {sorted(nodes)} differ from groups {sorted(groups)}")
    return Evidence(
        course, {s.id: s.group for s in sounds.values()}, load_applied(folder / "thresholds.json")
    )


def load_checked_canonical(folder: Path, prompts: list[Prompt]) -> dict[str, list[Word]]:
    """The prompts' canonical phones, refused at start-up if any prompt is inconsistent."""
    canonical = load_canonical(folder / "canonical.yaml")
    problems = check_canonical(
        canonical,
        {p.id: (p.text, p.targets) for p in prompts},
        phone_set(folder / "model-phones.txt"),
    )
    if problems:
        raise ValueError("; ".join(problems))
    return canonical


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
        courses_dir: Path | None = None,
    ) -> None:
        self.pool = pool
        self.sounds, self.prompts = load_prompts(folder)
        # The pronunciation nodes (step 3.4b), shown as progress; checked against the groups.
        self.evidence = load_evidence(folder, courses_dir) if courses_dir else None
        self.canonical = load_checked_canonical(folder, self.prompts)
        # Applied thresholds (step 3.4): none until the owner applies a passing 3.3b report.
        self.applied = load_applied(folder / "thresholds.json")
        self.group_of = {s.id: s.group for s in self.sounds.values()}
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

    def progress(self, learner_id: str) -> list[dict[str, Any]]:
        """The pronunciation nodes and the learner's mastery; null until a node has evidence."""
        if self.evidence is None:
            return []
        course = self.evidence.course
        with self.pool().connection() as conn:
            rows = conn.execute(
                "select c.slug, m.p_known from mastery m join concepts c on c.id=m.concept_id "
                "join subjects s on s.id=c.subject_id where m.learner_id=%s and s.slug=%s",
                (learner_uuid(learner_id), course.slug),
            ).fetchall()
        known = {r[0]: round(float(r[1]), 3) for r in rows}
        return [
            {
                "node": c.slug,
                "name_vi": c.name_vi,
                "p_known": known.get(c.slug),
                "known": known.get(c.slug, 0.0) >= ASSUMED_KNOWN,
                "measured": c.slug in self.evidence.applied,
            }
            for c in course.concepts
            if c.part_of
        ]

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

    def get(self, learner_id: str, recording_id: str) -> dict[str, Any]:
        """One of the learner's recordings with its analysis (scores, never a verdict yet)."""
        learner, rid = learner_uuid(learner_id), recording_uuid(recording_id)
        with self.pool().connection() as conn:
            row = conn.execute(
                "select prompt_id,keep,seconds,status,created_at,delete_after,analysis,failure "
                "from speech_recordings where id=%s and learner_id=%s",
                (rid, learner),
            ).fetchone()
            labels = conn.execute(
                "select target,label from speech_labels where recording_id=%s order by target",
                (rid,),
            ).fetchall()
        if row is None:
            raise HTTPException(404, "Không tìm thấy bản ghi.")
        return {
            "id": recording_id,
            "prompt_id": row[0],
            "keep": row[1],
            "seconds": row[2],
            "status": row[3],
            "created_at": row[4].isoformat(),
            "delete_after": row[5].isoformat() if row[5] else None,
            "analysis": row[6],
            "failed": row[7] is not None,
            "labels": [{"target": t, "label": label} for t, label in labels],
            "marks": marks(row[6]["targets"], self.group_of, self.applied) if row[6] else [],
        }

    def audio(self, learner_id: str, recording_id: str) -> bytes:
        """The WAV of a kept recording, for the owner's labelling (3.3b); 404 when not kept."""
        learner, rid = learner_uuid(learner_id), recording_uuid(recording_id)
        with self.pool().connection() as conn:
            row = conn.execute(
                "select audio from speech_recordings where id=%s and learner_id=%s and keep "
                "and octet_length(audio) > 0",
                (rid, learner),
            ).fetchone()
        if row is None:
            raise HTTPException(404, "Bản ghi này không được giữ lại nên không nghe lại được.")
        return bytes(row[0])

    def label(self, learner_id: str, recording_id: str, labels: Sequence[TargetLabel]) -> None:
        """Save the owner's labels on an analysed recording's target sounds (3.3b)."""
        learner, rid = learner_uuid(learner_id), recording_uuid(recording_id)
        if not self.can_record(learner_id):
            raise HTTPException(403, "Chỉ chủ dự án gán nhãn bản ghi.")
        with self.pool().connection() as conn:
            row = conn.execute(
                "select analysis from speech_recordings where id=%s and learner_id=%s "
                "and status='analysed'",
                (rid, learner),
            ).fetchone()
            if row is None:
                raise HTTPException(404, "Không tìm thấy bản ghi đã phân tích.")
            count = len(row[0]["targets"])
            if any(x.target >= count for x in labels):
                raise HTTPException(422, "Vị trí âm không có trong kết quả phân tích.")
            for x in labels:
                conn.execute(
                    "insert into speech_labels(recording_id,target,label,labelled_at) "
                    "values (%s,%s,%s,%s) on conflict (recording_id,target) "
                    "do update set label=excluded.label, labelled_at=excluded.labelled_at",
                    (rid, x.target, x.label, self.clock()),
                )

    def delete(self, learner_id: str, recording_id: str) -> None:
        learner, rid = learner_uuid(learner_id), recording_uuid(recording_id)
        with self.pool().connection() as conn:
            cur = conn.execute(
                "delete from speech_recordings where id=%s and learner_id=%s", (rid, learner)
            )
        if cur.rowcount == 0:
            raise HTTPException(404, "Không tìm thấy bản ghi.")
