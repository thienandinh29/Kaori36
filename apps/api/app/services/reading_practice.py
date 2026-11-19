"""Reading practice (specs/listening-reading/step-4.3.md, plan CP4).

A question is served only when it is approved, its `item_ok` labels are Silver or Gold with the
value "right" (code checks plus the blind checker, or a teacher; the owner's approval adds
nothing), and its passage is unchanged and still passes the code checks. Each answer is graded from
the key and moves the item's Reading competency by BKT (mastery under `ielts-competencies`), logged
in `reading_answers`.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
from fastapi import HTTPException
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool
from pydantic import TypeAdapter

from app.competencies.model import load_map
from app.engine import bkt
from app.engine.bkt import DEFAULT_PARAMS
from app.engine.trace import fmt_p
from app.reading.items import Item, check, grade, learner_view
from app.reading.pipeline import sha256 as passage_sha256
from app.services.backend import learner_uuid, save_trace
from app.services.competency_evidence import competency_ids
from app.services.learning import save_mastery
from app.services.reading_review import key_of, read_texts
from app.validation.tiers import Label, effective

_ITEM: TypeAdapter[Any] = TypeAdapter(Item)
COMPETENCY = {
    "detail": "reading-detail",
    "main_idea": "reading-main-idea",
    "inference": "reading-inference",
    "writers_view": "reading-writers-view",
    "skimming": "reading-skimming",
}
PARAMS = DEFAULT_PARAMS["mcq"]  # objective items graded from a key, like grammar questions
KIND_ORDER = ("tfng", "mcq", "completion", "headings")


def load_texts(folder: Path) -> dict[str, tuple[str, str]]:
    """Text slug -> (title, passage) from the bank's folder; cached until a file changes."""
    return read_texts(folder)


def key_text(item: Any) -> str:
    """The answer as a learner reads it."""
    k: Any = key_of(item)
    if item.kind == "tfng":
        return "NOT GIVEN" if k == "not_given" else str(k).upper()
    if item.kind == "mcq":
        return f"{'ABCD'[k]}. {item.options[k]}"
    if isinstance(k, list):
        return " / ".join(map(str, k))
    if isinstance(k, dict):
        return ", ".join(f"{p}: {h}" for p, h in k.items())
    return str(k)


class ReadingPractice:
    def __init__(
        self,
        pool: Callable[[], ConnectionPool],
        texts_dir: Path,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.pool = pool
        self.texts_dir = texts_dir
        self.clock = clock
        self.cmap = load_map()  # once, as TodayService does: parsing it per answer took 35 ms

    def _learner(self, conn: psycopg.Connection[Any], learner_id: str) -> Any:
        learner = learner_uuid(learner_id)
        if not conn.execute("select 1 from learners where id=%s", (learner,)).fetchone():
            raise HTTPException(404, "Không tìm thấy người học.")
        return learner

    def served(
        self, conn: psycopg.Connection[Any], only: str | None = None
    ) -> dict[str, list[tuple[str, Any]]]:
        """Text slug -> [(item id, item)] that may be served now, in kind order.

        `only`: just that item (an answer needs one, not the whole bank).
        """
        texts = load_texts(self.texts_dir)
        one = " and id=%(id)s" if only is not None else ""
        rows = conn.execute(
            "select id, text_slug, passage_sha256, item from reading_items "
            f"where status='approved'{one} order by id",
            {"id": only},
        ).fetchall()
        labels: dict[str, list[Label]] = {}
        for cid, role, value, key in conn.execute(
            "select content_id, role, value, independence from labels "
            f"where content_type='reading_item' and aspect='item_ok'"
            f"{one.replace('id=', 'content_id=')} order by id",
            {"id": only},
        ).fetchall():
            labels.setdefault(cid, []).append(Label(role, value, key))
        out: dict[str, list[tuple[str, Any]]] = {}
        for item_id, slug, digest, data in rows:
            text = texts.get(slug)
            if text is None or passage_sha256(text[1]) != digest:
                continue
            e = effective(labels.get(item_id, []))
            if e.tier not in ("silver", "gold") or e.value != "right":
                continue
            item = _ITEM.validate_python(data)
            if check(item, text[1]):
                continue
            out.setdefault(slug, []).append((item_id, item))
        for items in out.values():
            items.sort(key=lambda x: (KIND_ORDER.index(x[1].kind), x[0]))
        return out

    def any_served(self, conn: psycopg.Connection[Any]) -> bool:
        return bool(self.served(conn))

    def texts(self, learner_id: str) -> dict[str, Any]:
        titles = load_texts(self.texts_dir)
        with self.pool().connection() as conn:
            self._learner(conn, learner_id)
            served = self.served(conn)
        return {
            "texts": [
                {
                    "slug": slug,
                    "title": titles[slug][0],
                    "questions": len(items),
                    "words": len(titles[slug][1].split()),
                }
                for slug, items in sorted(served.items())
            ]
        }

    def text(self, learner_id: str, slug: str) -> dict[str, Any]:
        titles = load_texts(self.texts_dir)
        with self.pool().connection() as conn:
            self._learner(conn, learner_id)
            items = self.served(conn).get(slug)
        if not items:
            raise HTTPException(404, "Chưa có câu hỏi cho bài đọc này.")
        return {
            "slug": slug,
            "title": titles[slug][0],
            "passage": titles[slug][1],
            "items": [
                {"id": i, **learner_view(item)}
                # Headings: which paragraphs to label (the positions, never the answers).
                | ({"paragraphs": sorted(item.key)} if item.kind == "headings" else {})
                for i, item in items
            ],
        }

    def answer(self, learner_id: str, item_id: str, answer: Any) -> dict[str, Any]:
        now = self.clock()
        with self.pool().connection() as conn, conn.transaction():
            learner = self._learner(conn, learner_id)
            found = next((it for its in self.served(conn, item_id).values() for i, it in its), None)
            if found is None:
                raise HTTPException(404, "Câu hỏi này chưa được dùng cho người học.")
            score = grade(found, answer)
            correct = score >= 1.0
            competency = COMPETENCY[found.skill]
            cmap = self.cmap
            subject, ids = competency_ids(conn, cmap)
            row = conn.execute(
                "select p_known from mastery where learner_id=%s and concept_id=%s",
                (learner, ids[competency]),
            ).fetchone()
            before = float(row[0]) if row else PARAMS.p_init
            after, trace = bkt.update_traced(
                before, correct, PARAMS, concept_slug=competency, now=now, item_id=item_id
            )
            name = next(c.name_vi for c in cmap.competencies if c.slug == competency)
            trace = trace.model_copy(
                update={
                    "rule": "reading.answer",
                    "rule_vi": (
                        f"{name}: trả lời {'đúng' if correct else 'sai'} (chấm theo đáp án) → "
                        f"ước lượng từ {fmt_p(before)} thành {fmt_p(after)}."
                    ),
                }
            )
            save_mastery(conn, learner, ids[competency], after)
            save_trace(conn, learner, subject, trace)
            conn.execute(
                "insert into reading_answers(learner_id,item_id,competency,answer,score,correct,"
                "p_before,p_after,answered_at) values (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (learner, item_id, competency, Jsonb(answer), score, correct, before, after, now),
            )
        return {
            "correct": correct,
            "score": round(score, 3),
            "key": key_text(found),
            "evidence": list(found.evidence),
            "competency": competency,
            "trace": trace.model_dump(mode="json"),
        }
