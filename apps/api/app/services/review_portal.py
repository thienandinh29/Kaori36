"""The reviewer portal (specs/validation/step-v2.md).

Outside reviewers label content through a private link. Every call carries the reviewer's token;
only its SHA-256 is stored. A view holds only what the judgement needs: never the item's status,
the checker's answer, or anyone else's labels. Labels are written with the reviewer's own role, so
they are Gold (app.validation.tiers).
"""

import hashlib
import hmac
import secrets
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import psycopg
from fastapi import HTTPException
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from app.reading.items import Item, learner_view
from app.services.reading_review import key_of as reading_key
from app.services.reading_review import load_passages
from app.validation.sampling import Sample
from app.validation.store import LabelIn, add_label

_ITEM: TypeAdapter[Any] = TypeAdapter(Item)
LEVELS = ("A1", "A2", "B1", "B2", "C1")
# Which queue each content type is, and the role that judges it.
QUEUES: dict[str, tuple[str, str]] = {
    "reading_item": ("item_ok", "expert_teacher"),
    "text_level": ("cefr_level", "expert_teacher"),
}


class PortalLabel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Reading: the reviewer's own blind answer, then the verdict on the key.
    answer: str | None = Field(default=None, max_length=300)
    verdict: Literal["right", "wrong", "unsure"] | None = None
    reason: Literal["wrong_key", "not_answerable", "two_answers", "unclear", "other"] | None = None
    # Text level.
    level: Literal["A1", "A2", "B1", "B2", "C1", "unsure"] | None = None
    note: str | None = Field(default=None, max_length=500)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_token(conn: psycopg.Connection, reviewer_id: str) -> str:
    """A new token for the reviewer; it is returned once and never stored."""
    token = secrets.token_urlsafe(32)
    conn.execute(
        "insert into reviewer_tokens(token_sha256,reviewer_id) values (%s,%s)",
        (token_hash(token), reviewer_id),
    )
    return token


def revoke_tokens(conn: psycopg.Connection, reviewer_id: str) -> int:
    cur = conn.execute(
        "update reviewer_tokens set revoked_at=now() where reviewer_id=%s and revoked_at is null",
        (reviewer_id,),
    )
    return cur.rowcount


def create_batch(
    conn: psycopg.Connection, name: str, content_type: str, sample: Sample, seed: int
) -> str:
    aspect, role = QUEUES[content_type]
    row = conn.execute(
        "insert into review_batches(name,content_type,aspect,role,item_ids,strata,population,seed) "
        "values (%s,%s,%s,%s,%s,%s,%s,%s) returning id::text",
        (
            name,
            content_type,
            aspect,
            role,
            Jsonb(sample.item_ids),
            Jsonb(sample.strata),
            Jsonb(sample.population),
            seed,
        ),
    ).fetchone()
    assert row is not None
    return str(row[0])


def reading_strata(conn: psycopg.Connection) -> tuple[list[str], list[str]]:
    """Items that passed the code checks, split by the blind checker's call (before any review)."""
    rows = conn.execute(
        "select id, case when status in ('approved','rejected') then review_was else status end "
        "from reading_items where status in ('needs_review','verified','approved','rejected')"
    ).fetchall()
    return [i for i, s in rows if s == "needs_review"], [i for i, s in rows if s == "verified"]


