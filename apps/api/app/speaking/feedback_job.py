"""The worker step for the model's Speaking feedback (specs/speaking/step-5.3b.md).

One queued answer per call: claim it, call the model with no transaction open (a slow call
must not hold a row lock), check the quotes, store the points or the reason it failed. A model
that is not configured, a spent budget and any other failure all end as `failed` with a message
the page shows; the learner may ask again (a few times). A `working` row left by a stopped
worker is queued again when the worker starts.
"""

import logging
from typing import Any, Protocol
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb
from pydantic import BaseModel

from app.speaking.feedback import SYSTEM, FeedbackOut, check, part_of, prompt

logger = logging.getLogger(__name__)

NO_MODEL = "Nhận xét bằng AI chưa được bật trên máy chủ này."
BUDGET = "Hôm nay đã dùng hết lượt nhận xét bằng AI. Mai thử lại nhé."
FAILED = "Chưa tạo được nhận xét lúc này. Bạn thử lại sau nhé."
EMPTY = (
    "AI chưa đưa ra được điểm nào có trích dẫn khớp với bản chép, "
    "nên không có nhận xét để hiển thị."
)


class Model(Protocol):
    def complete[T: BaseModel](
        self, learner: UUID, task: str, system: str, user: str, schema: type[T]
    ) -> T: ...

    last_model: str


def requeue_stuck(database_url: str) -> int:
    """Answers left `working` by a stopped worker are queued again."""
    with psycopg.connect(database_url) as conn:
        return conn.execute(
            "update speaking_answers set feedback_status='queued' where feedback_status='working'"
        ).rowcount


def process_next_feedback(database_url: str, model: Model | None) -> bool:
    """Write the feedback of the oldest queued answer; False when there is none."""
    from app.writing.model_calls import BudgetExceeded

    with psycopg.connect(database_url) as conn, conn.transaction():
        row = conn.execute(
            "select a.id, t.learner_id, a.question, a.question_id, a.transcript "
            "from speaking_answers a join speaking_tests t on t.id=a.sitting_id "
            "where a.feedback_status='queued' order by a.feedback_requested_at, a.id "
            "limit 1 for update of a skip locked"
        ).fetchone()
        if row is None:
            return False
        answer, learner, question, question_id, transcript = row
        conn.execute("update speaking_answers set feedback_status='working' where id=%s", (answer,))
    text = str((transcript or {}).get("text", "")).strip()
    result: dict[str, Any]
    if model is None:
        result = {"failed": NO_MODEL}
    elif not text:
        result = {"failed": FAILED}
    else:
        try:
            out = model.complete(
                learner,
                "speaking_feedback",
                SYSTEM,
                prompt(question, part_of(question_id), text),
                FeedbackOut,
            )
            checked = check(out, text)
            result = (
                {
                    "points": checked.points,
                    "dropped": checked.dropped,
                    "quotes_checked": checked.quotes_checked,
                    "model": model.last_model,
                }
                if checked.points
                else {"failed": EMPTY, "dropped": checked.dropped}
            )
        except BudgetExceeded:
            result = {"failed": BUDGET}
        except Exception:
            logger.exception("speaking feedback failed", extra={"answer_id": str(answer)})
            result = {"failed": FAILED}
    with psycopg.connect(database_url) as conn:
        conn.execute(
            "update speaking_answers set feedback_status=%s, feedback=%s, feedback_at=now() "
            "where id=%s",
            ("failed" if "failed" in result else "done", Jsonb(result), answer),
        )
    return True
