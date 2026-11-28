"""The examiner test (specs/speaking/step-5.4a.md): sittings, recorded answers, replay, deletion.

No model call and no evidence: this step stores what was said so it can be heard again. Audio
follows the voice policy of phase 3: owner only until a privacy review, cleared after a day unless
the learner chose to keep it, and deletable at once. A bad recording is still stored here (an exam
answer is what it is); its quality check is kept so the result page can say "quá nhỏ" instead of
judging the answer.
"""

from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
from fastapi import HTTPException
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from app.pronunciation.quality import check
from app.services.backend import learner_uuid
from app.services.recordings import RETENTION
from app.speaking.measures import pooled
from app.speaking.tests import (
    CLOSING_SECONDS,
    LONG_TURN_SECONDS,
    PART1_SECONDS,
    PART3_SECONDS,
    PREPARE_SECONDS,
    Loaded,
    Question,
    load_tests,
    max_answer_seconds,
    questions,
)

BYTES_PER_SECOND = 32_000  # 16 kHz mono 16-bit
MAX_ANSWER_BYTES = 44 + BYTES_PER_SECOND * (LONG_TURN_SECONDS + 10)
MAX_CHECK_BYTES = 600_000  # the microphone check: a few seconds
# The test's own notice (messages/vi.ts, speakingTest.consent): the voice policy plus the
# transcript, which is kept with the sitting after the audio is gone (step 5.1).
CONSENT = "speaking-v1"
MIN_ANSWER_SECONDS = 0.3  # shorter is not a recording (a tap on "Xong" at once is still stored)


