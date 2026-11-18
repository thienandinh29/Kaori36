"""FORGET-001: delayed grammar re-checks (specs/forget-001/spec.md).

A re-check asks one unaided question on a node the model calls known, at least five days after its
last evidence. It is evaluation data: it never changes mastery and is not written to
grammar_answers, so it measures the model without feeding it. Planning is pure
(app.studies.recheck); this service stores and serves.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
from fastapi import HTTPException

from app.services.grammar import GrammarService
from app.studies.recheck import Known, due, pick_item

COURSE = "english-ielts"


@dataclass(frozen=True)
class RecheckQuestion:
    id: str
    node: str
    node_name_vi: str
    prompt: str
    options: list[str]
    draft: bool


class Rechecks:
    def __init__(
        self,
        grammar: GrammarService,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.grammar = grammar
        self.clock = clock

    def _plan(
        self, conn: psycopg.Connection[Any], learner: Any, course: str, now: datetime
    ) -> None:
        b = self.grammar.bundle(course)
        known = [
            Known(slug, float(p), at)
            for slug, p, at in conn.execute(
                "select c.slug, m.p_known, m.updated_at from mastery m "
                "join concepts c on c.id=m.concept_id join subjects s on s.id=c.subject_id "
                "where m.learner_id=%s and s.slug=%s",
                (learner, course),
            ).fetchall()
        ]
        last = dict(
            conn.execute(
                "select node, max(created_at) from grammar_rechecks "
                "where learner_id=%s and course=%s group by node",
                (learner, course),
            ).fetchall()
        )
        week_row = conn.execute(
            "select count(*) from grammar_rechecks where learner_id=%s and created_at > %s",
            (learner, now - timedelta(days=7)),
        ).fetchone()
        drafts = learner in self.grammar.draft_learners
        for k in due(known, last, int(week_row[0]) if week_row else 0, now):
            items = [i.id for i in b.bank.for_node(k.node, include_drafts=drafts)]
            answered = dict(
                conn.execute(
                    "select item_id, max(answered_at) from grammar_answers "
                    "where learner_id=%s and course=%s and node=%s group by item_id",
                    (learner, course, k.node),
                ).fetchall()
            )
            item = pick_item(items, answered)
            if item is None:
                continue  # no item this learner may see for the node
            conn.execute(
                "insert into grammar_rechecks(learner_id,course,node,item_id,p_known,evidence_at,"
                "created_at) values (%s,%s,%s,%s,%s,%s,%s)",
                (learner, course, k.node, item, k.p_known, k.evidence_at, now),
            )

    def next(self, learner_id: str, course: str = COURSE) -> RecheckQuestion | None:
        now = self.clock()
        with self.grammar.pool().connection() as conn, conn.transaction():
            learner = self.grammar._learner(conn, learner_id)
            if self._open(conn, learner, course) is None:
                self._plan(conn, learner, course, now)
            row = self._open(conn, learner, course)
        if row is None:
            return None
        rid, node, item_id = row
        b = self.grammar.bundle(course)
        item = b.bank.get(item_id)
        if item is None:
            return None
        names = {c.slug: c.name_vi for c in b.course.concepts}
        return RecheckQuestion(
            str(rid), node, names.get(node, node), item.prompt,
            [o.text for o in item.shuffled()], item.status == "draft",
        )  # fmt: skip

    @staticmethod
    def _open(conn: psycopg.Connection[Any], learner: Any, course: str) -> tuple[Any, ...] | None:
        row = conn.execute(
            "select id, node, item_id from grammar_rechecks where learner_id=%s and course=%s "
            "and answered_at is null order by created_at, evidence_at, id limit 1",
            (learner, course),
        ).fetchone()
        return None if row is None else tuple(row)

    def answer(self, learner_id: str, recheck_id: str, answer: str) -> dict[str, Any]:
        now = self.clock()
        with self.grammar.pool().connection() as conn, conn.transaction():
            learner = self.grammar._learner(conn, learner_id)
            row = conn.execute(
                "select course, item_id, answered_at from grammar_rechecks "
                "where id::text=%s and learner_id=%s for update",
                (recheck_id, learner),
            ).fetchone()
            if row is None:
                raise HTTPException(404, "Không tìm thấy câu kiểm tra lại.")
            course, item_id, answered_at = row
            if answered_at is not None:
                raise HTTPException(409, "Câu này đã được trả lời.")
            item = self.grammar.bundle(course).bank.get(item_id)
            if item is None:
                raise HTTPException(404, "Câu hỏi không còn trong ngân hàng.")
            correct = answer.strip() == item.key
            conn.execute(
                "update grammar_rechecks set answered_at=%s, answer=%s, correct=%s "
                "where id::text=%s",
                (now, answer.strip()[:200], correct, recheck_id),
            )
        return {"correct": correct, "key": item.key}
