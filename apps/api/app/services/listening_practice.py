"""Listening practice from the Reading bank (specs/listening-reading/step-4.4b.md, plan CP5).

Dictation and gap-fill items are built by code from the bank's texts (`app.listening.items`); the
server voice reads each sentence, and the sentence itself never reaches the browser before the
learner answers. Each answer moves the item's Listening competency by BKT (mastery under
`ielts-competencies`), logged in `listening_answers`. Without a server voice nothing is offered.
"""

from collections import OrderedDict
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import psycopg
from fastapi import HTTPException
from psycopg_pool import ConnectionPool

from app.competencies.model import load_map
from app.engine import bkt
from app.engine.bkt import BKTParams
from app.engine.trace import fmt_p
from app.listening.items import ListeningItem, build, grade
from app.services.backend import learner_uuid, save_trace
from app.services.competency_evidence import competency_ids
from app.services.learning import save_mastery
from app.services.reading_review import read_texts

if TYPE_CHECKING:
    from app.api.speech import SpeechClient

# Typed answers: guessing a whole sentence or a missing word is nearly impossible.
PARAMS = BKTParams(p_init=0.2, p_transit=0.1, p_slip=0.1, p_guess=0.05)
AUDIO_CACHE = 256  # sentences kept in memory (one sentence is about 100-300 kB of WAV)
NO_VOICE = "Chưa bật giọng đọc của máy chủ (hồ sơ speech), nên chưa luyện nghe được."


class ListeningPractice:
    def __init__(
        self,
        pool: Callable[[], ConnectionPool],
        texts_dir: Path,
        speech: "SpeechClient | None",
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.pool = pool
        self.texts_dir = texts_dir
        self.speech = speech
        self.clock = clock
        self.cmap = load_map()
        self._built: tuple[object, dict[str, list[ListeningItem]]] | None = None
        self._audio: OrderedDict[tuple[str, str], bytes] = OrderedDict()

    @property
    def available(self) -> bool:
        return self.speech is not None

    def items(self) -> dict[str, list[ListeningItem]]:
        """Text slug -> its items, rebuilt only when the bank changes."""
        texts = read_texts(self.texts_dir)
        key = tuple(sorted((s, t) for s, (_, t) in texts.items()))
        if self._built is None or self._built[0] != key:
            built = {slug: build(slug, text) for slug, (_, text) in texts.items()}
            self._built = (key, {s: its for s, its in built.items() if its})
        return self._built[1]

    def _item(self, item_id: str) -> ListeningItem:
        for its in self.items().values():
            for it in its:
                if it.id == item_id:
                    return it
        raise HTTPException(404, "Không tìm thấy bài nghe.")

    def _voice(self) -> None:
        if self.speech is None:
            raise HTTPException(503, NO_VOICE)

    def _learner(self, conn: psycopg.Connection[Any], learner_id: str) -> Any:
        learner = learner_uuid(learner_id)
        if not conn.execute("select 1 from learners where id=%s", (learner,)).fetchone():
            raise HTTPException(404, "Không tìm thấy người học.")
        return learner

    def texts(self, learner_id: str) -> dict[str, Any]:
        with self.pool().connection() as conn:
            self._learner(conn, learner_id)
        if not self.available:
            return {"available": False, "texts": []}
        titles = read_texts(self.texts_dir)
        return {
            "available": True,
            "texts": [
                {
                    "slug": slug,
                    "title": titles[slug][0],
                    "dictation": sum(i.kind == "dictation" for i in its),
                    "gaps": sum(i.kind == "gap" for i in its),
                }
                for slug, its in sorted(self.items().items())
            ],
        }

    def text(self, learner_id: str, slug: str) -> dict[str, Any]:
        self._voice()
        with self.pool().connection() as conn:
            self._learner(conn, learner_id)
        its = self.items().get(slug)
        if not its:
            raise HTTPException(404, "Chưa có bài nghe cho văn bản này.")
        return {
            "slug": slug,
            "title": read_texts(self.texts_dir)[slug][0],
            # What the learner may see: never the sentence or the missing word.
            "items": [{"id": i.id, "kind": i.kind, "prompt": i.prompt} for i in its],
        }

    async def audio(self, item_id: str, pace: str) -> bytes:
        self._voice()
        assert self.speech is not None
        item = self._item(item_id)
        key = (item.id, pace)
        if key in self._audio:
            self._audio.move_to_end(key)
            return self._audio[key]
        wav = await self.speech.speak(item.sentence, pace)
        self._audio[key] = wav
        while len(self._audio) > AUDIO_CACHE:
            self._audio.popitem(last=False)
        return wav

    def answer(self, learner_id: str, item_id: str, answer: str) -> dict[str, Any]:
        self._voice()
        item = self._item(item_id)
        now = self.clock()
        score, correct, marks = grade(item, answer)
        competency = item.competency
        with self.pool().connection() as conn, conn.transaction():
            learner = self._learner(conn, learner_id)
            subject, ids = competency_ids(conn, self.cmap)
            row = conn.execute(
                "select p_known from mastery where learner_id=%s and concept_id=%s",
                (learner, ids[competency]),
            ).fetchone()
            before = float(row[0]) if row else PARAMS.p_init
            after, trace = bkt.update_traced(
                before, correct, PARAMS, concept_slug=competency, now=now, item_id=item.id
            )
            name = next(c.name_vi for c in self.cmap.competencies if c.slug == competency)
            trace = trace.model_copy(
                update={
                    "rule": "listening.answer",
                    "rule_vi": (
                        f"{name}: {'đúng' if correct else 'chưa đúng'} (chấm theo câu đã đọc) → "
                        f"ước lượng từ {fmt_p(before)} thành {fmt_p(after)}."
                    ),
                }
            )
            save_mastery(conn, learner, ids[competency], after)
            save_trace(conn, learner, subject, trace)
            conn.execute(
                "insert into listening_answers(learner_id,item_id,kind,competency,answer,score,"
                "correct,p_before,p_after,answered_at) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (learner, item.id, item.kind, competency, answer, score, correct, before, after,
                 now),
            )  # fmt: skip
        return {
            "correct": correct,
            "score": round(score, 3),
            "key": item.answer,
            "sentence": item.sentence,
            "words": marks,
            "competency": competency,
            "trace": trace.model_dump(mode="json"),
        }