class ReviewPortal:
    def __init__(
        self,
        pool: Callable[[], ConnectionPool],
        texts_dir: Path,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.pool = pool
        self.texts_dir = texts_dir
        self.clock = clock

    def _reviewer(self, conn: psycopg.Connection, token: str | None) -> tuple[str, str, str]:
        if not token:
            raise HTTPException(401, "Đường link không hợp lệ.")
        digest = token_hash(token)
        row = conn.execute(
            "select t.token_sha256, r.id::text, r.display_name, r.role from reviewer_tokens t "
            "join reviewers r on r.id=t.reviewer_id "
            "where t.token_sha256=%s and t.revoked_at is null",
            (digest,),
        ).fetchone()
        if row is None or not hmac.compare_digest(row[0], digest):
            raise HTTPException(401, "Đường link không hợp lệ hoặc đã bị thu hồi.")
        return row[1], row[2], row[3]

    def _batch(self, conn: psycopg.Connection, batch_id: str, role: str) -> tuple[Any, ...]:
        row = conn.execute(
            "select content_type,aspect,item_ids from review_batches "
            "where id::text=%s and role=%s and closed_at is null",
            (batch_id, role),
        ).fetchone()
        if row is None:
            raise HTTPException(404, "Không tìm thấy đợt kiểm tra.")
        return tuple(row)

    @staticmethod
    def _done(
        conn: psycopg.Connection, reviewer_id: str, ctype: str, aspect: str, ids: Sequence[str]
    ) -> set[str]:
        rows = conn.execute(
            "select content_id from labels where source=%s and content_type=%s and aspect=%s "
            "and content_id = any(%s)",
            (f"reviewer:{reviewer_id}", ctype, aspect, list(ids)),
        ).fetchall()
        return {r[0] for r in rows}

    def me(self, token: str | None) -> dict[str, Any]:
        with self.pool().connection() as conn:
            rid, name, role = self._reviewer(conn, token)
            batches = []
            for bid, bname, ctype, aspect, ids in conn.execute(
                "select id::text,name,content_type,aspect,item_ids from review_batches "
                "where role=%s and closed_at is null order by created_at",
                (role,),
            ).fetchall():
                done = len(self._done(conn, rid, ctype, aspect, ids))
                batches.append(
                    {
                        "id": bid,
                        "name": bname,
                        "content_type": ctype,
                        "total": len(ids),
                        "done": done,
                    }
                )
        return {"name": name, "role": role, "batches": batches}

    def _view(self, conn: psycopg.Connection, ctype: str, cid: str) -> dict[str, Any] | None:
        passages = load_passages(self.texts_dir)
        if ctype == "text_level":
            text = passages.get(cid)
            return (
                None if text is None else {"content_id": cid, "content_type": ctype, "text": text}
            )
        row = conn.execute(
            "select text_slug,passage_sha256,item from reading_items where id=%s", (cid,)
        ).fetchone()
        if row is None:
            return None
        slug, digest, data = row
        passage = passages.get(slug)
        if passage is None or hashlib.sha256(passage.encode()).hexdigest() != digest:
            return None  # the text is missing or changed: nothing fair to judge
        item = _ITEM.validate_python(data)
        return {
            "content_id": cid,
            "content_type": ctype,
            "kind": item.kind,
            "skill": item.skill,
            "passage": passage,
            "question": learner_view(item),
            "key": reading_key(item),
        }

    def next(self, token: str | None, batch_id: str) -> dict[str, Any]:
        with self.pool().connection() as conn:
            rid, _, role = self._reviewer(conn, token)
            ctype, aspect, ids = self._batch(conn, batch_id, role)
            done = self._done(conn, rid, ctype, aspect, ids)
            item = None
            unavailable = 0
            for cid in ids:
                if cid in done:
                    continue
                item = self._view(conn, ctype, cid)
                if item is not None:
                    break
                unavailable += 1
        return {"total": len(ids), "done": len(done), "unavailable": unavailable, "item": item}

    def label(
        self, token: str | None, batch_id: str, content_id: str, body: PortalLabel
    ) -> dict[str, Any]:
        with self.pool().connection() as conn:
            rid, _, role = self._reviewer(conn, token)
            ctype, aspect, ids = self._batch(conn, batch_id, role)
            if content_id not in ids:
                raise HTTPException(404, "Mục này không thuộc đợt kiểm tra.")
            if ctype == "reading_item":
                if body.verdict is None or body.level is not None:
                    raise HTTPException(422, "Hãy chọn đánh giá cho đáp án.")
                if body.verdict == "wrong" and body.reason is None:
                    raise HTTPException(422, "Hãy chọn lý do.")
                value: str = body.verdict
                detail = {"answer": body.answer, "reason": body.reason}
            else:
                if body.level is None or body.verdict is not None:
                    raise HTTPException(422, "Hãy chọn cấp độ.")
                value, detail = body.level, {}
            add_label(
                conn,
                LabelIn(
                    content_type=ctype,
                    content_id=content_id,
                    aspect=aspect,
                    value=value,
                    role=role,
                    reviewer_id=rid,
                    note=body.note,
                    detail=detail,
                    labelled_at=self.clock(),
                ),
            )
        return {"content_id": content_id, "value": value}
