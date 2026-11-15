"""Rewrites (worker job) and saved phrases (FSRS cards) for writing step 2.4b.

specs/writing/step-2.4.md, points 4 and 5. The model rewrites one paragraph; the code computes
what changed, keeps a reason only next to a real change, and accepts the rewrite only if it stays
a rewrite in length, LanguageTool finds no error in it, and (once calibrated) the scorer rates the
essay higher with it. Otherwise it is regenerated once, then rejected with the reason.
"""

import logging
import re
import unicodedata
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
from fastapi import HTTPException
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from app.engine import srs
from app.graders.typed import grade_typed
from app.services.backend import learner_uuid, save_trace
from app.services.writing import FEEDBACK_BUDGET_VI, FEEDBACK_OFF_VI, GrammarStep
from app.writing import rewrite as rw
from app.writing.languagetool import NEVER_MAPPED_CATEGORIES
from app.writing.model_calls import BudgetExceeded
from app.writing.prompts import load_prompts

logger = logging.getLogger(__name__)
MAX_REWRITES_PER_ESSAY = 3
PHRASE_LIST = "my-phrases"
MAX_PHRASE_WORDS = 12
NO_LANGUAGETOOL_VI = "Chưa viết lại được: cần bật LanguageTool để kiểm tra bản viết lại."
FAILED_VI = "Chưa viết lại được lần này. Bạn thử lại sau nhé."
TOO_DIFFERENT_VI = "Bản viết lại dài hoặc ngắn hơn quá nhiều so với đoạn gốc."
UNCHANGED_VI = "Bản viết lại không thay đổi gì so với đoạn gốc."
LT_ERRORS_VI = "LanguageTool vẫn tìm thấy lỗi trong bản viết lại."
NOT_HIGHER_VI = "Mô hình chấm không đánh giá bản viết lại cao hơn đoạn gốc."


def _uuid(value: str, what: str = "bài viết") -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(404, f"Không tìm thấy {what}.") from None


def request_rewrite(
    pool: Callable[[], ConnectionPool],
    draft_learners: set[UUID],
    learner_id: str,
    essay_id: str,
    paragraph: int,
) -> str:
    """Queue a rewrite of one paragraph (202). Model features: DRAFT_ITEM_LEARNERS only."""
    learner = learner_uuid(learner_id)
    if learner not in draft_learners:
        raise HTTPException(403, "Viết lại bằng AI đang được thử nghiệm, chưa mở cho mọi người.")
    with pool().connection() as conn, conn.transaction():
        row = conn.execute(
            "select text, result from essays where id=%s and learner_id=%s and status='done' "
            "for update",
            (_uuid(essay_id), learner),
        ).fetchone()
        if row is None:
            raise HTTPException(404, "Không tìm thấy bài viết.")
        if not 0 <= paragraph < len(rw.split_paragraphs(row[0])):
            raise HTTPException(422, "Không có đoạn văn này.")
        count = conn.execute(
            "select count(*) from essay_rewrites where essay_id=%s", (_uuid(essay_id),)
        ).fetchone()
        assert count is not None
        if count[0] >= MAX_REWRITES_PER_ESSAY:
            raise HTTPException(
                429, f"Mỗi bài viết được viết lại tối đa {MAX_REWRITES_PER_ESSAY} lần."
            )
        target = rw.target_band((row[1] or {}).get("score"))
        new = conn.execute(
            "insert into essay_rewrites(essay_id,learner_id,paragraph,target_band) "
            "values (%s,%s,%s,%s) returning id",
            (_uuid(essay_id), learner, paragraph, target),
        ).fetchone()
    assert new is not None
    return str(new[0])


def rewrites_of(conn: psycopg.Connection[Any], essay_id: UUID) -> list[dict[str, Any]]:
    rows = conn.execute(
        "select id, paragraph, target_band, status, result, reason_vi from essay_rewrites "
        "where essay_id=%s order by created_at",
        (essay_id,),
    ).fetchall()
    return [
        {"id": str(r[0]), "paragraph": r[1], "target_band": float(r[2]), "status": r[3],
         "result": r[4], "reason_vi": r[5]}
        for r in rows
    ]  # fmt: skip


def _check(
    original_essay: str, paragraph: str, out: rw.RewriteOut, step: GrammarStep
) -> tuple[str | None, dict[str, str]]:
    """Why the rewrite is rejected (None when accepted), and which checks ran."""
    checks = {"length": "passed", "languagetool": "not_run", "scorer": "not_run",
              "cefr": "not_run"}  # fmt: skip
    if not rw.length_ok(paragraph, out.paragraph):
        checks["length"] = "failed"
        return TOO_DIFFERENT_VI, checks
    if not rw.diff(paragraph, out.paragraph):
        return UNCHANGED_VI, checks
    assert step.client is not None
    flagged = [m for m in step.client.matches(out.paragraph)
               if m.category not in NEVER_MAPPED_CATEGORIES]  # fmt: skip
    checks["languagetool"] = "failed" if flagged else "passed"
    if flagged:
        return LT_ERRORS_VI, checks
    config = step.scorer_config
    if step.scorer and config and config.calibration:
        before = step.scorer.score(original_essay).raw[config.output]
        after = step.scorer.score(original_essay.replace(paragraph, out.paragraph, 1)).raw[
            config.output
        ]
        checks["scorer"] = "passed" if after > before else "failed"
        if after <= before:
            return NOT_HIGHER_VI, checks
    return None, checks


