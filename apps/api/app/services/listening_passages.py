"""Listening to a Reading passage, then answering its approved questions (step 4.4c, plan CP5b).

The questions are the ones Reading serves (approved, Silver or Gold, passage unchanged, checks
passing), so their keys are already checked twice; headings are left out (they need the paragraphs
on screen). The passage is never sent before the learner submits: the browser gets only how many
parts there are and plays each part's audio, voiced by the server and cached. One BKT observation
per answered question on a Listening competency (detail, else main idea), logged in
`listening_answers` with kind 'passage'; a blank gives no evidence.
"""

import json
from collections import OrderedDict
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException

from app.engine import bkt
from app.engine.trace import fmt_p
from app.listening.passages import LISTENED_KINDS, competency, parts
from app.reading.items import grade, learner_view, presented, to_stored
from app.services.backend import save_trace
from app.services.competency_evidence import competency_ids
from app.services.learning import save_mastery
from app.services.reading_practice import PARAMS, ReadingPractice, key_text, load_texts

if TYPE_CHECKING:
    from app.api.speech import SpeechClient

AUDIO_CACHE = 128  # parts kept in memory: about 40 MB (a part averaged 0.32 MB, 20 Nov)
NO_VOICE = "Chưa bật giọng đọc của máy chủ (hồ sơ speech), nên chưa luyện nghe được."


class ListeningPassages:
    def __init__(
        self,
        reading: ReadingPractice,
        speech: "SpeechClient | None",
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.reading = reading
        self.speech = speech
        self.clock = clock
        self._audio: OrderedDict[tuple[str, int, str], bytes] = OrderedDict()

    def _voice(self) -> None:
        if self.speech is None:
            raise HTTPException(503, NO_VOICE)

    def _served(self, conn: Any, slug: str | None = None) -> dict[str, list[tuple[str, Any]]]:
        out = {
            s: [(i, it) for i, it in items if it.kind in LISTENED_KINDS]
            for s, items in self.reading.served(conn).items()
            if slug is None or s == slug
        }
        return {s: items for s, items in out.items() if items}

    def texts(self, learner_id: str) -> dict[str, Any]:
        if self.speech is None:
            with self.reading.pool().connection() as conn:
                self.reading._learner(conn, learner_id)
            return {"available": False, "texts": []}
        titles = load_texts(self.reading.texts_dir)
        with self.reading.pool().connection() as conn:
            learner = self.reading._learner(conn, learner_id)
            served = self._served(conn)
            read = {
                r[0]
                for r in conn.execute(
                    "select distinct i.text_slug from reading_answers a join reading_items i "
                    "on i.id = a.item_id where a.learner_id=%s",
                    (learner,),
                ).fetchall()
            }
        return {
            "available": True,
            "texts": [
                {
                    "slug": slug,
                    "title": titles[slug][0],
                    "questions": len(items),
                    "parts": len(parts(titles[slug][1])),
                    "read_before": slug in read,  # it may be easier: the learner read it
                }
                for slug, items in sorted(served.items())
            ],
        }

    def text(self, learner_id: str, slug: str) -> dict[str, Any]:
        """The questions and how many audio parts: never the passage before submitting."""
        self._voice()
        titles = load_texts(self.reading.texts_dir)
        with self.reading.pool().connection() as conn:
            self.reading._learner(conn, learner_id)
            items = self._served(conn, slug).get(slug)
        if not items:
            raise HTTPException(404, "Chưa có câu hỏi nghe cho bài này.")
        return {
            "slug": slug,
            "title": titles[slug][0],
            "parts": len(parts(titles[slug][1])),
            "items": [{"id": i, **learner_view(presented(it))} for i, it in items],
        }

    async def audio(self, slug: str, n: int, pace: str) -> bytes:
        self._voice()
        assert self.speech is not None
        text = load_texts(self.reading.texts_dir).get(slug)
        if text is None:
            raise HTTPException(404, "Không tìm thấy bài nghe.")
        spoken = parts(text[1])
        if not 0 <= n < len(spoken):
            raise HTTPException(404, "Không có đoạn âm thanh này.")
        key = (slug, n, pace)
        if key in self._audio:
            self._audio.move_to_end(key)
            return self._audio[key]
        wav = await self.speech.speak(spoken[n], pace)
        self._audio[key] = wav
        while len(self._audio) > AUDIO_CACHE:
            self._audio.popitem(last=False)
        return wav

    def submit(self, learner_id: str, slug: str, answers: dict[str, Any]) -> dict[str, Any]:
        """Grade every question; answered ones move a Listening competency. Then the transcript."""
        self._voice()
        now = self.clock()
        titles = load_texts(self.reading.texts_dir)
        with self.reading.pool().connection() as conn, conn.transaction():
            learner = self.reading._learner(conn, learner_id)
            items = self._served(conn, slug).get(slug)
            if not items:
                raise HTTPException(404, "Chưa có câu hỏi nghe cho bài này.")
            unknown = sorted(set(answers) - {i for i, _ in items})
            if unknown:
                raise HTTPException(422, "Có câu trả lời không thuộc bài nghe này.")
            subject, ids = competency_ids(conn, self.reading.cmap)
            names = {c.slug: c.name_vi for c in self.reading.cmap.competencies}
            out = []
            for item_id, item in items:
                given = answers.get(item_id)
                base = {"id": item_id, "key": key_text(item), "evidence": list(item.evidence)}
                if given is None or given == "" or given == {}:
                    out.append(base | {"answer": None, "correct": False})
                    continue
                kept = to_stored(item, given)
                score = grade(item, kept)
                correct = score >= 1.0
                slug_c = competency(item.skill)
                row = conn.execute(
                    "select p_known from mastery where learner_id=%s and concept_id=%s",
                    (learner, ids[slug_c]),
                ).fetchone()
                before = float(row[0]) if row else PARAMS.p_init
                after, trace = bkt.update_traced(
                    before, correct, PARAMS, concept_slug=slug_c, now=now, item_id=item_id
                )
                trace = trace.model_copy(
                    update={
                        "rule": "listening.passage",
                        "rule_vi": (
                            f"{names[slug_c]}: nghe cả bài rồi trả lời "
                            f"{'đúng' if correct else 'sai'} → ước lượng từ {fmt_p(before)} "
                            f"thành {fmt_p(after)}."
                        ),
                    }
                )
                save_mastery(conn, learner, ids[slug_c], after)
                save_trace(conn, learner, subject, trace)
                conn.execute(
                    "insert into listening_answers(learner_id,item_id,kind,competency,answer,"
                    "score,correct,p_before,p_after,answered_at) "
                    "values (%s,%s,'passage',%s,%s,%s,%s,%s,%s,%s)",
                    (learner, item_id, slug_c, json.dumps(kept), score, correct, before, after,
                     now),
                )  # fmt: skip
                out.append(base | {"answer": given, "correct": correct, "competency": slug_c})
        return {
            "slug": slug,
            "correct": sum(x["correct"] for x in out),
            "total": len(out),
            "answered": sum(x["answer"] is not None for x in out),
            "items": out,
            "transcript": titles[slug][1],  # only now: after the learner has answered
        }
