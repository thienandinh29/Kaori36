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
from app.speaking.feedback import CONSENT as FEEDBACK_CONSENT
from app.speaking.feedback import MAX_TRIES as FEEDBACK_TRIES
from app.speaking.measures import pooled
from app.speaking.tests import (
    CLOSING_SECONDS,
    GRACE_SECONDS,
    LONG_TURN_SECONDS,
    MAX_TRIES,
    PART1_SECONDS,
    PART3_SECONDS,
    PREPARE_SECONDS,
    Loaded,
    Question,
    load_tests,
    max_answer_seconds,
    questions,
    try_seconds,
)
from app.testers import store as testers
from app.testers.limits import DailyLimits, used_today

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
        testers_may_record: bool = False,
        limits: DailyLimits | None = None,
    ) -> None:
        self.pool = pool
        # Invited testers (step 5.5): they record only while the owner's switch is on (set after the
        # privacy review), and only with their own session; the limits apply to them, not the owner.
        self.testers_may_record = testers_may_record
        self.limits = limits
        self.transcripts = transcripts  # a recogniser is configured (ASR_URL, step 5.1)
        self.tests: dict[str, Loaded] = load_tests(folder)
        self.owners = {learner_uuid(x.strip()) for x in draft_learners.split(",") if x.strip()}
        self.clock = clock

    def _allowed(self, learner: UUID, session: str | None) -> bool:
        """The owner; or a tester with a valid session of their own while the switch is on."""
        if learner in self.owners:
            return True
        if not self.testers_may_record:
            return False
        with self.pool().connection() as conn:
            return (
                testers.is_tester(conn, learner)
                and testers.session_learner(conn, session, self.clock()) == learner
            )

    def _owner(self, learner_id: str, session: str | None = None) -> UUID:
        learner = learner_uuid(learner_id)
        if not self._allowed(learner, session):
            raise HTTPException(
                403,
                "Ghi âm hiện chỉ mở cho chủ dự án, cho đến khi việc lưu giữ giọng nói được xem xét "
                "về quyền riêng tư.",
            )
        return learner

    def _check_limit(self, learner: UUID, guided: bool) -> None:
        """A tester's daily limit on starting a mock test or a practice try (Vietnam day)."""
        if learner in self.owners or self.limits is None:
            return
        with self.pool().connection() as conn:
            mocks, tries = used_today(conn, learner, self.clock())
        if guided and tries >= self.limits.practice_tries_per_day:
            raise HTTPException(
                429,
                f"Hôm nay bạn đã luyện đủ {self.limits.practice_tries_per_day} lần. "
                "Mai quay lại nhé.",
            )
        if not guided and mocks >= self.limits.mock_tests_per_day:
            raise HTTPException(
                429,
                f"Hôm nay bạn đã thi thử đủ {self.limits.mock_tests_per_day} bài. "
                "Mai quay lại nhé.",
            )

    def _left(self, learner: UUID) -> dict[str, int] | None:
        """What a tester has left today; None for the owner or when there are no limits."""
        if learner in self.owners or self.limits is None:
            return None
        with self.pool().connection() as conn:
            mocks, tries = used_today(conn, learner, self.clock())
        return {
            "mock_tests": max(0, self.limits.mock_tests_per_day - mocks),
            "practice_tries": max(0, self.limits.practice_tries_per_day - tries),
        }

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

    def overview(self, learner_id: str, session: str | None = None) -> dict[str, Any]:
        """The tests on offer and the learner's past sittings."""
        learner = learner_uuid(learner_id)
        can = self._allowed(learner, session)
        past: list[dict[str, Any]] = []
        practices: list[dict[str, Any]] = []
        if can:
            with self.pool().connection() as conn:
                purge_expired(conn, self.clock())
                rows = conn.execute(
                    "select t.id,t.test_id,t.keep,t.started_at,t.finished_at,count(a.id),"
                    "count(a.audio) from speaking_tests t left join speaking_answers a "
                    "on a.sitting_id=t.id where t.learner_id=%s and t.mode='exam' group by t.id "
                    "order by t.started_at desc limit 30",
                    (learner,),
                ).fetchall()
                practised = conn.execute(
                    "select t.id,t.test_id,t.question_id,t.started_at,"
                    "(select count(*) from speaking_tests c where c.practice_of=t.id)+1 "
                    "from speaking_tests t where t.learner_id=%s and t.mode='guided' "
                    "and t.practice_of is null order by t.started_at desc limit 30",
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
            for r in practised:
                test = self.tests.get(r[1])
                q = next((q for q in questions(test.test) if q.id == r[2]), None) if test else None
                if test is not None and q is not None:
                    practices.append(
                        {
                            "id": str(r[0]),
                            "title": test.test.title,
                            "question": q.text,
                            "started_at": r[3].isoformat(),
                            "tries": int(r[4]),
                        }
                    )
        return {
            "can_record": can,
            "consent": CONSENT,
            "tests": [
                {
                    "id": x.test.id,
                    "title": x.test.title,
                    "draft": x.test.status == "draft",
                    "questions": len(questions(x.test)),
                    "practice": [
                        {"id": q.id, "part": q.part, "text": q.text, "seconds": q.seconds}
                        for q in questions(x.test)
                    ],
                }
                for x in self.tests.values()
            ],
            "past": past,
            "practices": practices,
            "max_tries": MAX_TRIES,
            "left_today": self._left(learner) if can else None,
        }

    def mic_check(
        self, learner_id: str, audio: bytes, session: str | None = None
    ) -> dict[str, Any]:
        """The phase 3 quality check on a few seconds of audio; nothing is stored."""
        self._owner(learner_id, session)
        if len(audio) > MAX_CHECK_BYTES:
            raise HTTPException(413, "Bản thử quá dài.")
        return asdict(check(audio))

    def start(
        self,
        learner_id: str,
        test_id: str,
        consent: str,
        keep: bool,
        session: str | None = None,
    ) -> dict[str, Any]:
        learner = self._owner(learner_id, session)
        self._check_limit(learner, guided=False)
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
        self,
        learner_id: str,
        sitting_id: str,
        question_id: str,
        audio: bytes,
        session: str | None = None,
    ) -> dict[str, Any]:
        learner = self._owner(learner_id, session)
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
            guided = conn.execute(
                "select question_id,asked_seconds from speaking_tests "
                "where id=%s and mode='guided'",
                (sitting,),
            ).fetchone()
            limit = max_answer_seconds(question)
            if guided is not None:
                if guided[0] != question.id:
                    raise HTTPException(422, "Lần luyện này chỉ có một câu hỏi.")
                limit = int(guided[1]) + GRACE_SECONDS
            quality = check(audio, min_seconds=MIN_ANSWER_SECONDS, max_seconds=limit)
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

    def finish(
        self, learner_id: str, sitting_id: str, session: str | None = None
    ) -> dict[str, Any]:
        learner = self._owner(learner_id, session)
        sitting = _uuid(sitting_id, "bài thi")
        with self.pool().connection() as conn:
            self._sitting(conn, learner, sitting)
            conn.execute(
                "update speaking_tests set finished_at=coalesce(finished_at,%s) where id=%s",
                (self.clock(), sitting),
            )
        return self.result(learner_id, sitting_id, session)

    def _item(self, r: Any, asked: int) -> dict[str, Any]:
        """One stored answer as the pages see it (`r` is a row of the answers query)."""
        return {
            "id": str(r[1]),
            "seconds": r[3],
            "problems": list(r[4].get("problems", [])),
            "audio": bool(r[5]),
            "delete_after": r[6].isoformat() if r[6] else None,
            **_transcript(r[7], r[8], bool(r[5]), self.transcripts, r[9], asked, r[10]),
        }

    def start_practice(
        self,
        learner_id: str,
        test_id: str,
        question_id: str,
        consent: str,
        keep: bool,
        previous_id: str | None,
        session: str | None = None,
    ) -> dict[str, Any]:
        """Start a try of one question: the first, or a repeat of `previous_id`'s question with
        less time. A fourth try, a repeat of a try nobody answered, or another question: refused."""
        learner = self._owner(learner_id, session)
        self._check_limit(learner, guided=True)
        if consent != CONSENT:
            raise HTTPException(409, "Cần đồng ý với thông báo về ghi âm trước.")
        loaded = self.tests.get(test_id)
        question = (
            next((q for q in questions(loaded.test) if q.id == question_id), None)
            if loaded
            else None
        )
        if loaded is None or question is None:
            raise HTTPException(404, "Không tìm thấy câu hỏi.")
        root: UUID | None = None
        try_no = 1
        with self.pool().connection() as conn:
            if previous_id is not None:
                prev = _uuid(previous_id, "lần luyện")
                row = conn.execute(
                    "select coalesce(practice_of,id),test_id,question_id,keep from speaking_tests "
                    "where id=%s and learner_id=%s and mode='guided'",
                    (prev, learner),
                ).fetchone()
                if row is None:
                    raise HTTPException(404, "Không tìm thấy lần luyện trước.")
                root = row[0]
                if (row[1], row[2]) != (test_id, question_id):
                    raise HTTPException(422, "Chỉ nói lại đúng câu hỏi đó.")
                keep = bool(row[3])  # the repeats follow the first try's choice
                tries = conn.execute(
                    "select count(*), count(a.id) from speaking_tests t "
                    "left join speaking_answers a on a.sitting_id=t.id "
                    "where t.id=%s or t.practice_of=%s",
                    (root, root),
                ).fetchone()
                assert tries is not None
                if tries[0] >= MAX_TRIES:
                    raise HTTPException(409, f"Mỗi câu hỏi luyện tối đa {MAX_TRIES} lần.")
                if tries[1] < tries[0]:
                    raise HTTPException(409, "Hãy trả lời lần trước đã.")
                try_no = int(tries[0]) + 1
            asked = try_seconds(question, try_no)
            if not conn.execute("select 1 from learners where id=%s", (learner,)).fetchone():
                raise HTTPException(404, "Không tìm thấy người học.")
            made = conn.execute(
                "insert into speaking_tests(learner_id,test_id,test_sha256,consent,keep,started_at,"
                "mode,question_id,try_no,practice_of,asked_seconds) "
                "values (%s,%s,%s,%s,%s,%s,'guided',%s,%s,%s,%s) returning id",
                (learner, test_id, loaded.sha256, consent, keep, self.clock(),
                 question_id, try_no, root, asked),
            ).fetchone()  # fmt: skip
        assert made is not None
        return {"id": str(made[0]), "keep": keep, "try_no": try_no, "asked_seconds": asked}

    def practice(
        self, learner_id: str, sitting_id: str, session: str | None = None
    ) -> dict[str, Any]:
        """A question's tries, in order, each with its answer's transcript, numbers and checks, and
        the time the next try would have. Only the first try counts as evidence of fluency."""
        learner = self._owner(learner_id, session)
        sitting = _uuid(sitting_id, "lần luyện")
        with self.pool().connection() as conn:
            purge_expired(conn, self.clock())
            head = conn.execute(
                "select coalesce(practice_of,id),test_id,question_id,keep from speaking_tests "
                "where id=%s and learner_id=%s and mode='guided'",
                (sitting, learner),
            ).fetchone()
            if head is None or head[1] not in self.tests:
                raise HTTPException(404, "Không tìm thấy lần luyện.")
            root, test_id, question_id, keep = head
            tries = conn.execute(
                "select t.id,t.try_no,t.asked_seconds,t.finished_at from speaking_tests t "
                "where t.id=%s or t.practice_of=%s order by t.try_no",
                (root, root),
            ).fetchall()
            rows = {
                r[0]: r
                for r in conn.execute(
                    "select sitting_id,id,question,seconds,quality,audio is not null,delete_after,"
                    "transcript_status,transcript,measures,language from speaking_answers "
                    "where sitting_id = any(%s)",
                    ([t[0] for t in tries],),
                ).fetchall()
            }
        loaded = self.tests[test_id]
        question = next(q for q in questions(loaded.test) if q.id == question_id)
        out = []
        for t in tries:
            r = rows.get(t[0])
            out.append(
                {
                    "id": str(t[0]),
                    "try_no": t[1],
                    "asked_seconds": t[2],
                    "finished": t[3] is not None,
                    "counts_as_evidence": t[1] == 1,
                    "answer": None if r is None else self._item(r, t[2]),
                }
            )
        answered = sum(1 for x in out if x["answer"] is not None)
        self._attach_feedback(learner, [x["answer"] for x in out if x["answer"] is not None])
        content = self._content(loaded)
        part = question.part
        words = {2: loaded.test.part2.words, 3: loaded.test.part3.words}.get(part, ())
        return {
            "id": str(root),
            "keep": bool(keep),
            "test_id": test_id,
            "title": loaded.test.title,
            "question": {"id": question.id, "part": part, "text": question.text},
            "cue_card": content["cue_card"] if part == 2 else None,
            "theme": loaded.test.part3.theme if part == 3 else None,
            "words": list(words),
            "tries": out,
            "max_tries": MAX_TRIES,
            "next_seconds": try_seconds(question, len(out) + 1)
            if len(out) < MAX_TRIES and answered == len(out)
            else None,
        }

    def result(
        self, learner_id: str, sitting_id: str, session: str | None = None
    ) -> dict[str, Any]:
        """Every question of the sitting, with its answer when there is one (no score)."""
        learner = self._owner(learner_id, session)
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
                    "answer": None if r is None else self._item(r, q.seconds),
                }
            )
        self._attach_feedback(learner, [i["answer"] for i in items if i["answer"]])
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

    def _attach_feedback(self, learner: UUID, answers: list[dict[str, Any]]) -> None:
        """Each answer's AI feedback state (step 5.3b): `status` none, queued, working, done or
        failed, the checked points, and whether the learner may ask now (the owner, a transcript
        with 15 s of speech, fewer than MAX_TRIES asks)."""
        if not answers:
            return
        with self.pool().connection() as conn:
            rows = {
                str(r[0]): r
                for r in conn.execute(
                    "select id,feedback_status,feedback,feedback_tries from speaking_answers "
                    "where id = any(%s)",
                    ([UUID(a["id"]) for a in answers],),
                ).fetchall()
            }
        for a in answers:
            r = rows.get(a["id"])
            status, data, tries = (r[1], r[2], r[3]) if r else (None, None, 0)
            measures = a.get("measures") or {}
            spoke = a.get("transcript") == "done" and not measures.get("short", True)
            data = data or {}
            a["feedback"] = {
                "status": status or "none",
                "points": data.get("points", []),
                "failed": data.get("failed"),
                "can_ask": (
                    learner in self.owners
                    and spoke
                    and status in (None, "failed")
                    and tries < FEEDBACK_TRIES
                ),
                "consent": FEEDBACK_CONSENT,
            }

    def feedback_state(
        self, learner_id: str, answer_id: str, session: str | None = None
    ) -> dict[str, Any]:
        """One answer's AI feedback state, for the page that waits for it (step 5.3b)."""
        learner = learner_uuid(learner_id)
        answer = _uuid(answer_id, "câu trả lời")
        with self.pool().connection() as conn:
            row = conn.execute(
                "select a.transcript_status,a.measures from speaking_answers a "
                "join speaking_tests t on t.id=a.sitting_id where a.id=%s and t.learner_id=%s",
                (answer, learner),
            ).fetchone()
        if row is None:
            raise HTTPException(404, "Không tìm thấy câu trả lời.")
        item = {"id": str(answer), "transcript": row[0], "measures": row[1]}
        self._attach_feedback(learner, [item])
        state: dict[str, Any] = item["feedback"]
        return state

    def request_feedback(
        self, learner_id: str, answer_id: str, consent: str, session: str | None = None
    ) -> dict[str, Any]:
        """Queue the model's feedback on one answer's transcript (step 5.3b). Owner only for now;
        the transcript is sent to a model provider only after this request, with the notice's
        version."""
        learner = learner_uuid(learner_id)
        if learner not in self.owners:
            raise HTTPException(403, "Nhận xét bằng AI hiện chỉ mở cho chủ dự án.")
        if consent != FEEDBACK_CONSENT:
            raise HTTPException(422, "Hãy đọc và đồng ý thông báo trước khi gửi.")
        answer = _uuid(answer_id, "câu trả lời")
        with self.pool().connection() as conn:
            row = conn.execute(
                "select a.transcript_status,a.measures,a.feedback_status,a.feedback_tries "
                "from speaking_answers a join speaking_tests t on t.id=a.sitting_id "
                "where a.id=%s and t.learner_id=%s",
                (answer, learner),
            ).fetchone()
            if row is None:
                raise HTTPException(404, "Không tìm thấy câu trả lời.")
            transcript, measures, status, tries = row
            if transcript != "done" or measures is None:
                raise HTTPException(409, "Câu trả lời này chưa có bản chép lời.")
            if measures.get("short", True):
                raise HTTPException(409, "Câu trả lời dưới 15 giây nên chưa có nhận xét bằng AI.")
            if status in ("queued", "working", "done"):
                return {"status": status}
            if tries >= FEEDBACK_TRIES:
                raise HTTPException(409, "Đã thử nhiều lần, bạn quay lại sau nhé.")
            conn.execute(
                "update speaking_answers set feedback_status='queued', feedback=null, "
                "feedback_consent=%s, feedback_requested_at=%s, feedback_tries=feedback_tries+1 "
                "where id=%s",
                (consent, self.clock(), answer),
            )
        return {"status": "queued"}

    def audio(self, learner_id: str, answer_id: str, session: str | None = None) -> bytes:
        learner = self._owner(learner_id, session)
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

    def delete(self, learner_id: str, sitting_id: str, session: str | None = None) -> None:
        """Deleting one's own sitting works even when recording is shut, but a tester's learner id
        is not enough: it needs that tester's own session."""
        learner = learner_uuid(learner_id)
        if learner not in self.owners:
            with self.pool().connection() as conn:
                bound = (
                    not testers.is_tester(conn, learner)
                    or testers.session_learner(conn, session, self.clock()) == learner
                )
            if not bound:
                raise HTTPException(403, "Hãy mở lại liên kết mời để xóa.")
        sitting = _uuid(sitting_id, "bài thi")
        with self.pool().connection() as conn:
            cur = conn.execute(
                "delete from speaking_tests where id=%s and learner_id=%s", (sitting, learner)
            )
        if cur.rowcount == 0:
            raise HTTPException(404, "Không tìm thấy bài thi.")
