"""The reviewer portal (specs/validation/step-v2.md, step-v2b.md).

Outside reviewers label content through a private link. Every call carries the reviewer's token;
only its SHA-256 is stored. A view holds only what the judgement needs: never the item's status,
the checker's answer, or anyone else's labels. Labels are written with the reviewer's own role, so
they are Gold (app.validation.tiers).

Pronunciation (V2b): a reviewer hears a recording only when it was kept, belongs to an owner
(DRAFT_ITEM_LEARNERS) and the owner put it in a batch with an explicit command; nobody else's voice
is ever served.
"""

import hashlib
import hmac
import random
import re
import secrets
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import psycopg
import yaml  # type: ignore[import-untyped]
from fastapi import HTTPException
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from app.reading.items import Item, learner_view
from app.reading.pipeline import sha256 as passage_sha256
from app.services.reading_review import key_of as reading_key
from app.services.reading_review import load_passages
from app.validation.sampling import Sample
from app.validation.store import LabelIn, add_label
from app.vocabulary.wordlist import Word, shared_wordlist

_ITEM: TypeAdapter[Any] = TypeAdapter(Item)
LEVELS = ("A1", "A2", "B1", "B2", "C1")
# Which queue each content type is, and the role that judges it by default.
QUEUES: dict[str, tuple[str, str]] = {
    "reading_item": ("item_ok", "expert_teacher"),
    "text_level": ("cefr_level", "expert_teacher"),
    "grammar_item": ("item_ok", "expert_teacher"),
    "vocab_entry": ("entry_ok", "expert_teacher"),
    "speech_target": ("phone_ok", "phonetics_expert"),
}
# Other roles a batch may be given (the spec: a phonetics-trained reviewer, or an English teacher).
OTHER_ROLES: dict[str, frozenset[str]] = {"speech_target": frozenset({"expert_teacher"})}
# The reasons a "wrong" verdict may give, per content type (none for a sound).
REASONS: dict[str, frozenset[str]] = {
    "reading_item": frozenset({"wrong_key", "not_answerable", "two_answers", "unclear", "other"}),
    "grammar_item": frozenset({"wrong_key", "two_answers", "unclear", "other"}),
    "vocab_entry": frozenset(
        {"definition", "example", "collocation", "form", "gloss", "ipa", "other"}
    ),
    "speech_target": frozenset(),
}


def vocab_id(word: Word) -> str:
    """A URL-safe id for a word-list entry: lemma and part of speech."""
    return re.sub(r"[^a-z0-9]+", "-", f"{word.lemma}-{word.pos}".lower()).strip("-")


def shuffled(item_id: str, n: int) -> list[int]:
    """A fixed option order per item, so the correct option is not always first."""
    order = list(range(n))
    random.Random(hashlib.sha256(item_id.encode()).hexdigest()).shuffle(order)
    return order


@dataclass(frozen=True)
class Sources:
    """Where the file-based content lives (defaults: the repository's data folders)."""

    items: Path | None = None  # data/items/english-ielts.yaml
    vocab: Path | None = None  # data/vocabulary/core-seed.yaml
    vocab_imported: Path | None = None  # data-sa/vocabulary
    pronunciation: Path | None = None  # data/pronunciation


class PortalLabel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Reading: the reviewer's own blind answer, then the verdict on the key.
    answer: str | None = Field(default=None, max_length=300)
    verdict: Literal["right", "wrong", "unsure"] | None = None
    reason: str | None = Field(default=None, max_length=20)  # checked per content type
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
    conn: psycopg.Connection,
    name: str,
    content_type: str,
    sample: Sample,
    seed: int,
    role: str | None = None,
) -> str:
    aspect, default = QUEUES[content_type]
    role = role or default
    if role != default and role not in OTHER_ROLES.get(content_type, frozenset()):
        raise ValueError(f"a {content_type} batch cannot go to {role}")
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


def speech_targets(conn: psycopg.Connection, learner: str, owners: set[str]) -> list[str]:
    """Every target sound of an owner's kept, analysed recordings, as `<recording>:<index>`."""
    if learner not in owners:
        raise ValueError("only an owner's own recordings may be sent to a reviewer")
    rows = conn.execute(
        "select id::text, analysis from speech_recordings where learner_id::text=%s and keep "
        "and status='analysed' and octet_length(audio) > 0",
        (learner,),
    ).fetchall()
    return [f"{rid}:{i}" for rid, analysis in rows for i in range(len(analysis["targets"]))]


