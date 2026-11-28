"""Writing: prompts, essay submission, the learner's essays, and the worker's analysis
(specs/writing/step-2.1.md).

A request never analyses: it stores the essay as `queued`; the worker claims essays with FOR UPDATE
SKIP LOCKED, analyses them (`writing.analysis`) and stores the result.
"""

import logging
import re
import time
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
import psycopg
from fastapi import HTTPException
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from app.curriculum.course import CourseSpec, load_course
from app.curriculum.store import sync_course
from app.engine import bkt
from app.engine.graph import UNSEEN_P_KNOWN
from app.engine.trace import fmt_p
from app.lessons.graded import WordIndex
from app.services import competency_evidence
from app.services.backend import learner_uuid, save_trace
from app.services.learning import save_mastery
from app.services.plans import NAMES_VI, Plans
from app.services.vocabulary import start_of_day
from app.writing import (
    competency,
    feedback,
    guardrails,
    llm_corrections,
    own_prompt,
    repair,
    structure,
    task1,
    tracker,
)
from app.writing.analysis import analyse, load_linking_words, paragraphs, words
from app.writing.caps import CapRule, applied_caps, load_caps
from app.writing.descriptor_features import DescriptorFeatures, load_word_index, measure_essay
from app.writing.error_map import ErrorMap, load_error_map
from app.writing.feedback import FeedbackOut
from app.writing.grammar import (
    GrammarResult,
    Issue,
    analyse_grammar,
    choose_evidence,
    complexity,
    edit_distance,
)
from app.writing.languagetool import NEVER_MAPPED_CATEGORIES, LanguageToolClient
from app.writing.llm_corrections import CorrectionsOut, Sentence, unflagged
from app.writing.model_calls import BudgetExceeded, WritingModel
from app.writing.prompts import Prompt, PromptBank, load_prompts
from app.writing.scorer_client import ScorerClient
from app.writing.scoring import (
    MIN_WORDS_FOR_BAND,
    ScorerConfig,
    band_range,
    compare_raw,
    load_scorer_config,
    no_band_reason,
    residual_band_range,
)
from app.writing.timing import KEY as TIMINGS
from app.writing.timing import timed

logger = logging.getLogger(__name__)
CONSENT = (
    "writing-v1"  # the version of the notice the learner accepts (messages/vi.ts, writing.consent)
)
MAX_CHARS = 12_000
TEST_SECONDS = 40 * 60  # Task 2 in the exam (step 2.10)
TEST_GRACE_SECONDS = 30  # network and a last click; later is analysed but marked over time


def _test_view(
    submitted: datetime, over: bool | None, started: datetime, limit: int
) -> dict[str, Any]:
    seconds = int((submitted - started).total_seconds())
    return {"started_at": started, "time_limit_s": limit, "over_time": bool(over),
            "seconds": seconds}  # fmt: skip


def prompt_for(
    bank: PromptBank, prompt_id: str, own: str | None, own_parts: list[str] | None = None
) -> Prompt | None:
    """An essay's prompt: from the bank, or the learner's own Task 2 question (step 2.10) with
    the parts the learner kept (step 2.11b)."""
    if prompt_id == own_prompt.OWN_ID:
        return own_prompt.as_prompt(own, own_parts) if own else None
    return bank.get(prompt_id)


NOTE_VI = "Điểm ước lượng và nhận xét chi tiết sẽ có ở các bước sau."
ACCEPTED_VI = "Đúng rồi! Bạn đã tự sửa được lỗi này."
STILL_ERROR_VI = "Câu vẫn còn lỗi ngữ pháp hoặc chính tả. Thử lại nhé."
NOT_CLOSER_VI = "Câu chưa sửa đúng chỗ lỗi. Đọc lại gợi ý rồi thử lại nhé."
PATTERN_DAYS = 90
DELETED_VI = (
    "Bạn đã xoá phần có lỗi thay vì sửa nó. Giữ ý của câu và chỉ sửa chỗ được đánh dấu nhé."
)
UNCHANGED_VI = "Chỗ được đánh dấu vẫn như cũ. Sửa đúng chỗ đó rồi thử lại nhé."
LAST_TRY_VI = "Chưa đúng. Đây là cách sửa, bạn so sánh với câu của mình nhé."
SHOWN_VI = "Đây là cách sửa, bạn so sánh với câu của mình nhé."
FEEDBACK_OFF_VI = "Chưa có nhận xét bằng AI: máy chủ chưa cấu hình mô hình (DEEPSEEK_API_KEY)."
FEEDBACK_HIDDEN_VI = "Nhận xét bằng AI đang được thử nghiệm, chưa mở cho mọi người."
FEEDBACK_BUDGET_VI = (
    "Hôm nay đã dùng hết lượt nhận xét bằng AI; các phần đo bằng công cụ vẫn đầy đủ."
)
FEEDBACK_FAILED_VI = "Chưa tạo được nhận xét bằng AI lần này. Các phần đo bằng công cụ vẫn đầy đủ."
BAND_OFF_VI = "Chưa ước lượng band: máy chủ chưa bật mô hình chấm (SCORER_URL)."
BAND_HIDDEN_VI = "Ước lượng band đang được kiểm chứng với điểm giám khảo, chưa mở cho mọi người."
BAND_DOWN_VI = "Chưa ước lượng được band: mô hình chấm không phản hồi. Bạn thử gửi lại sau nhé."
BAND_MISMATCH_VI = "Chưa ước lượng band: mô hình đang chạy khác với mô hình đã được hiệu chỉnh."
BAND_NO_GRAMMAR_VI = (
    "Chưa ước lượng band: chưa kiểm tra được ngữ pháp của bài này (LanguageTool), "
    "nên các số đo chưa đủ."
)
BAND_REASONS_VI = {
    "task1": "Chưa ước lượng band cho Task 1.",
    "too_short": "Bài dưới 150 từ: chưa đủ dài để ước lượng band.",
    "not_calibrated": "Chưa ước lượng band: mô hình chưa được hiệu chỉnh với điểm giám khảo.",
    "padded": (
        "Chưa ước lượng band: nhiều đoạn trong bài là câu lặp lại hoặc câu mẫu học thuộc, "
        "không phải lời của bạn (xem phần Kiểm tra bài)."
    ),
}
GRAMMAR_OFF_VI = "Chưa kiểm tra ngữ pháp: máy chủ chưa bật LanguageTool (LANGUAGETOOL_URL)."
GRAMMAR_DOWN_VI = (
    "Chưa kiểm tra được ngữ pháp: LanguageTool không phản hồi. Bạn thử gửi lại sau nhé."
)


