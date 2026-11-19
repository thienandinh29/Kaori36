"""The owner's review queue for generated Reading questions (specs/listening-reading/step-4.2c.md).

Only the owner (the ids in DRAFT_ITEM_LEARNERS) may list or decide. Approval is refused when the
passage is missing or changed, or the item no longer passes the code checks: what the owner
approves is exactly what a learner will later see.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml  # type: ignore[import-untyped]
from fastapi import HTTPException
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from app.reading.items import Item, check, learner_view
from app.reading.pipeline import sha256 as passage_sha256
from app.services.backend import learner_uuid
from app.validation.store import LabelIn, add_label

STATUSES = ("needs_review", "verified", "approved", "rejected")
Reason = Literal["wrong_key", "not_answerable", "two_answers", "unclear", "other"]
_ITEM: TypeAdapter[Any] = TypeAdapter(Item)


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["approve", "reject"]
    reason: Reason | None = None
    note: str | None = Field(default=None, max_length=500)


def _signature(folder: Path) -> tuple[tuple[str, int, int], ...]:
    """What the folder holds now: a file's name, modification time and size."""
    files = sorted(folder.glob("*.yaml")) if folder.is_dir() else []
    return tuple((p.name, (st := p.stat()).st_mtime_ns, st.st_size) for p in files)


@lru_cache(maxsize=8)
def _read(folder: Path, signature: tuple[tuple[str, int, int], ...]) -> dict[str, tuple[str, str]]:
    out: dict[str, tuple[str, str]] = {}
    for name, _, _ in signature:
        raw = yaml.safe_load((folder / name).read_text(encoding="utf-8"))
        if isinstance(raw, dict) and raw.get("slug") and raw.get("text"):
            out[str(raw["slug"])] = (str(raw.get("title") or raw["slug"]), str(raw["text"]))
    return out


def read_texts(folder: Path) -> dict[str, tuple[str, str]]:
    """Text slug -> (title, passage), parsed again only when a file changes.

    Answering and reviewing read the bank on every request; parsing every YAML file each time
    made an answer take about 0.3 s with 30 texts (found by tests/reading/test_bank_simulation.py).
    """
    return dict(_read(folder, _signature(folder)))


def load_passages(folder: Path) -> dict[str, str]:
    """Text slug -> passage, from the bank's folder (raw entries; serving also needs the bank)."""
    return {slug: text for slug, (_, text) in read_texts(folder).items()}


class ReadingReview:
    def __init__(
        self,
        pool: Callable[[], ConnectionPool],
        texts_dir: Path,
        draft_learners: str,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.pool = pool
        self.texts_dir = texts_dir
        self.owners = {learner_uuid(x.strip()) for x in draft_learners.split(",") if x.strip()}
        self.clock = clock

    def _owner(self, learner_id: str) -> None:
        if learner_uuid(learner_id) not in self.owners:
            raise HTTPException(403, "Chỉ chủ dự án duyệt câu hỏi.")

    def queue(self, learner_id: str, status: str) -> dict[str, Any]:
        self._owner(learner_id)
        if status not in STATUSES:
            raise HTTPException(422, "Trạng thái không hợp lệ.")
        passages = load_passages(self.texts_dir)
        with self.pool().connection() as conn:
            counts: dict[str, int] = dict(
                conn.execute(
                    "select status, count(*) from reading_items group by status"
                ).fetchall()
            )
            rows = conn.execute(
                "select id,text_slug,passage_sha256,item,checker_answer,checker_model,review_note "
                "from reading_items where status=%s order by generated_at, id limit 50",
                (status,),
            ).fetchall()
        items = []
        for item_id, slug, digest, data, answer, model, note in rows:
            item = _ITEM.validate_python(data)
            passage = passages.get(slug)
            current = passage is not None and passage_sha256(passage) == digest
            items.append({
                "id": item_id, "text": slug, "kind": item.kind, "skill": item.skill,
                "question": learner_view(item), "key": key_of(item),
                "evidence": list(item.evidence),
                "checker_answer": answer, "checker_model": model, "note": note,
                "passage": passage if current else None,
            })  # fmt: skip
        return {"counts": {s: int(counts.get(s, 0)) for s in STATUSES}, "items": items}

    def decide(self, learner_id: str, item_id: str, body: Decision) -> dict[str, str]:
        self._owner(learner_id)
        if body.decision == "reject" and body.reason is None:
            raise HTTPException(422, "Hãy chọn lý do loại.")
        with self.pool().connection() as conn:
            row = conn.execute(
                "select text_slug,passage_sha256,item,status from reading_items where id=%s "
                "for update",
                (item_id,),
            ).fetchone()
            if row is None:
                raise HTTPException(404, "Không tìm thấy câu hỏi.")
            slug, digest, data, status = row
            if status not in ("verified", "needs_review"):
                raise HTTPException(409, "Câu hỏi này đã được duyệt hoặc chưa qua bước kiểm tra.")
            if body.decision == "approve":
                passage = load_passages(self.texts_dir).get(slug)
                if passage is None or passage_sha256(passage) != digest:
                    raise HTTPException(
                        422, "Bài đọc không còn hoặc đã thay đổi; không duyệt được."
                    )
                problems = check(_ITEM.validate_python(data), passage)
                if problems:
                    raise HTTPException(422, "Câu hỏi không qua kiểm tra: " + "; ".join(problems))
            new = "approved" if body.decision == "approve" else "rejected"
            note = (f"[{body.reason}] " if body.reason else "") + (body.note or "")
            conn.execute(
                "update reading_items set status=%s, reviewed_at=%s, review_note=%s, "
                "review_was=%s where id=%s",
                (new, self.clock(), note.strip() or None, status, item_id),
            )
            # The owner's decision is one source, Bronze (specs/validation/step-v2.md).
            add_label(
                conn,
                LabelIn(
                    content_type="reading_item",
                    content_id=item_id,
                    aspect="item_ok",
                    value="right" if new == "approved" else "wrong",
                    role="owner_developer",
                    note=note.strip() or None,
                    detail={"reason": body.reason},
                    labelled_at=self.clock(),
                ),
            )
        return {"id": item_id, "status": new}


def key_of(item: Any) -> object:
    if item.kind == "completion":
        return list(item.accepted)
    if item.kind == "headings":
        return {str(k): v for k, v in item.key.items()}
    return item.key