def _uuid(value: str, what: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(404, f"Không tìm thấy {what}.") from None


def purge_expired(conn: psycopg.Connection[Any], now: datetime | None = None) -> int:
    """Clear answers' audio past its time (the row stays); returns how many."""
    cur = conn.execute(
        "update speaking_answers set audio=null where delete_after is not null "
        "and delete_after <= %s and audio is not null",
        (now or datetime.now(UTC),),
    )
    return cur.rowcount


def _transcript(
    status: str | None,
    data: dict[str, Any] | None,
    audio: bool,
    enabled: bool,
    measures: dict[str, Any] | None = None,
    asked: int | None = None,
    language: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The answer's transcript for the page (step 5.1): done, failed, waiting (only when a
    recogniser is configured and the audio is still there), or none."""
    if status == "done" and data:
        return {
            "transcript": "done",
            "text": data.get("text", ""),
            "words": [
                {"word": w["word"], "start": w["start"], "end": w["end"]}
                for w in data.get("words", [])
            ],
            "measures": _with_share(measures, asked),
            "language": language,
        }
    if status == "failed":
        return {
            "transcript": "failed",
            "text": None,
            "words": [],
            "measures": None,
            "language": None,
        }
    waiting = "waiting" if audio and enabled else "none"
    return {
        "transcript": waiting,
        "text": None,
        "words": [],
        "measures": None,
        "language": None,
    }


def _with_share(measures: dict[str, Any] | None, asked: int | None) -> dict[str, Any] | None:
    """The stored measures with the time asked and the share of it spoken (known from the question,
    not from the audio)."""
    if measures is None:
        return None
    out = dict(measures)
    out["asked_seconds"] = asked
    out["share_of_time"] = (
        round(min(measures["speaking_seconds"] / asked, 9.99), 2) if asked else None
    )
    return out


class SpeakingTests:
    def __init__(
        self,
        pool: Callable[[], ConnectionPool],
        folder: Path,
        draft_learners: str,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        transcripts: bool = False,
    ) -> None:
        self.pool = pool
        self.transcripts = transcripts  # a recogniser is configured (ASR_URL, step 5.1)
        self.tests: dict[str, Loaded] = load_tests(folder)
        self.owners = {learner_uuid(x.strip()) for x in draft_learners.split(",") if x.strip()}
        self.clock = clock

    def _owner(self, learner_id: str) -> UUID:
        learner = learner_uuid(learner_id)
        if learner not in self.owners:
            raise HTTPException(
                403,
                "Ghi âm hiện chỉ mở cho chủ dự án, cho đến khi việc lưu giữ giọng nói được xem xét "
                "về quyền riêng tư.",
            )
        return learner

    @staticmethod
    def timing() -> dict[str, int]:
        return {
            "part1": PART1_SECONDS,
            "prepare": PREPARE_SECONDS,
            "long_turn": LONG_TURN_SECONDS,
            "closing": CLOSING_SECONDS,
            "part3": PART3_SECONDS,
        }

    def _content(self, loaded: Loaded) -> dict[str, Any]:
        t = loaded.test
        return {
            "id": t.id,
            "title": t.title,
            "draft": t.status == "draft",
            "part1_topics": [x.topic for x in t.part1],
            "cue_card": {
                "task": t.part2.task,
                "points": list(t.part2.points),
                "explain": t.part2.explain,
            },
            "part3_theme": t.part3.theme,
            "questions": [asdict(q) for q in questions(t)],
            "timing": self.timing(),
        }

    def overview(self, learner_id: str) -> dict[str, Any]:
        """The tests on offer and the learner's past sittings."""
        learner = learner_uuid(learner_id)
        can = learner in self.owners
        past: list[dict[str, Any]] = []
        if can:
            with self.pool().connection() as conn:
                purge_expired(conn, self.clock())
                rows = conn.execute(
                    "select t.id,t.test_id,t.keep,t.started_at,t.finished_at,count(a.id),"
                    "count(a.audio) from speaking_tests t left join speaking_answers a "
                    "on a.sitting_id=t.id where t.learner_id=%s group by t.id "
                    "order by t.started_at desc limit 30",
                    (learner,),
                ).fetchall()
            past = [
                {
                    "id": str(r[0]),
                    "test_id": r[1],
                    "title": self.tests[r[1]].test.title if r[1] in self.tests else r[1],
                    "keep": r[2],
                    "started_at": r[3].isoformat(),
                    "finished_at": r[4].isoformat() if r[4] else None,
                    "answers": r[5],
                    "with_audio": r[6],
                }
                for r in rows
            ]
        return {
            "can_record": can,
            "consent": CONSENT,
            "tests": [
                {
                    "id": x.test.id,
                    "title": x.test.title,
                    "draft": x.test.status == "draft",
                    "questions": len(questions(x.test)),
                }
                for x in self.tests.values()
            ],
            "past": past,
        }

    def mic_check(self, learner_id: str, audio: bytes) -> dict[str, Any]:
        """The phase 3 quality check on a few seconds of audio; nothing is stored."""
        self._owner(learner_id)
        if len(audio) > MAX_CHECK_BYTES:
            raise HTTPException(413, "Bản thử quá dài.")
        return asdict(check(audio))

    def start(self, learner_id: str, test_id: str, consent: str, keep: bool) -> dict[str, Any]:
        learner = self._owner(learner_id)
        if consent != CONSENT:
            raise HTTPException(409, "Cần đồng ý với thông báo về ghi âm trước.")
        loaded = self.tests.get(test_id)
        if loaded is None:
            raise HTTPException(404, "Không tìm thấy bài thi.")
        with self.pool().connection() as conn:
            if not conn.execute("select 1 from learners where id=%s", (learner,)).fetchone():
                raise HTTPException(404, "Không tìm thấy người học.")
            row = conn.execute(
                "insert into speaking_tests(learner_id,test_id,test_sha256,consent,keep,started_at)"
                " values (%s,%s,%s,%s,%s,%s) returning id",
                (learner, test_id, loaded.sha256, consent, keep, self.clock()),
            ).fetchone()
        assert row is not None
        return {"id": str(row[0]), "keep": keep, "test": self._content(loaded)}

    def _sitting(
        self, conn: psycopg.Connection[Any], learner: UUID, sitting: UUID
    ) -> tuple[Loaded, bool, datetime | None]:
        row = conn.execute(
            "select test_id,keep,finished_at from speaking_tests where id=%s and learner_id=%s",
            (sitting, learner),
        ).fetchone()
        if row is None or row[0] not in self.tests:
            raise HTTPException(404, "Không tìm thấy bài thi.")
        return self.tests[row[0]], bool(row[1]), row[2]

    def answer(
        self, learner_id: str, sitting_id: str, question_id: str, audio: bytes
    ) -> dict[str, Any]:
        learner = self._owner(learner_id)
        sitting = _uuid(sitting_id, "bài thi")
        if len(audio) > MAX_ANSWER_BYTES:
            raise HTTPException(413, "Bản ghi quá dài.")
        with self.pool().connection() as conn:
            loaded, keep, finished = self._sitting(conn, learner, sitting)
            if finished is not None:
                raise HTTPException(409, "Bài thi này đã kết thúc.")
            question: Question | None = next(
                (q for q in questions(loaded.test) if q.id == question_id), None
            )
            if question is None:
                raise HTTPException(404, "Không có câu hỏi này trong bài thi.")
            quality = check(
                audio,
                min_seconds=MIN_ANSWER_SECONDS,
                max_seconds=max_answer_seconds(question),
            )
            if "format" in quality.problems:
                raise HTTPException(422, "Bản ghi không đúng định dạng WAV 16 kHz mono.")
            if "too_long" in quality.problems:
                raise HTTPException(413, "Bản ghi dài hơn thời gian của câu hỏi.")
            now = self.clock()
            row = conn.execute(
                "insert into speaking_answers(sitting_id,question_id,part,question,audio,seconds,"
                "quality,recorded_at,delete_after) values (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "on conflict (sitting_id,question_id) do nothing returning id",
                (
                    sitting,
                    question.id,
                    question.part,
                    question.text,
                    audio,
                    quality.seconds,
                    Jsonb(asdict(quality)),
                    now,
                    None if keep else now + RETENTION,
                ),
            ).fetchone()
        if row is None:
            raise HTTPException(409, "Câu này đã được trả lời.")
        return {"id": str(row[0]), "seconds": quality.seconds, "problems": list(quality.problems)}

    def finish(self, learner_id: str, sitting_id: str) -> dict[str, Any]:
        learner = self._owner(learner_id)
        sitting = _uuid(sitting_id, "bài thi")
        with self.pool().connection() as conn:
            self._sitting(conn, learner, sitting)
            conn.execute(
                "update speaking_tests set finished_at=coalesce(finished_at,%s) where id=%s",
                (self.clock(), sitting),
            )
        return self.result(learner_id, sitting_id)

    def result(self, learner_id: str, sitting_id: str) -> dict[str, Any]:
        """Every question of the sitting, with its answer when there is one (no score)."""
        learner = self._owner(learner_id)
        sitting = _uuid(sitting_id, "bài thi")
        with self.pool().connection() as conn:
            purge_expired(conn, self.clock())
            loaded, keep, finished = self._sitting(conn, learner, sitting)
            started = conn.execute(
                "select started_at from speaking_tests where id=%s", (sitting,)
            ).fetchone()
            rows = conn.execute(
                "select question_id,id,question,seconds,quality,audio is not null,delete_after,"
                "transcript_status,transcript,measures,language "
                "from speaking_answers where sitting_id=%s",
                (sitting,),
            ).fetchall()
        assert started is not None
        answers = {r[0]: r for r in rows}
        content = self._content(loaded)
        items: list[dict[str, Any]] = []
        for q in questions(loaded.test):
            r = answers.get(q.id)
            items.append(
                {
                    "id": q.id,
                    "part": q.part,
                    # The question as it was asked, should the file have changed since.
                    "text": r[2] if r else q.text,
                    "answer": None
                    if r is None
                    else {
                        "id": str(r[1]),
                        "seconds": r[3],
                        "problems": list(r[4].get("problems", [])),
                        "audio": bool(r[5]),
                        "delete_after": r[6].isoformat() if r[6] else None,
                        **_transcript(
                            r[7], r[8], bool(r[5]), self.transcripts, r[9], q.seconds, r[10]
                        ),
                    },
                }
            )
        return {
            "id": sitting_id,
            "test_id": loaded.test.id,
            "title": loaded.test.title,
            "keep": keep,
            "started_at": started[0].isoformat(),
            "finished_at": finished.isoformat() if finished else None,
            "cue_card": content["cue_card"],
            "part3_theme": content["part3_theme"],
            "questions": items,
            "summary": pooled(
                [
                    i["answer"]["measures"]
                    for i in items
                    if i["answer"] and i["answer"].get("measures")
                ]
            ),
        }

    def audio(self, learner_id: str, answer_id: str) -> bytes:
        learner = self._owner(learner_id)
        answer = _uuid(answer_id, "câu trả lời")
        with self.pool().connection() as conn:
            purge_expired(conn, self.clock())
            row = conn.execute(
                "select a.audio from speaking_answers a join speaking_tests t on t.id=a.sitting_id "
                "where a.id=%s and t.learner_id=%s and a.audio is not null",
                (answer, learner),
            ).fetchone()
        if row is None:
            raise HTTPException(404, "Bản ghi này đã được xóa nên không nghe lại được.")
        return bytes(row[0])

    def delete(self, learner_id: str, sitting_id: str) -> None:
        learner = learner_uuid(learner_id)
        sitting = _uuid(sitting_id, "bài thi")
        with self.pool().connection() as conn:
            cur = conn.execute(
                "delete from speaking_tests where id=%s and learner_id=%s", (sitting, learner)
            )
        if cur.rowcount == 0:
            raise HTTPException(404, "Không tìm thấy bài thi.")