def process_next_rewrite(database_url: str, step: GrammarStep) -> bool:
    """Claim and run one queued rewrite; False when there is none."""
    with psycopg.connect(database_url) as conn:
        with conn.transaction():
            row = conn.execute(
                "select r.id, r.learner_id, r.paragraph, r.target_band, e.text, e.prompt_id "
                "from essay_rewrites r join essays e on e.id = r.essay_id "
                "where r.status='queued' order by r.created_at limit 1 for update of r skip locked"
            ).fetchone()
            if row is None:
                return False
            conn.execute("update essay_rewrites set status='working' where id=%s", (row[0],))
        rewrite_id, learner, index, target, text, prompt_id = row

        def finish(status: str, result: dict[str, Any] | None, reason: str | None, n: int) -> None:
            with conn.transaction():
                conn.execute(
                    "update essay_rewrites set status=%s, result=%s, reason_vi=%s, attempts=%s, "
                    "finished_at=now() where id=%s",
                    (status, Jsonb(result) if result else None, reason, n, rewrite_id),
                )

        if step.model is None:
            finish("failed", None, FEEDBACK_OFF_VI, 0)
            return True
        if step.client is None:
            finish("failed", None, NO_LANGUAGETOOL_VI, 0)
            return True
        paragraph = rw.split_paragraphs(text)[index]
        prompt = load_prompts(step_writing_dir(step)).get(prompt_id)
        reason: str | None = None
        attempts = 0
        try:
            for attempts in (1, 2):
                out = step.model.complete(learner, "writing_rewrite", rw.SYSTEM,
                                          rw.prompt(prompt.prompt if prompt else "", paragraph,
                                                    float(target)),
                                          rw.RewriteOut)  # fmt: skip
                reason, checks = _check(text, paragraph, out, step)
                if reason is None:
                    changes, unmatched = rw.attach_reasons(rw.diff(paragraph, out.paragraph),
                                                           out.changes, paragraph,
                                                           out.paragraph)  # fmt: skip
                    finish("done", {"original": paragraph, "rewrite": out.paragraph,
                                    "changes": rw.as_json(changes), "unmatched_reasons": unmatched,
                                    "checks": checks, "model": step.model.last_model},
                           None, attempts)  # fmt: skip
                    return True
            finish("rejected", None, reason, attempts)
        except BudgetExceeded:
            finish("failed", None, FEEDBACK_BUDGET_VI, attempts)
        except Exception:
            logger.exception("rewrite failed", extra={"rewrite_id": str(rewrite_id)})
            finish("failed", None, FAILED_VI, attempts)
        return True


def step_writing_dir(step: GrammarStep) -> Path:
    """The prompts file of the step's writing data (data/writing/prompts.yaml)."""
    return step.writing_dir / "prompts.yaml"


# --- saved phrases ------------------------------------------------------------------------------


def _subject(conn: psycopg.Connection[Any]) -> UUID:
    row = conn.execute(
        "insert into subjects(slug,name_vi,name_en) values (%s,%s,%s) "
        "on conflict(slug) do update set name_vi=excluded.name_vi returning id",
        (f"vocabulary-{PHRASE_LIST}", "Cụm từ đã lưu", "Saved phrases"),
    ).fetchone()
    assert row is not None
    return row[0]  # type: ignore[no-any-return]


def _blank(sentence: str, phrase: str) -> str:
    """The sentence with the phrase replaced by a gap (case-insensitive, first occurrence)."""
    return re.sub(re.escape(phrase), "_____", sentence, count=1, flags=re.IGNORECASE)


