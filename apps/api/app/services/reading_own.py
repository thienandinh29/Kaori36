"""A Reading test taken outside the app, pasted for feedback (specs/listening-reading/step-4.3d.md).

Flow: the learner pastes the passage, the questions, the official key and their answers
(`submit`, status `queued`); the worker reads the questions with one model call and code checks
them (`process_next_own_test`, `parsed`); the learner confirms or fixes the list (`confirm`): code
marks every answer from the key and records the evidence (`marked`); the worker then explains each
wrong answer, one call each, and keeps only explanations that pass code's checks (`done`).

Owner-only while it uses the model, like Writing's feedback. The pasted test stays with the
learner's submission, is deletable, and never reaches the bank or another learner.
"""

import logging
import re
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

import psycopg
from fastapi import HTTPException
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from app.competencies.model import load_map
from app.engine import bkt
from app.engine.bkt import DEFAULT_PARAMS
from app.engine.trace import fmt_p
from app.reading import own_test as ot
from app.services.backend import learner_uuid, save_trace
from app.services.competency_evidence import competency_ids
from app.services.learning import save_mastery

logger = logging.getLogger(__name__)
PARAMS = DEFAULT_PARAMS["mcq"]  # graded from a key, as the bank's Reading questions


class Model(Protocol):
    """`WritingModel`: budget first, the gateway, one `llm_calls` row per attempt."""

    last_model: str

    def complete(self, learner: UUID, task: str, system: str, user: str, schema: Any) -> Any: ...


def _owners(value: str | Iterable[UUID]) -> frozenset[UUID]:
    if isinstance(value, str):
        return frozenset(learner_uuid(x.strip()) for x in value.split(",") if x.strip())
    return frozenset(value)


def _uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(404, "Không tìm thấy bài này.") from None


