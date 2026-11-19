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
TEST_SECONDS = 20 * 60  # about 20 minutes per IELTS passage (step 4.3b)
GRACE_SECONDS = 30  # network and a last click; later is graded but marked over time


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
            return self._record(conn, learner, item_id, found, answer, now)

    def _record(
        self,
        conn: psycopg.Connection[Any],
        learner: Any,
        item_id: str,
        item: Any,
        answer: Any,
        now: datetime,
        test_id: Any = None,
    ) -> dict[str, Any]:
        """Grade from the key, move the item's Reading competency by BKT, log the answer.

        Shared by practice and timed tests (step 4.3b), so both give the same evidence.
        """
        score = grade(item, answer)
        correct = score >= 1.0
        competency = COMPETENCY[item.skill]
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
        how = "trong bài thi có giờ" if test_id is not None else "chấm theo đáp án"
        trace = trace.model_copy(
            update={
                "rule": "reading.answer",
                "rule_vi": (
                    f"{name}: trả lời {'đúng' if correct else 'sai'} ({how}) → "
                    f"ước lượng từ {fmt_p(before)} thành {fmt_p(after)}."
                ),
            }
        )
        save_mastery(conn, learner, ids[competency], after)
        save_trace(conn, learner, subject, trace)
        conn.execute(
            "insert into reading_answers(learner_id,item_id,competency,answer,score,correct,"
            "p_before,p_after,answered_at,test_id) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (learner, item_id, competency, Jsonb(answer), score, correct, before, after, now,
             test_id),
        )  # fmt: skip
        return {
            "correct": correct,
            "score": round(score, 3),
            "key": key_text(item),
            "evidence": list(item.evidence),
            "competency": competency,
            "trace": trace.model_dump(mode="json"),
        }

    # --- Timed tests (specs/listening-reading/step-4.3b.md) ---

    def start_test(self, learner_id: str, slug: str) -> dict[str, Any]:
        """Fix the text's served questions and the start time; the server keeps the clock."""
        now = self.clock()
        view = self.text(learner_id, slug)  # 404 when nothing is served
        with self.pool().connection() as conn:
            learner = self._learner(conn, learner_id)
            row = conn.execute(
                "insert into reading_tests(learner_id,text_slug,item_ids,limit_seconds,started_at) "
                "values (%s,%s,%s,%s,%s) returning id::text",
                (learner, slug, [i["id"] for i in view["items"]], TEST_SECONDS, now),
            ).fetchone()
        assert row is not None
        return view | {"test_id": row[0], "limit_seconds": TEST_SECONDS,
                       "started_at": now.isoformat()}  # fmt: skip

    def submit_test(
        self, learner_id: str, test_id: str, answers: dict[str, tuple[Any, int | None]]
    ) -> dict[str, Any]:
        """Grade every question once. A blank is wrong in the score but gives no evidence."""
        now = self.clock()
        with self.pool().connection() as conn, conn.transaction():
            learner = self._learner(conn, learner_id)
            row = conn.execute(
                "select item_ids, started_at, limit_seconds, submitted_at, text_slug "
                "from reading_tests where id::text=%s and learner_id=%s for update",
                (test_id, learner),
            ).fetchone()
            if row is None:
                raise HTTPException(404, "Không tìm thấy bài thi.")
            item_ids, started, limit, submitted, slug = row
            if submitted is not None:
                raise HTTPException(409, "Bài thi này đã được nộp.")
            unknown = sorted(set(answers) - set(item_ids))
            if unknown:
                raise HTTPException(422, "Có câu trả lời không thuộc bài thi này.")
            seconds = round((now - started).total_seconds())
            over = seconds > limit + GRACE_SECONDS
            served = dict(self.served(conn).get(slug, []))
            stored = {
                r[0]: _ITEM.validate_python(r[1])
                for r in conn.execute(
                    "select id, item from reading_items where id = any(%s)", (list(item_ids),)
                ).fetchall()
            }
            out = []
            for item_id in item_ids:
                item = stored[item_id]
                given, at = answers.get(item_id, (None, None))
                blank = given is None or given == "" or given == {}
                if blank:
                    out.append({"id": item_id, "answer": None, "correct": False,
                                "key": key_text(item), "evidence": list(item.evidence),
                                "at_seconds": None})  # fmt: skip
                    continue
                if item_id in served:  # still served: evidence, as in practice
                    r = self._record(conn, learner, item_id, item, given, now, test_id)
                    correct = r["correct"]
                else:  # withdrawn since the test began: graded, but no evidence
                    correct = grade(item, given) >= 1.0
                out.append({"id": item_id, "answer": given, "correct": correct,
                            "key": key_text(item), "evidence": list(item.evidence),
                            "at_seconds": at})  # fmt: skip
            right = sum(x["correct"] for x in out)
            conn.execute(
                "update reading_tests set submitted_at=%s, correct=%s, total=%s, over_time=%s "
                "where id::text=%s",
                (now, right, len(out), over, test_id),
            )
        return {"test_id": test_id, "correct": right, "total": len(out),
                "answered": sum(x["answer"] is not None for x in out), "over_time": over,
                "seconds": seconds, "items": out}  # fmt: skip