def grammar_items(path: Path) -> dict[str, dict[str, Any]]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {str(x["id"]): x for x in raw.get("items", [])}


class ReviewPortal:
    def __init__(
        self,
        pool: Callable[[], ConnectionPool],
        texts_dir: Path,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        sources: Sources | None = None,
    ) -> None:
        self.pool = pool
        self.texts_dir = texts_dir
        self.clock = clock
        self.sources = sources or Sources()

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
        if ctype == "grammar_item":
            return self._grammar_view(cid)
        if ctype == "vocab_entry":
            return self._vocab_view(cid)
        if ctype == "speech_target":
            return self._speech_view(conn, cid)
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
        if passage is None or passage_sha256(passage) != digest:
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

    def _grammar_view(self, cid: str) -> dict[str, Any] | None:
        if self.sources.items is None:
            return None
        item = grammar_items(self.sources.items).get(cid)
        if item is None:
            return None
        options = item["options"]
        order = shuffled(cid, len(options))
        correct = [i for i, o in enumerate(options) if o.get("correct")]
        return {
            "content_id": cid,
            "content_type": "grammar_item",
            "prompt": item["prompt"],
            "options": [options[i]["text"] for i in order],
            "key": order.index(correct[0]) if len(correct) == 1 else None,
        }

    def _vocab_view(self, cid: str) -> dict[str, Any] | None:
        if self.sources.vocab is None:
            return None
        words = shared_wordlist(self.sources.vocab, self.sources.vocab_imported).words
        word = next((w for w in words if vocab_id(w) == cid), None)
        if word is None:
            return None
        return {
            "content_id": cid,
            "content_type": "vocab_entry",
            "lemma": word.lemma,
            "pos": word.pos,
            "level": word.level,
            "ipa": word.ipa,
            "definition": word.definition,
            "vi": word.vi,
            "examples": [e.text.replace("___", e.answer) for e in word.examples],
            "collocations": [c.phrase for c in word.collocations],
            "forms": [f.sentence.replace("___", f.answer) for f in word.forms],
        }

    def _speech_view(self, conn: psycopg.Connection, cid: str) -> dict[str, Any] | None:
        if self.sources.pronunciation is None or ":" not in cid:
            return None
        rid, _, index = cid.partition(":")
        row = conn.execute(
            "select prompt_id, analysis from speech_recordings where id::text=%s and keep "
            "and status='analysed' and octet_length(audio) > 0",
            (rid,),
        ).fetchone()
        if row is None or not index.isdigit() or int(index) >= len(row[1]["targets"]):
            return None  # deleted, no longer kept, or not this recording's target
        from app.services.recordings import load_prompts

        sounds, prompts = load_prompts(self.sources.pronunciation)
        target = row[1]["targets"][int(index)]
        sound = sounds.get(target["sound"])
        prompt = next((p for p in prompts if p.id == row[0]), None)
        return {
            "content_id": cid,
            "content_type": "speech_target",
            "sentence": None if prompt is None else prompt.text,
            "word": target["word"],
            "ipa": None if sound is None else sound.ipa,
            "sound_vi": None if sound is None else sound.name_vi,
            "start_ms": target["start_ms"],
            "end_ms": target["end_ms"],
        }

    def audio(self, token: str | None, batch_id: str, content_id: str) -> bytes:
        """The whole recording of a target in the reviewer's batch, while it is still kept."""
        with self.pool().connection() as conn:
            _, _, role = self._reviewer(conn, token)
            ctype, _, ids = self._batch(conn, batch_id, role)
            if ctype != "speech_target" or content_id not in ids:
                raise HTTPException(404, "Không có bản ghi này.")
            row = conn.execute(
                "select audio from speech_recordings where id::text=%s and keep "
                "and octet_length(audio) > 0",
                (content_id.partition(":")[0],),
            ).fetchone()
        if row is None:
            raise HTTPException(404, "Bản ghi không còn.")
        return bytes(row[0])

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
            if ctype != "text_level":
                if body.verdict is None or body.level is not None:
                    raise HTTPException(422, "Hãy chọn đánh giá.")
                reasons = REASONS[ctype]
                if body.verdict == "wrong" and reasons and body.reason not in reasons:
                    raise HTTPException(422, "Hãy chọn lý do.")
                if body.reason is not None and body.reason not in reasons:
                    raise HTTPException(422, "Lý do không hợp lệ.")
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