class OwnTests:
    def __init__(
        self,
        pool: Callable[[], ConnectionPool],
        draft_learners: str | Iterable[UUID] = "",
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.pool = pool
        self.owners = _owners(draft_learners)
        self.clock = clock
        self.cmap = load_map()

    def _learner(self, conn: psycopg.Connection[Any], learner_id: str) -> UUID:
        learner = learner_uuid(learner_id)
        if not conn.execute("select 1 from learners where id=%s", (learner,)).fetchone():
            raise HTTPException(404, "Không tìm thấy người học.")
        if learner not in self.owners:
            raise HTTPException(403, "Tính năng này đang thử nghiệm, chưa mở cho mọi người.")
        return learner

    def submit(
        self,
        learner_id: str,
        consent: str,
        passage: str,
        questions: str,
        key: str,
        answers: str,
        *,
        progress_test: bool = False,
    ) -> str:
        if consent != ot.CONSENT:
            raise HTTPException(422, "Cần đồng ý với thông báo trước khi gửi bài.")
        passage, questions, key, answers = (ot.clean(x) for x in (passage, questions, key, answers))
        if not passage or len(passage) > ot.MAX_PASSAGE_CHARS:
            raise HTTPException(422, "Bài đọc cần có nội dung và không quá 14.000 ký tự.")
        if len(passage.split()) > ot.MAX_PASSAGE_WORDS:
            raise HTTPException(422, "Mỗi lần chỉ dán một bài đọc (khoảng 1.500 từ).")
        if not questions or len(questions) > ot.MAX_QUESTIONS_CHARS:
            raise HTTPException(422, "Phần câu hỏi cần có nội dung và không quá 8.000 ký tự.")
        if len(key) > ot.MAX_KEY_CHARS or len(answers) > ot.MAX_KEY_CHARS:
            raise HTTPException(422, "Đáp án và câu trả lời mỗi phần không quá 2.000 ký tự.")
        entries = ot.numbered(key)
        if not entries:
            raise HTTPException(422, "Không đọc được đáp án. Dán theo dạng: 1 TRUE 2 NOT GIVEN 3 C")
        if len(entries) > ot.MAX_QUESTIONS:
            raise HTTPException(422, f"Mỗi lần tối đa {ot.MAX_QUESTIONS} câu (một bài đọc).")
        with self.pool().connection() as conn:
            learner = self._learner(conn, learner_id)
            row = conn.execute(
                "insert into reading_own_tests(learner_id,consent,passage,questions_text,key_text,"
                "answers_text,fingerprint,progress_test,submitted_at) "
                "values (%s,%s,%s,%s,%s,%s,%s,%s,%s) returning id",
                (learner, consent, passage, questions, key, answers,
                 ot.fingerprint(passage, key), progress_test, self.clock()),
            ).fetchone()  # fmt: skip
        assert row is not None
        return str(row[0])

    def listing(self, learner_id: str) -> list[dict[str, Any]]:
        with self.pool().connection() as conn:
            learner = self._learner(conn, learner_id)
            rows = conn.execute(
                "select id, status, submitted_at, result->'correct', result->'total', "
                "left(passage, 80) from reading_own_tests where learner_id=%s "
                "order by submitted_at desc limit 50",
                (learner,),
            ).fetchall()
        return [
            {"id": str(r[0]), "status": r[1], "submitted_at": r[2], "correct": r[3],
             "total": r[4], "opening": " ".join(r[5].split())}
            for r in rows
        ]  # fmt: skip

    def get(self, learner_id: str, test_id: str) -> dict[str, Any]:
        with self.pool().connection() as conn:
            return self._view(conn, self._learner(conn, learner_id), test_id)

    def _view(self, conn: psycopg.Connection[Any], learner: UUID, test_id: str) -> dict[str, Any]:
        """The test as the page shows it: each question with the learner's answer and problems."""
        row = conn.execute(
            "select id, status, passage, questions_text, key_text, answers_text, questions, "
            "result, failure_vi, progress_test, submitted_at from reading_own_tests "
            "where id=%s and learner_id=%s",
            (_uuid(test_id), learner),
        ).fetchone()
        if row is None:
            raise HTTPException(404, "Không tìm thấy bài này.")
        tid, status, passage, qtext, key_text, answers_text, questions, result, failure = row[:9]
        prog, at = row[9:]
        answers = ot.numbered(answers_text)
        listed = [
            q | {"answer": answers.get(q["number"]),
                 "problems": problems(ot.question_from_json(q), qtext, key_text)}
            for q in (questions or [])
        ]  # fmt: skip
        return {
            "id": str(tid), "status": status, "passage": passage, "questions": listed,
            "result": result, "failure_vi": failure, "progress_test": prog, "submitted_at": at,
        }  # fmt: skip

    def delete(self, learner_id: str, test_id: str) -> None:
        with self.pool().connection() as conn:
            learner = self._learner(conn, learner_id)
            gone = conn.execute(
                "delete from reading_own_tests where id=%s and learner_id=%s returning id",
                (_uuid(test_id), learner),
            ).fetchone()
        if gone is None:
            raise HTTPException(404, "Không tìm thấy bài này.")

    def confirm(
        self, learner_id: str, test_id: str, questions: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Mark the confirmed list from the key and record the evidence, once per question.

        A list that still has a problem is kept as the learner edited it and sent back with its
        problems, unmarked (status `parsed`), so the page can say what to fix.
        """
        now = self.clock()
        with self.pool().connection() as conn, conn.transaction():
            learner = self._learner(conn, learner_id)
            row = conn.execute(
                "select status, questions_text, key_text, answers_text, fingerprint "
                "from reading_own_tests where id=%s and learner_id=%s for update",
                (_uuid(test_id), learner),
            ).fetchone()
            if row is None:
                raise HTTPException(404, "Không tìm thấy bài này.")
            status, qtext, key_text, answers_text, digest = row
            if status != "parsed":
                raise HTTPException(409, "Bài này không ở bước xác nhận câu hỏi.")
            confirmed = _confirmed(questions)
            kept = Jsonb([q.to_json() for q in confirmed])
            marked = [q for q in confirmed if q.kind != "unsupported"]
            if not marked:
                raise HTTPException(422, "Không còn câu hỏi nào để chấm.")
            if any(problems(q, qtext, key_text) for q in marked):
                conn.execute(
                    "update reading_own_tests set questions=%s where id=%s", (kept, _uuid(test_id))
                )
                return self._view(conn, learner, test_id)
            answers = ot.numbered(answers_text)
            marks = [ot.mark(q, answers.get(q.number)) for q in marked]
            moved = self._evidence(conn, learner, _uuid(test_id), digest, marks, now)
            wrong = [m.number for m in marks if not m.correct]
            result = {
                "correct": sum(m.correct for m in marks),
                "total": len(marks),
                "answered": sum(m.answer is not None for m in marks),
                "unsupported": [q.number for q in confirmed if q.kind == "unsupported"],
                "marks": [
                    {"number": m.number, "kind": m.kind, "answer": m.answer, "correct": m.correct,
                     "trap": m.trap, "key": ot.key_text(q),
                     "answer_text": ot.answer_text(q, m.answer) if m.answer else None,
                     "explanation": None, "explanation_vi": None}
                    for m, q in zip(marks, marked, strict=True)
                ],
                "evidence": moved,
                "explained": not wrong,
            }  # fmt: skip
            conn.execute(
                "update reading_own_tests set status=%s, questions=%s, result=%s, confirmed_at=%s "
                "where id=%s",
                ("marked" if wrong else "done", kept, Jsonb(result), now, _uuid(test_id)),
            )
            return self._view(conn, learner, test_id)

    def _evidence(
        self,
        conn: psycopg.Connection[Any],
        learner: UUID,
        test_id: UUID,
        digest: str,
        marks: list[ot.Mark],
        now: datetime,
    ) -> int:
        """One BKT observation per answered question, never twice for the same pasted test."""
        subject, ids = competency_ids(conn, self.cmap)
        names = {c.slug: c.name_vi for c in self.cmap.competencies}
        moved = 0
        for m in marks:
            if m.answer is None:
                continue  # a blank gives no evidence
            competency = ot.COMPETENCY[m.kind]
            seen = conn.execute(
                "select 1 from reading_own_answers where learner_id=%s and fingerprint=%s "
                "and number=%s",
                (learner, digest, m.number),
            ).fetchone()
            if seen:
                continue
            got = conn.execute(
                "select p_known from mastery where learner_id=%s and concept_id=%s",
                (learner, ids[competency]),
            ).fetchone()
            before = float(got[0]) if got else PARAMS.p_init
            after, trace = bkt.update_traced(
                before, m.correct, PARAMS, concept_slug=competency, now=now,
                item_id=f"own-{test_id}-{m.number}",
            )  # fmt: skip
            trace = trace.model_copy(
                update={
                    "rule": "reading.own_test",
                    "rule_vi": (
                        f"{names[competency]}: câu {m.number} trong bài bạn tự làm, "
                        f"{'đúng' if m.correct else 'sai'} theo đáp án chính thức → ước lượng từ "
                        f"{fmt_p(before)} thành {fmt_p(after)}."
                    ),
                }
            )
            save_mastery(conn, learner, ids[competency], after)
            save_trace(conn, learner, subject, trace)
            conn.execute(
                "insert into reading_own_answers(learner_id,test_id,fingerprint,number,kind,"
                "competency,correct,trap,p_before,p_after,answered_at) "
                "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (learner, test_id, digest, m.number, m.kind, competency, m.correct, m.trap,
                 before, after, now),
            )  # fmt: skip
            moved += 1
        return moved


def problems(q: ot.Question, qtext: str, key_text: str) -> list[str]:
    """Code's checks on a question as read or as the learner fixed it; a key they typed in must
    be in the pasted key (the official key is the truth, not the learner's memory of it)."""
    if q.kind == "unsupported":
        return []
    found = ot.check_question(q, qtext)
    if q.key is not None and not _whole_words_in(ot.flat(q.key), ot.flat(key_text)):
        found.insert(0, "Đáp án này không có trong phần đáp án đã dán.")
    return found


def _whole_words_in(part: str, text: str) -> bool:
    """`part` appears in `text` as whole words: a key edited to "A" needs an "A" of its own in the
    pasted key, not the letter inside "species"."""
    return bool(part) and re.search(rf"(?<!\w){re.escape(part)}(?!\w)", text) is not None


def _confirmed(questions: list[dict[str, Any]]) -> list[ot.Question]:
    """The learner's list, its shape checked (each question's content is checked by `problems`)."""
    out: list[ot.Question] = []
    seen: set[int] = set()
    for data in questions:
        try:
            q = ot.question_from_json(data)
        except (KeyError, TypeError, ValueError):
            raise HTTPException(422, "Danh sách câu hỏi không hợp lệ.") from None
        if q.kind not in ("tfng", "ynng", "mcq", "completion", "unsupported"):
            raise HTTPException(422, "Dạng câu hỏi không hợp lệ.")
        if q.number in seen:
            raise HTTPException(422, f"Câu {q.number} bị lặp.")
        seen.add(q.number)
        out.append(q)
    if not out:
        raise HTTPException(422, "Không còn câu hỏi nào để chấm.")
    if len(out) > ot.MAX_QUESTIONS:
        raise HTTPException(422, f"Mỗi lần tối đa {ot.MAX_QUESTIONS} câu (một bài đọc).")
    return sorted(out, key=lambda q: q.number)


# --- The worker's part ---

PARSE_FAILED_VI = "Không đọc được phần câu hỏi. Bạn kiểm tra lại nội dung đã dán rồi gửi lại nhé."
NO_MODEL_VI = "Máy chủ chưa bật mô hình đọc câu hỏi, nên chưa xử lý được bài này."
BUDGET_VI = "Hôm nay đã hết lượt dùng mô hình. Hẹn bạn ngày mai nhé."
NOT_EXPLAINED_VI = "Không có lời giải thích nào đạt kiểm tra cho câu này."


def process_next_own_test(database_url: str, model: Model | None) -> bool:
    """Read one queued test's questions, or explain one marked test's wrong answers.

    False when there is nothing to do (the worker then moves on).
    """
    from app.writing.model_calls import BudgetExceeded

    with psycopg.connect(database_url) as conn:
        with conn.transaction():
            row = conn.execute(
                "select id, learner_id, status, passage, questions_text, key_text, questions, "
                "result from reading_own_tests where status in ('queued','marked') "
                "order by submitted_at, id limit 1 for update skip locked"
            ).fetchone()
            if row is None:
                return False
            tid, learner, status, passage, qtext, key_text, questions, result = row
            conn.execute(
                "update reading_own_tests set status=%s where id=%s",
                ("parsing" if status == "queued" else "explaining", tid),
            )
        if status == "queued":
            _parse(conn, tid, learner, qtext, key_text, model, BudgetExceeded)
        else:
            _explain(conn, tid, learner, passage, questions, result, model, BudgetExceeded)
    return True


def _parse(
    conn: psycopg.Connection[Any],
    tid: UUID,
    learner: UUID,
    qtext: str,
    key_text: str,
    model: Model | None,
    budget_error: type[Exception],
) -> None:
    failure: str | None = None
    questions: list[ot.Question] = []
    if model is None:
        failure = NO_MODEL_VI
    else:
        try:
            out = model.complete(
                learner, "reading_own_parse", ot.PARSE_SYSTEM, ot.parse_prompt(qtext),
                ot.QuestionsOut,
            )  # fmt: skip
            questions = ot.from_model(out, ot.numbered(key_text))
            if not questions:
                failure = PARSE_FAILED_VI
        except budget_error:
            failure = BUDGET_VI
        except Exception:
            logger.exception("own test parse failed", extra={"test_id": str(tid)})
            failure = PARSE_FAILED_VI
    with conn.transaction():
        if failure:
            conn.execute(
                "update reading_own_tests set status='failed', failure_vi=%s where id=%s",
                (failure, tid),
            )
        else:
            conn.execute(
                "update reading_own_tests set status='parsed', questions=%s where id=%s",
                (Jsonb([q.to_json() for q in questions]), tid),
            )


def _explain(
    conn: psycopg.Connection[Any],
    tid: UUID,
    learner: UUID,
    passage: str,
    questions: list[dict[str, Any]],
    result: dict[str, Any],
    model: Model | None,
    budget_error: type[Exception],
) -> None:
    by_number = {q["number"]: ot.question_from_json(q) for q in questions}
    stop: str | None = None if model is not None else NO_MODEL_VI
    dropped = 0
    for entry in result["marks"]:
        if entry["correct"] or entry["explanation"] is not None:
            continue
        if stop is not None:
            entry["explanation_vi"] = stop
            continue
        assert model is not None
        q = by_number[entry["number"]]
        m = ot.Mark(q.number, q.kind, entry["answer"], False, entry["trap"])
        try:
            out = model.complete(
                learner, "reading_own_explain", ot.EXPLAIN_SYSTEM,
                ot.explain_prompt(passage, q, m.answer), ot.ExplanationOut,
            )  # fmt: skip
        except budget_error:
            stop = BUDGET_VI
            entry["explanation_vi"] = stop
            continue
        except Exception:
            logger.exception("own test explanation failed", extra={"test_id": str(tid)})
            entry["explanation_vi"] = NOT_EXPLAINED_VI
            continue
        explanation, problems = ot.check_explanation(out, passage, q, m)
        if explanation is None:
            dropped += 1
            logger.info("own test explanation dropped: %s", "; ".join(problems))
            entry["explanation_vi"] = NOT_EXPLAINED_VI
            continue
        entry["explanation"] = explanation.to_json() | {"model": model.last_model}
        entry["trap"] = explanation.trap
        entry["explanation_vi"] = None
    result["explained"] = True
    result["explanations_dropped"] = dropped
    with conn.transaction():
        for entry in result["marks"]:
            conn.execute(
                "update reading_own_answers set trap=%s where test_id=%s and number=%s",
                (entry["trap"], tid, entry["number"]),
            )
        conn.execute(
            "update reading_own_tests set status='done', result=%s where id=%s",
            (Jsonb(result), tid),
        )