def _own_columns(prompt_id: str, prompt: Prompt) -> tuple[str | None, Jsonb | None]:
    """An own question and the parts kept, as stored with the test or essay (2.10, 2.11b)."""
    if prompt_id != own_prompt.OWN_ID:
        return None, None
    return prompt.prompt, Jsonb([p.text for p in prompt.parts])


def _uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(404, "Không tìm thấy bài viết.") from None


class WritingService:
    def __init__(
        self,
        pool: Callable[[], ConnectionPool],
        writing_dir: Path,
        *,
        draft_learners: str = "",
        daily_essays: int = 3,
        languagetool: LanguageToolClient | None = None,
        courses_dir: Path | None = None,
        plans: "Plans | None" = None,
    ) -> None:
        self.pool = pool
        self.writing_dir = writing_dir
        self.daily_essays = daily_essays  # used when there are no plans (tests, older setups)
        self.plans = plans
        self.languagetool = languagetool
        self.courses_dir = courses_dir
        self._course: tuple[ErrorMap, CourseSpec, UUID, dict[str, UUID]] | None = None
        self.draft_learners = {
            learner_uuid(x.strip()) for x in draft_learners.split(",") if x.strip()
        }
        self._bank: PromptBank | None = None

    def _map_and_ids(
        self, conn: psycopg.Connection[Any]
    ) -> tuple[ErrorMap, CourseSpec, UUID, dict[str, UUID]]:
        if self._course is None:
            if self.courses_dir is None:
                raise HTTPException(503, "Máy chủ chưa cấu hình khóa học cho phần tự sửa.")
            error_map = load_error_map(self.writing_dir / "error-map.yaml")
            course = load_course(self.courses_dir / f"{error_map.course}.yaml")
            ids = sync_course(conn, course)
            row = conn.execute("select id from subjects where slug=%s", (course.slug,)).fetchone()
            assert row is not None
            self._course = (error_map, course, row[0], ids)
        return self._course

    def patterns(self, learner_id: str, *, now: datetime | None = None) -> dict[str, Any]:
        """Errors this learner repeats across essays in the last 90 days (step 2.8)."""
        since = (now or datetime.now(UTC)) - timedelta(days=PATTERN_DAYS)
        with self.pool().connection() as conn:
            learner = self._learner(conn, learner_id)
            rows = conn.execute(
                "select result from essays where learner_id=%s and status='done' "
                "and submitted_at >= %s order by submitted_at desc, id desc",
                (learner, since),
            ).fetchall()
        results = [r[0] or {} for r in rows]
        return {
            "essays": len(results),
            "days": PATTERN_DAYS,
            "patterns": [p.to_json() for p in tracker.patterns(results)],
        }

    def correct(
        self,
        learner_id: str,
        essay_id: str,
        issue_id: int,
        sentence: str | None,
        *,
        show_answer: bool = False,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Hint first, then the answer (step 2.4, point 3). No model call.

        Accepted when LanguageTool finds no error in the learner's sentence and it is closer to
        the minimal correction than the original was; an accepted correction is aided evidence.
        """
        now = now or datetime.now(UTC)
        with self.pool().connection() as conn, conn.transaction():
            learner = self._learner(conn, learner_id)
            row = conn.execute(
                "select result from essays where id=%s and learner_id=%s and status='done' "
                "for update",
                (_uuid(essay_id), learner),
            ).fetchone()
            if row is None:
                raise HTTPException(404, "Không tìm thấy bài viết.")
            issues = ((row[0] or {}).get("grammar") or {}).get("issues", [])
            issue = next((i for i in issues if i["id"] == issue_id and i["evidence"]), None)
            if issue is None or not issue.get("suggestion"):
                raise HTTPException(404, "Lỗi này không có phần tự sửa.")
            state = conn.execute(
                "select tries, accepted, answer_shown from essay_corrections "
                "where essay_id=%s and issue_id=%s",
                (_uuid(essay_id), issue_id),
            ).fetchone()
            tries, accepted, shown = state or (0, False, False)
            if accepted or shown:
                raise HTTPException(409, "Bạn đã hoàn thành phần tự sửa cho lỗi này.")
            original = issue["sentence"]
            at = issue["start"] - issue["sentence_start"]
            answer = original[:at] + issue["suggestion"] + original[at + len(issue["text"]) :]
            feedback_vi = SHOWN_VI
            outcome: repair.Outcome = "check"
            if not show_answer:
                text = unicodedata.normalize("NFC", sentence or "").strip()
                if not 0 < len(text) <= 1000:
                    raise HTTPException(422, "Câu cần từ 1 đến 1.000 ký tự.")
                # Step 2.8: removing the error is not repairing it.
                outcome = repair.judge(original, at, at + len(issue["text"]), text)
            if not show_answer and outcome != "check":
                tries += 1
                accepted = False
                feedback_vi = DELETED_VI if outcome == "deleted" else UNCHANGED_VI
                logger.info("self-correction refused", extra={"outcome": outcome})
            elif not show_answer:
                if self.languagetool is None:
                    raise HTTPException(503, "Chưa kiểm tra được: máy chủ chưa bật LanguageTool.")
                try:
                    flagged = [m for m in self.languagetool.matches(text)
                               if m.category not in NEVER_MAPPED_CATEGORIES]  # fmt: skip
                except httpx.HTTPError:
                    raise HTTPException(503, "LanguageTool không phản hồi, thử lại sau.") from None
                closer = _distance(text, answer) < _distance(original, answer)
                accepted = closer and not flagged
                tries += 1
                feedback_vi = (
                    ACCEPTED_VI if accepted else (STILL_ERROR_VI if flagged else NOT_CLOSER_VI)
                )
                if accepted:
                    self._aided_evidence(conn, learner, issue, essay_id, now)
            shown = show_answer or (not accepted and tries >= 2)
            conn.execute(
                "insert into essay_corrections(essay_id,issue_id,learner_id,tries,accepted,"
                "answer_shown,last_sentence,updated_at) values (%s,%s,%s,%s,%s,%s,%s,%s) "
                "on conflict (essay_id,issue_id) do update set tries=excluded.tries, "
                "accepted=excluded.accepted, answer_shown=excluded.answer_shown, "
                "last_sentence=excluded.last_sentence, updated_at=excluded.updated_at",
                (_uuid(essay_id), issue_id, learner, tries, accepted, shown, sentence, now),
            )
        return {
            "accepted": accepted,
            "tries": tries,
            "answer": answer if shown or accepted else None,
            "feedback_vi": feedback_vi if not shown or show_answer or accepted else LAST_TRY_VI,
        }

    def _aided_evidence(
        self,
        conn: psycopg.Connection[Any],
        learner: UUID,
        issue: dict[str, Any],
        essay_id: str,
        now: datetime,
    ) -> None:
        error_map, _, subject, ids = self._map_and_ids(conn)
        node = issue["node"]
        got = conn.execute(
            "select p_known from mastery where learner_id=%s and concept_id=%s",
            (learner, ids[node]),
        ).fetchone()
        p = float(got[0]) if got else UNSEEN_P_KNOWN
        p_new, trace = bkt.update_traced(
            p, True, bkt.params_with_help(error_map.params(), 1), concept_slug=node, now=now,
            item_id=f"essay:{essay_id}:{issue['id']}:self",
        )  # fmt: skip
        trace = trace.model_copy(
            update={
                "rule": "writing.self_correction",
                "rule_vi": (
                    f"Bạn tự sửa đúng lỗi sau khi xem gợi ý → khả năng đã nắm vững tăng từ "
                    f"{fmt_p(p)} lên {fmt_p(p_new)}. Có gợi ý nên được tính nhẹ hơn và không "
                    f"tính vào số câu đúng tự làm."
                ),
            }
        )
        save_mastery(conn, learner, ids[node], p_new)
        save_trace(conn, learner, subject, trace)

    def bank(self) -> PromptBank:
        if self._bank is None:
            self._bank = load_prompts(self.writing_dir / "prompts.yaml")
        return self._bank

    def _learner(self, conn: psycopg.Connection[Any], learner_id: str) -> UUID:
        learner = learner_uuid(learner_id)
        if not conn.execute(
            "select id from learners where id=%s for update", (learner,)
        ).fetchone():
            raise HTTPException(404, "Không tìm thấy người học.")
        return learner

    def _visible(self, prompt: Prompt, learner: UUID) -> bool:
        return prompt.status == "reviewed" or learner in self.draft_learners

    def _checked_prompt(
        self, prompt_id: str, own: str | None, learner: UUID, parts: list[str] | None = None
    ) -> Prompt:
        """The prompt an essay or test is written on; an own question must pass the check, and
        its kept parts must be ones the code proposed (step 2.11b)."""
        if prompt_id == own_prompt.OWN_ID:
            why = own_prompt.problem(own or "") or own_prompt.parts_problem(own or "", parts)
            if why:
                raise HTTPException(422, why)
            return own_prompt.as_prompt(own or "", parts)
        prompt = self.bank().get(prompt_id)
        if prompt is None or not self._visible(prompt, learner):
            raise HTTPException(404, "Không tìm thấy đề bài.")
        return prompt

    def check_own_prompt(self, text: str) -> dict[str, Any]:
        """Step 2.10: whether a typed question can be written on, and how it is labelled."""
        why = own_prompt.problem(text)
        if why:
            return {"ok": False, "reason_vi": why, "prompt": None}
        return {"ok": True, "reason_vi": None, "prompt": own_prompt.as_prompt(text).model_dump()}

    def start_test(
        self,
        learner_id: str,
        prompt_id: str,
        own: str | None,
        *,
        own_parts: list[str] | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """A timed Task 2 exam: the clock is the server's; the essay is sent with the test id."""
        now = now or datetime.now(UTC)
        with self.pool().connection() as conn, conn.transaction():
            learner = self._learner(conn, learner_id)
            prompt = self._checked_prompt(prompt_id, own, learner, own_parts)
            if prompt.task != 2:
                raise HTTPException(422, "Thi thử hiện chỉ có cho Task 2.")
            own_text, kept = _own_columns(prompt_id, prompt)
            row = conn.execute(
                "insert into writing_tests(learner_id,prompt_id,own_prompt,own_parts,"
                "time_limit_s,started_at) values (%s,%s,%s,%s,%s,%s) returning id",
                (learner, prompt_id, own_text, kept, TEST_SECONDS, now),
            ).fetchone()
        assert row is not None
        return {"id": str(row[0]), "prompt": prompt.model_dump(), "started_at": now,
                "time_limit_s": TEST_SECONDS}  # fmt: skip

    def prompts(self, learner_id: str) -> list[Prompt]:
        with self.pool().connection() as conn:
            learner = self._learner(conn, learner_id)
        return [p for p in self.bank().prompts if self._visible(p, learner)]

    def submit(
        self,
        learner_id: str,
        prompt_id: str,
        text: str,
        consent: str,
        *,
        own: str | None = None,
        own_parts: list[str] | None = None,
        test_id: str | None = None,
        now: datetime | None = None,
    ) -> str:
        if consent != CONSENT:
            raise HTTPException(422, "Cần đồng ý với thông báo trước khi gửi bài.")
        text = unicodedata.normalize("NFC", text).strip()
        if not text or len(text) > MAX_CHARS:
            raise HTTPException(422, f"Bài viết cần từ 1 đến {MAX_CHARS} ký tự.")
        now = now or datetime.now(UTC)
        with self.pool().connection() as conn, conn.transaction():
            learner = self._learner(conn, learner_id)
            over: bool | None = None
            test: UUID | None = None
            if test_id is not None:
                test = _uuid(test_id)
                started = conn.execute(
                    "select prompt_id, own_prompt, started_at, time_limit_s, own_parts "
                    "from writing_tests where id=%s and learner_id=%s for update",
                    (test, learner),
                ).fetchone()
                if started is None:
                    raise HTTPException(404, "Không tìm thấy bài thi.")
                if conn.execute("select 1 from essays where test_id=%s", (test,)).fetchone():
                    raise HTTPException(409, "Bài thi này đã được nộp.")
                prompt_id, own, own_parts = started[0], started[1], started[4]
                over = (now - started[2]).total_seconds() > started[3] + TEST_GRACE_SECONDS
            prompt = self._checked_prompt(prompt_id, own, learner, own_parts)
            today = conn.execute(
                "select count(*) from essays where learner_id=%s and submitted_at >= %s "
                "and status <> 'failed'",  # a failed analysis is not the learner's try
                (learner, start_of_day(now)),
            ).fetchone()
            assert today is not None
            if self.plans is not None:
                plan, limits = self.plans.limits_of(conn, learner)
                allowed, named = limits.essays_per_day, f" (gói {NAMES_VI[plan]})"
            else:
                allowed, named = self.daily_essays, ""
            if today[0] >= allowed:
                raise HTTPException(
                    429, f"Hôm nay bạn đã gửi {allowed} bài{named}. Hẹn bạn ngày mai nhé."
                )
            own_text, kept = _own_columns(prompt_id, prompt)
            row = conn.execute(
                "insert into essays(learner_id,prompt_id,own_prompt,own_parts,text,consent,"
                "submitted_at,test_id,over_time) values (%s,%s,%s,%s,%s,%s,%s,%s,%s) returning id",
                (learner, prompt_id, own_text, kept, text, consent, now, test, over),
            ).fetchone()
        assert row is not None
        return str(row[0])

    def list(self, learner_id: str) -> list[dict[str, Any]]:
        with self.pool().connection() as conn:
            learner = self._learner(conn, learner_id)
            rows = conn.execute(
                "select id,prompt_id,status,result->>'words',submitted_at,own_prompt,test_id "
                "from essays where learner_id=%s order by submitted_at desc",
                (learner,),
            ).fetchall()
        return [
            {"id": str(r[0]), "prompt_id": r[1], "status": r[2],
             "words": int(r[3]) if r[3] is not None else None, "submitted_at": r[4],
             "own_prompt": r[5], "timed": r[6] is not None}
            for r in rows
        ]  # fmt: skip

    def get(self, learner_id: str, essay_id: str) -> dict[str, Any]:
        with self.pool().connection() as conn:
            learner = self._learner(conn, learner_id)
            row = conn.execute(
                "select e.id,e.prompt_id,e.text,e.status,e.submitted_at,e.result,e.failure_vi,"
                "e.own_prompt,e.over_time,t.started_at,t.time_limit_s,e.own_parts from essays e "
                "left join writing_tests t on t.id = e.test_id where e.id=%s and e.learner_id=%s",
                (_uuid(essay_id), learner),
            ).fetchone()
        if row is None:
            raise HTTPException(404, "Không tìm thấy bài viết.")
        prompt = prompt_for(self.bank(), row[1], row[7], row[11])
        from app.services.rewrites import rewrites_of

        with self.pool().connection() as conn:
            rewrites = rewrites_of(conn, row[0])
            states = conn.execute(
                "select issue_id, tries, accepted, answer_shown from essay_corrections "
                "where essay_id=%s",
                (row[0],),
            ).fetchall()
        return {
            "rewrites": rewrites,
            "corrections": {
                str(s[0]): {"tries": s[1], "accepted": s[2], "answer_shown": s[3]} for s in states
            },
            "id": str(row[0]),
            "prompt": prompt.model_dump() if prompt else None,
            "text": row[2],
            "status": row[3],
            "submitted_at": row[4],
            # keys starting with "_" are for measurement only (e.g. the model's own bands)
            "result": {k: v for k, v in row[5].items() if not k.startswith("_")}
            if row[5]
            else None,
            "failure_vi": row[6],
            "test": None if row[9] is None else _test_view(row[4], row[8], row[9], row[10]),
        }

    def delete(self, learner_id: str, essay_id: str) -> None:
        with self.pool().connection() as conn, conn.transaction():
            learner = self._learner(conn, learner_id)
            gone = conn.execute(
                "delete from essays where id=%s and learner_id=%s returning id",
                (_uuid(essay_id), learner),
            ).fetchone()
        if gone is None:
            raise HTTPException(404, "Không tìm thấy bài viết.")


@dataclass
class GrammarStep:
    """What the worker needs for step 2.2, loaded once (spaCy takes about a second)."""

    nlp: Any
    annotator: Any
    error_map: ErrorMap
    course: CourseSpec
    client: LanguageToolClient | None  # None: LANGUAGETOOL_URL not set, grammar is not checked
    draft_learners: frozenset[UUID] = frozenset()
    scorer: ScorerClient | None = None  # None: SCORER_URL not set, no band (step 2.3)
    scorer_config: ScorerConfig | None = None
    model: WritingModel | None = None  # None: no model key; no feedback (step 2.4)
    writing_dir: Path = Path("data/writing")
    # Step 2.12: only loaded when scorer.yaml's method is not "scorer"
    word_index: WordIndex | None = None
    cap_rules: tuple[CapRule, ...] = ()
    _ids: tuple[UUID, dict[str, UUID]] | None = None

    def evidence_allowed(self, learner: UUID) -> bool:
        return self.error_map.status == "reviewed" or learner in self.draft_learners

    def ids(self, conn: psycopg.Connection[Any]) -> tuple[UUID, dict[str, UUID]]:
        if self._ids is None:
            concept_ids = sync_course(conn, self.course)
            row = conn.execute(
                "select id from subjects where slug=%s", (self.course.slug,)
            ).fetchone()
            assert row is not None
            self._ids = (row[0], concept_ids)
        return self._ids


def load_grammar_step(
    writing_dir: Path,
    courses_dir: Path,
    languagetool_url: str,
    draft_learners: str = "",
    scorer_url: str = "",
    model: WritingModel | None = None,
    forms_yaml: Path | None = None,
) -> GrammarStep:
    import errant
    import spacy

    nlp = spacy.load("en_core_web_sm")
    error_map = load_error_map(writing_dir / "error-map.yaml")
    course = load_course(courses_dir / f"{error_map.course}.yaml")
    if problems := error_map.problems(course):
        raise ValueError("; ".join(problems))
    scorer_config = load_scorer_config(writing_dir / "scorer.yaml")
    word_index: WordIndex | None = None
    cap_rules: tuple[CapRule, ...] = ()
    if scorer_config.method != "scorer":
        # A band from descriptor features needs the word index it was fitted with: fail at start.
        if forms_yaml is None or not forms_yaml.exists():
            raise ValueError(f"scorer.yaml method {scorer_config.method} needs {forms_yaml}")
        word_index = load_word_index(forms_yaml)
        cap_rules = load_caps(writing_dir / "caps.yaml").rules
    return GrammarStep(
        nlp=nlp,
        annotator=errant.load("en", nlp),
        error_map=error_map,
        course=course,
        client=LanguageToolClient(languagetool_url) if languagetool_url else None,
        draft_learners=frozenset(
            learner_uuid(x.strip()) for x in draft_learners.split(",") if x.strip()
        ),
        scorer=ScorerClient(scorer_url) if scorer_url else None,
        scorer_config=scorer_config,
        model=model,
        writing_dir=writing_dir,
        word_index=word_index,
        cap_rules=cap_rules,
    )


def model_features(
    text: str,
    prompt: Prompt | None,
    result: dict[str, Any],
    grammar: GrammarResult | None,
    learner: UUID,
    step: GrammarStep,
) -> list[Issue]:
    """Feedback and the corrections the tools missed (step 2.4); fills `result`, returns AI issues.

    Only for DRAFT_ITEM_LEARNERS (the owner's decision until the privacy review). Every model call
    is budgeted and recorded; whatever fails leaves the tool results intact and says why.
    """
    result["feedback"] = None
    if step.model is None:
        result["feedback_unavailable_vi"] = FEEDBACK_OFF_VI
        return []
    if learner not in step.draft_learners:
        result["feedback_unavailable_vi"] = FEEDBACK_HIDDEN_VI
        return []
    model = step.model
    found: list[Issue] = []
    try:
        if grammar is not None:
            sents = [Sentence(s.start_char, s.text) for s in step.nlp(text).sents if words(s.text)]
            todo = unflagged(sents, grammar.issues)
            if todo:
                with timed(result, "corrections"):  # one model call
                    out = model.complete(learner, "writing_correct", llm_corrections.SYSTEM,
                                         llm_corrections.prompt([s.text for s in todo]),
                                         CorrectionsOut)  # fmt: skip
                found, discarded = llm_corrections.corrections(
                    todo, out, step.annotator, step.error_map, first_id=len(grammar.issues)
                )
                result["llm_corrections"] = {"kept": len(found), "discarded": discarded}
        measures = {k: result.get(k) for k in ("words", "sentences", "paragraphs",
                                               "linking_groups_used", "complexity")}  # fmt: skip
        if grammar is not None:
            measures["languagetool_errors"] = [
                {"text": i.text, "type": i.errant_type} for i in grammar.issues[:30]
            ]
        task_prompt = prompt.prompt if prompt else ""
        if prompt is not None and prompt.figure is not None:  # Task 1 (step 2.5)
            system = feedback.SYSTEM_TASK1
            user = feedback.task1_prompt(task_prompt, text, measures, task1.describe(prompt.figure))
        else:
            system, user = feedback.SYSTEM, feedback.prompt(task_prompt, text, measures)
        with timed(result, "feedback"):  # one model call
            out_fb = model.complete(learner, "writing_feedback", system, user, FeedbackOut)
        fb = feedback.verify(text, out_fb)
        result["feedback"] = fb.to_json(model.last_model)
        result["feedback_unavailable_vi"] = None
        overall = feedback.overall_band(list(fb.bands.values()))
        result["_llm_bands"] = fb.bands | {"overall": overall}  # never sent to the browser
        score = result.get("score")
        if score and not score["uncertain"]:
            reason = feedback.disagreement(score["band_low"], score["band_high"], overall)
            if reason:
                score["uncertain"], score["uncertain_reason"] = True, reason
    except BudgetExceeded:
        result["feedback_unavailable_vi"] = FEEDBACK_BUDGET_VI
    except Exception:
        logger.exception("writing model call failed")
        result["feedback_unavailable_vi"] = FEEDBACK_FAILED_VI
    return found


STRUCTURE_SHORT_VI = (
    f"Chưa kiểm tra cấu trúc: bài cần ít nhất {structure.MIN_PARAGRAPHS} đoạn (mở bài, thân bài, "
    "kết bài), cách nhau bằng một dòng trống."
)
STRUCTURE_BUDGET_VI = "Hôm nay đã dùng hết lượt kiểm tra cấu trúc bằng AI."
STRUCTURE_FAILED_VI = "Chưa kiểm tra được cấu trúc bài lần này."


def structure_check(
    text: str, prompt: Prompt | None, result: dict[str, Any], learner: UUID, step: GrammarStep
) -> None:
    """Step 2.11b: the structure of a Task 2 essay, described by the model and checked by code.

    Same gate as the feedback (owners only, a model configured); one budgeted call. The result
    is shown with its findings and never moves mastery. Without a model or for other learners
    the section is absent: the feedback's own reason already says why.
    """
    if prompt is None or prompt.task != 2 or not prompt.parts:
        return
    result["structure"], result["structure_unavailable_vi"] = None, None
    if step.model is None or learner not in step.draft_learners:
        return
    paras = paragraphs(text)
    if len(paras) < structure.MIN_PARAGRAPHS:
        result["structure_unavailable_vi"] = STRUCTURE_SHORT_VI
        return
    try:
        out = step.model.complete(learner, "writing_structure", structure.SYSTEM,
                                  structure.prompt(prompt.prompt, prompt.parts, paras),
                                  structure.StructureOut)  # fmt: skip
        found = structure.verify(paras, prompt.parts, out)
        result["structure"] = found.to_json(step.model.last_model)
    except BudgetExceeded:
        result["structure_unavailable_vi"] = STRUCTURE_BUDGET_VI
    except Exception:
        logger.exception("writing structure call failed")
        result["structure_unavailable_vi"] = STRUCTURE_FAILED_VI


def band_for(
    text: str,
    task: int,
    words: int,
    learner: UUID,
    step: GrammarStep,
    features: DescriptorFeatures | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    """The band range for this essay and learner, or why there is none (Vietnamese).

    Never a point: only the range from the calibration (specs/writing/step-2.3.md). While the
    scorer is a draft, only DRAFT_ITEM_LEARNERS see it.
    """
    if task != 2:  # Task 1 never gets a band, whatever the scorer's state (step 2.5)
        return None, BAND_REASONS_VI["task1"]
    config = step.scorer_config
    if config is None or (config.method == "scorer" and step.scorer is None):
        return None, BAND_OFF_VI
    if config.status == "draft" and learner not in step.draft_learners:
        return None, BAND_HIDDEN_VI
    if config.method != "scorer":
        return _descriptor_band(text, words, step, config, features)
    assert step.scorer is not None
    calibration = config.calibration.build() if config.calibration else None
    reason = no_band_reason(task, words, calibration)
    if reason is not None or calibration is None:
        return None, BAND_REASONS_VI[reason or "not_calibrated"]
    try:
        raw = step.scorer.score(text)
    except httpx.HTTPError:
        logger.exception("the scorer did not answer")
        return None, BAND_DOWN_VI
    if (raw.model, raw.revision) != (config.model, config.revision) or config.output >= len(
        raw.raw
    ):
        return None, BAND_MISMATCH_VI
    r = band_range(calibration.isotonic(raw.raw[config.output]), calibration)
    return {
        "band_low": r.low,
        "band_high": r.high,
        "uncertain": r.uncertain,
        "model": config.model,
        "revision": config.revision,
        "status": config.status,
        "truncated": raw.truncated,
    }, None


def _descriptor_band(
    text: str,
    words: int,
    step: GrammarStep,
    config: ScorerConfig,
    features: DescriptorFeatures | None,
) -> tuple[dict[str, Any] | None, str | None]:
    """The range from the descriptor model, or its blend with the pinned scorer (step 2.12).

    Only the overall range is returned; the criterion bands stay hidden until each one passes its
    own gate (`specs/writing/spec.md`, 8b). Without a grammar analysis there is no band: the
    features that count errors would otherwise read as an essay with none.
    """
    block = config.descriptors
    assert block is not None  # ScorerConfig refuses a method without its block
    if words < MIN_WORDS_FOR_BAND:
        return None, BAND_REASONS_VI["too_short"]
    if features is None:
        return None, BAND_NO_GRAMMAR_VI
    value = block.build().predict(features.as_dict(), applied_caps(step.cap_rules, text)).overall
    truncated = False
    if config.method == "blend":
        assert config.calibration is not None
        if step.scorer is None:
            return None, BAND_OFF_VI
        try:
            raw = step.scorer.score(text)
        except httpx.HTTPError:
            logger.exception("the scorer did not answer")
            return None, BAND_DOWN_VI
        if (raw.model, raw.revision) != (config.model, config.revision) or config.output >= len(
            raw.raw
        ):
            return None, BAND_MISMATCH_VI
        value = (config.calibration.build().isotonic(raw.raw[config.output]) + value) / 2
        truncated = raw.truncated
    r = residual_band_range(value, block.residual_low, block.residual_high)
    return {
        "band_low": r.low,
        "band_high": r.high,
        "uncertain": r.uncertain,
        "model": config.method,
        "revision": block.fitted_on,
        "status": config.status,
        "truncated": truncated,
    }, None


def score_preview(
    text: str, task: int, words: int, learner: UUID, step: GrammarStep, earlier: Sequence[float]
) -> dict[str, Any] | None:
    """The owner's preview while the scorer is uncalibrated (16 Nov 2026), or None.

    Only for DRAFT_ITEM_LEARNERS, only Task 2 essays long enough for a band, only while there is
    no calibration: the model's raw "Overall" output and how it compares with the learner's
    earlier ones. Raw output is not on the IELTS scale (step 2.3), so no band is derived from it.
    """
    config = step.scorer_config
    if (
        task != 2
        or config is None
        or step.scorer is None
        or config.calibration is not None
        or learner not in step.draft_learners
        or no_band_reason(task, words, None) != "not_calibrated"
    ):
        return None
    try:
        raw = step.scorer.score(text)
    except httpx.HTTPError:
        logger.exception("the scorer did not answer")
        return None
    if (raw.model, raw.revision) != (config.model, config.revision) or config.output >= len(
        raw.raw
    ):
        return None
    value = float(raw.raw[config.output])
    c = compare_raw(value, earlier)
    return {
        "raw": round(value, 2),
        "compared": len(earlier),
        "higher": c.higher,
        "lower": c.lower,
        "same": c.same,
        "model": config.model,
        "revision": config.revision,
        "truncated": raw.truncated,
    }


def _earlier_raw(conn: psycopg.Connection[Any], learner: UUID, essay_id: Any) -> list[float]:
    rows = conn.execute(
        "select (result->'score_preview'->>'raw')::float from essays where learner_id=%s "
        "and id<>%s and status='done' and result->'score_preview' ? 'raw'",
        (learner, essay_id),
    ).fetchall()
    return [float(r[0]) for r in rows]


def _analyse(
    text: str, task: int, writing_dir: Path, step: GrammarStep | None
) -> tuple[dict[str, Any], GrammarResult | None]:
    """The essay's result (version 2 with a grammar step) and the grammar analysis; no database."""
    linking = load_linking_words(writing_dir / "linking-words.yaml")
    if step is None:
        result = analyse(text, task, linking).to_json()
        result["note_vi"] = NOTE_VI
        return result, None
    grammar: GrammarResult | None = None
    unavailable: str | None = None
    if step.client is None:
        unavailable = GRAMMAR_OFF_VI
    else:
        try:
            grammar = analyse_grammar(
                text, step.client.matches(text), step.nlp, step.annotator, step.error_map
            )
        except httpx.HTTPError:
            logger.exception("LanguageTool did not answer")
            unavailable = GRAMMAR_DOWN_VI
    sents = (
        list(grammar.sentences)
        if grammar
        else [s.text for s in step.nlp(text).sents if words(s.text)]
    )
    result = analyse(text, task, linking, sentence_texts=sents).to_json()
    result |= {
        "version": 2,
        "note_vi": NOTE_VI,
        "grammar": None
        if grammar is None
        else {"checker": "LanguageTool", "issues": [], "counts": grammar.counts()},
        "grammar_unavailable_vi": unavailable,
        "complexity": asdict(
            grammar.complexity
            if grammar
            else complexity([s for s in step.nlp(text).sents if words(s.text)])
        ),
        "evidence": [],
    }
    return result, grammar


def _descriptor_features(
    text: str,
    prompt: Prompt | None,
    task: int,
    grammar: GrammarResult | None,
    guard: guardrails.Guard,
    step: GrammarStep,
    writing_dir: Path,
) -> DescriptorFeatures | None:
    """The features for a band from descriptors, or None when none are needed or possible."""
    config = step.scorer_config
    if config is None or config.method == "scorer" or task != 2 or grammar is None:
        return None
    assert step.word_index is not None  # load_grammar_step loads it for these methods
    return measure_essay(
        text,
        prompt.prompt if prompt else "",
        grammar=grammar,
        nlp=step.nlp,
        index=step.word_index,
        linking_groups=load_linking_words(writing_dir / "linking-words.yaml"),
        guard=guard,
    )


def _apply_evidence(
    conn: psycopg.Connection[Any],
    learner: UUID,
    essay_id: UUID,
    grammar: GrammarResult,
    step: GrammarStep,
    now: datetime,
) -> tuple[list[Issue], list[dict[str, Any]]]:
    """BKT updates for the chosen errors (point 6). Returns the issues, marked, and what moved."""
    chosen = (
        choose_evidence(grammar.issues, step.error_map.max_evidence_per_essay)
        if step.evidence_allowed(learner)
        else []
    )
    if not chosen:
        return list(grammar.issues), []
    subject, ids = step.ids(conn)
    params = step.error_map.params()
    rows = conn.execute(
        "select concept_id, p_known from mastery where learner_id=%s and concept_id = any(%s)",
        (learner, [ids[i.node] for i in chosen if i.node]),
    ).fetchall()
    known = {r[0]: float(r[1]) for r in rows}
    moved = []
    for issue in chosen:
        assert issue.node is not None
        p = known.get(ids[issue.node], UNSEEN_P_KNOWN)
        p_new, trace = bkt.update_traced(
            p, False, params, concept_slug=issue.node, now=now,
            item_id=f"essay:{essay_id}:{issue.id}", misconception=f"writing:{issue.errant_type}",
        )  # fmt: skip
        trace = trace.model_copy(
            update={
                "rule": "writing.error",
                "rule_vi": (
                    f"Bài viết có lỗi: {issue.explain_vi} → khả năng đã nắm vững giảm từ "
                    f"{fmt_p(p)} xuống {fmt_p(p_new)}. Lỗi khi viết tự do được tính nhẹ hơn câu "
                    f"trắc nghiệm (xác suất trượt {fmt_p(params.p_slip)}, "
                    f"đoán đúng {fmt_p(params.p_guess)})."
                ),
            }
        )
        save_mastery(conn, learner, ids[issue.node], p_new)
        save_trace(conn, learner, subject, trace)
        moved.append({"node": issue.node, "errant_type": issue.errant_type, "issue_id": issue.id,
                      "p_before": round(p, 4), "p_after": round(p_new, 4)})  # fmt: skip
    used = {i.id for i in chosen}
    return [replace(i, evidence=i.id in used) for i in grammar.issues], moved


def _competency_allowed(step: "GrammarStep", learner: UUID) -> bool:
    """Draft rules count only for the owners (specs/two-layer-map/writing-evidence.md)."""
    return competency_evidence.rules(step.writing_dir).status == "reviewed" or (
        learner in step.draft_learners
    )


def requeue_stuck_essays(database_url: str) -> int:
    """At worker start: an essay left `analysing` by a stopped worker goes back to the queue.

    One worker claims essays, so at start nothing can legitimately be analysing.
    """
    with psycopg.connect(database_url) as conn:
        return conn.execute("update essays set status='queued' where status='analysing'").rowcount


def process_next_essay(
    database_url: str,
    writing_dir: Path,
    step: GrammarStep | None = None,
    *,
    now: datetime | None = None,
) -> bool:
    """Claim and analyse one queued essay; False when there is none (the worker then sleeps).

    Without a grammar step this is step 2.1's analysis. The result and any mastery evidence are
    written in one transaction, so a retried job never counts an essay twice.
    """
    with psycopg.connect(database_url) as conn:
        with conn.transaction():
            row = conn.execute(
                "select id,learner_id,prompt_id,text,own_prompt,own_parts from essays "
                "where status='queued' order by submitted_at,id limit 1 for update skip locked"
            ).fetchone()
            if row is None:
                return False
            conn.execute("update essays set status='analysing' where id=%s", (row[0],))
        essay_id, learner, prompt_id, text, own, own_parts = row
        try:
            prompt = prompt_for(
                load_prompts(writing_dir / "prompts.yaml"), prompt_id, own, own_parts
            )
            task = prompt.task if prompt else 2
            clock: dict[str, Any] = {}
            started = time.perf_counter()
            with timed(clock, "analyse"):  # LanguageTool, spaCy and ERRANT
                result, grammar = _analyse(text, task, writing_dir, step)
            result[TIMINGS] = clock[TIMINGS]
            result["task"] = task
            # Step 2.7: text that is not the learner's own answer does not count towards a band.
            with timed(result, "checks"):  # the guard and, for Task 1, the chart's facts
                guard = guardrails.check(
                    text,
                    prompt.prompt if prompt else None,
                    guardrails.load_templates(writing_dir / "templates.yaml"),
                )
                result["guard"] = guard.to_json()
                if prompt is not None and prompt.figure is not None:
                    result["task1"] = task1.check(text, prompt.figure).to_json()
            ai_issues: list[Issue] = []
            if step is not None and guard.padded and task == 2:
                result["score"], result["score_unavailable_vi"] = None, BAND_REASONS_VI["padded"]
            elif step is not None:
                with timed(result, "band"):  # descriptor features and the band model's service
                    result["score"], result["score_unavailable_vi"] = band_for(
                        text, task, guard.own_words, learner, step,
                        _descriptor_features(text, prompt, task, grammar, guard, step, writing_dir),
                    )  # fmt: skip
                    if result["score"] is None:
                        result["score_preview"] = score_preview(
                            text, task, guard.own_words, learner, step,
                            _earlier_raw(conn, learner, essay_id),
                        )  # fmt: skip
            if step is not None:
                ai_issues = model_features(text, prompt, result, grammar, learner, step)
                with timed(result, "structure"):  # one model call
                    structure_check(text, prompt, result, learner, step)
            with conn.transaction():
                with timed(result, "evidence"):  # mastery evidence, in this transaction
                    if grammar is not None and step is not None:
                        issues, moved = _apply_evidence(
                            conn, learner, essay_id, grammar, step, now or datetime.now(UTC)
                        )
                        names = {c.slug: c.name_vi for c in step.course.concepts}
                        result["grammar"]["issues"] = [
                            i.to_json() | {"node_vi": names.get(i.node) if i.node else None}
                            for i in [*issues, *ai_issues]
                        ]
                        result["evidence"] = moved
                    if step is not None and _competency_allowed(step, learner):
                        rules = competency_evidence.rules(writing_dir)
                        found = competency.observations(
                            rules, result, text, task, competency_evidence.known_b1()
                        )
                        result["competency_evidence"] = competency_evidence.apply(
                            conn, learner, essay_id, found, rules.params(), now or datetime.now(UTC)
                        )
                result[TIMINGS]["total"] = round(time.perf_counter() - started, 3)
                conn.execute(
                    "update essays set status='done', result=%s, analysed_at=now() where id=%s",
                    (Jsonb(result), essay_id),
                )
            logger.info(
                "essay analysed",
                extra={"essay_id": str(essay_id), "seconds": result[TIMINGS]},
            )
        except Exception:
            logger.exception("essay analysis failed", extra={"essay_id": str(essay_id)})
            with conn.transaction():
                conn.execute(
                    "update essays set status='failed', failure_vi=%s, analysed_at=now() "
                    "where id=%s",
                    ("Không phân tích được bài viết. Bạn thử gửi lại sau nhé.", essay_id),
                )
        return True


_TOKENS = re.compile(r"\w+|[^\w\s]")


def _distance(a: str, b: str) -> int:
    return edit_distance(_TOKENS.findall(a), _TOKENS.findall(b))