class PhraseService:
    def __init__(self, pool: Callable[[], ConnectionPool]) -> None:
        self.pool = pool

    def _learner(self, conn: psycopg.Connection[Any], learner_id: str) -> UUID:
        learner = learner_uuid(learner_id)
        if not conn.execute("select 1 from learners where id=%s", (learner,)).fetchone():
            raise HTTPException(404, "Không tìm thấy người học.")
        return learner

    def save(self, learner_id: str, rewrite_id: str, change: int) -> str:
        with self.pool().connection() as conn, conn.transaction():
            learner = self._learner(conn, learner_id)
            row = conn.execute(
                "select essay_id, result from essay_rewrites where id=%s and learner_id=%s "
                "and status='done'",
                (_uuid(rewrite_id, "bản viết lại"), learner),
            ).fetchone()
            if row is None:
                raise HTTPException(404, "Không tìm thấy bản viết lại.")
            changes = row[1]["changes"]
            if not 0 <= change < len(changes):
                raise HTTPException(404, "Không tìm thấy thay đổi này.")
            phrase = unicodedata.normalize("NFC", changes[change]["revised"]).strip(" .,;:")
            if not 1 <= len(phrase.split()) <= MAX_PHRASE_WORDS or len(phrase) < 2:
                raise HTTPException(422, "Chỉ lưu được cụm từ 1 đến 12 từ.")
            sentence = rw.sentence_with(row[1]["rewrite"], phrase)
            if sentence is None:
                raise HTTPException(422, "Không tìm thấy câu chứa cụm từ này.")
            new = conn.execute(
                "insert into learner_phrases(learner_id,essay_id,phrase,sentence) "
                "values (%s,%s,%s,%s) on conflict (learner_id, phrase) do nothing returning id",
                (learner, row[0], phrase, sentence),
            ).fetchone()
        if new is None:
            raise HTTPException(409, "Bạn đã lưu cụm từ này rồi.")
        return str(new[0])

    def session(
        self, learner_id: str, *, limit: int = 10, now: datetime | None = None
    ) -> dict[str, Any]:
        now = now or datetime.now(UTC)
        with self.pool().connection() as conn:
            learner = self._learner(conn, learner_id)
            rows = conn.execute(
                "select p.id, p.phrase, p.sentence, c.due_at from learner_phrases p "
                "left join vocab_cards c on c.learner_id=p.learner_id and c.list_slug=%s "
                "and c.word_key=p.id::text where p.learner_id=%s "
                "and (c.due_at is null or c.due_at <= %s) "
                "order by c.due_at nulls last, p.created_at limit %s",
                (PHRASE_LIST, learner, now, limit),
            ).fetchall()
            total = conn.execute(
                "select count(*) from learner_phrases where learner_id=%s", (learner,)
            ).fetchone()
        assert total is not None
        return {
            "saved": total[0],
            "entries": [
                {"phrase_id": str(r[0]), "prompt": _blank(r[2], r[1]), "hint": r[1][0],
                 "is_new": r[3] is None, "phrase": r[1] if r[3] is None else None}
                for r in rows
            ],
        }  # fmt: skip

    def answer(
        self, learner_id: str, phrase_id: str, answer: str, *, now: datetime | None = None
    ) -> dict[str, Any]:
        if len(answer) > 100:
            raise HTTPException(422, "Câu trả lời quá dài.")
        now = now or datetime.now(UTC)
        with self.pool().connection() as conn, conn.transaction():
            learner = self._learner(conn, learner_id)
            pid = _uuid(phrase_id, "cụm từ")
            row = conn.execute(
                "select phrase from learner_phrases where id=%s and learner_id=%s",
                (pid, learner),
            ).fetchone()
            if row is None:
                raise HTTPException(404, "Không tìm thấy cụm từ.")
            phrase = row[0]
            correct = grade_typed(answer, (phrase,))
            card = conn.execute(
                "select fsrs_state, reviews, lapses from vocab_cards where learner_id=%s "
                "and list_slug=%s and word_key=%s for update",
                (learner, PHRASE_LIST, str(pid)),
            ).fetchone()
            state = card[0] if card else srs.new_card(now).state
            review, trace = srs.review_traced(state, correct, now, concept_slug=f"phrase:{pid}",
                                              item_id=f"{PHRASE_LIST}|{pid}")  # fmt: skip
            conn.execute(
                "insert into vocab_cards(learner_id,list_slug,word_key,fsrs_state,due_at,reviews,"
                "lapses,created_at) values (%s,%s,%s,%s,%s,%s,%s,%s) "
                "on conflict(learner_id,list_slug,word_key) do update set "
                "fsrs_state=excluded.fsrs_state, due_at=excluded.due_at, "
                "reviews=excluded.reviews, lapses=excluded.lapses",
                (learner, PHRASE_LIST, str(pid), Jsonb(dict(review.state)), review.due_at,
                 (card[1] if card else 0) + 1, (card[2] if card else 0) + (0 if correct else 1),
                 now),
            )  # fmt: skip
            conn.execute(
                "insert into vocab_reviews(learner_id,list_slug,word_key,item_kind,correct,answer,"
                "due_at,answered_at) values (%s,%s,%s,'gapfill',%s,%s,%s,%s)",
                (learner, PHRASE_LIST, str(pid), correct, answer.strip(), review.due_at, now),
            )
            save_trace(conn, learner, _subject(conn), trace)
        return {"correct": correct, "accepted": phrase, "due_at": review.due_at}

    def delete(self, learner_id: str, phrase_id: str) -> None:
        with self.pool().connection() as conn, conn.transaction():
            learner = self._learner(conn, learner_id)
            pid = _uuid(phrase_id, "cụm từ")
            gone = conn.execute(
                "delete from learner_phrases where id=%s and learner_id=%s returning id",
                (pid, learner),
            ).fetchone()
            if gone is None:
                raise HTTPException(404, "Không tìm thấy cụm từ.")
            conn.execute(
                "delete from vocab_cards where learner_id=%s and list_slug=%s and word_key=%s",
                (learner, PHRASE_LIST, str(pid)),
            )
