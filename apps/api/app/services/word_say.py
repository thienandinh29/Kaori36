"""Say a vocabulary word and see each sound's raw score (specs/pronunciation/step-3.7.md).

The voice policy holds (SPEC.md): owners only until a privacy review, with the same consent as
recordings (`voice-v1`), and the audio is analysed in memory and never stored. The pronunciation
service must be on. No mastery moves: thresholds wait for the gate.

Step 3.7b: each analysed attempt's per-sound scores (never audio) are kept in `say_attempts`, so a
sound that stays low across attempts gets a guide (how to say it, what to change, a minimal pair),
and the learner sees the sounds they most often miss across all words.
"""

import asyncio
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml  # type: ignore[import-untyped]
from fastapi import HTTPException
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from app.pronunciation import quality
from app.pronunciation.word import (
    WINDOW,
    focus,
    model_phones,
    per_phone,
    phones_from_ipa,
    repeated,
)
from app.services.backend import learner_uuid
from app.services.recordings import CONSENT
from app.vocabulary.wordlist import shared_wordlist

Score = Callable[[bytes, list[str]], dict[str, Any]]
WORD_MIN_SECONDS = 0.3  # of the trimmed recording: a short word said quickly is still a word
WORD_MIN_SPEECH = 0.15
WORD_PAD_SECONDS = 1.0  # what the aligner receives at least (silence added at both ends)
FOCUS_DAYS = 30


@lru_cache(maxsize=4)
def load_tips(path: Path) -> dict[str, Any]:
    """phone-tips.yaml: how to say each sound, what to change per confusion (draft)."""
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data


class WordSay:
    def __init__(
        self,
        vocab: Path,
        vocab_imported: Path | None,
        draft_learners: str,
        score: Score | None,
        pool: Callable[[], ConnectionPool] | None = None,
        tips: Path | None = None,
    ) -> None:
        self.vocab = vocab
        self.vocab_imported = vocab_imported
        self.owners = {learner_uuid(x.strip()) for x in draft_learners.split(",") if x.strip()}
        self.score = score
        self.pool = pool
        self.tips = tips

    def _tips(self) -> dict[str, Any]:
        return load_tips(self.tips) if self.tips else {"phones": {}, "pairs": {}, "dropped": ""}

    def _guide(self, g: dict[str, Any]) -> dict[str, Any]:
        tips = self._tips()
        pair = tips["pairs"].get(f"{g['phone']}>{g['heard']}") if g["heard"] else None
        return g | {
            "how": tips["phones"].get(g["phone"], {}).get("how"),
            "change": tips["dropped"] if g["dropped"] else (pair or {}).get("tip"),
            "minimal": (pair or {}).get("minimal"),
        }

    def focus(self, learner_id: str) -> dict[str, Any]:
        """The sounds this learner most often misses across words, last FOCUS_DAYS days."""
        if self.pool is None:
            return {"sounds": []}
        with self.pool().connection() as conn:
            rows = conn.execute(
                "select phones from say_attempts where learner_id=%s "
                "and said_at > now() - make_interval(days => %s) order by said_at desc",
                (learner_uuid(learner_id), FOCUS_DAYS),
            ).fetchall()
        tips = self._tips()["phones"]
        return {
            "days": FOCUS_DAYS,
            "attempts": len(rows),
            "sounds": [
                r
                | {
                    "how": tips.get(r["phone"], {}).get("how"),
                    "example": tips.get(r["phone"], {}).get("example"),
                }
                for r in focus([row[0] for row in rows])
            ],
        }

    def status(self, learner_id: str) -> dict[str, Any]:
        owner = learner_uuid(learner_id) in self.owners
        return {"analysis": owner and self.score is not None, "owner": owner, "consent": CONSENT}

    async def say(
        self, learner_id: str, word: str, consent: str, audio: bytes, take: UUID | None = None
    ) -> dict[str, Any]:
        if learner_uuid(learner_id) not in self.owners:
            raise HTTPException(403, "Phân tích giọng nói hiện chỉ mở cho chủ dự án.")
        if consent != CONSENT:
            raise HTTPException(422, "Cần đồng ý với cách xử lý giọng nói trước.")
        if self.score is None:
            raise HTTPException(503, "Chưa bật dịch vụ phân tích phát âm (PRONUNCIATION_URL).")
        entry = next(
            (w for w in shared_wordlist(self.vocab, self.vocab_imported).words if w.key == word),
            None,
        )
        if entry is None:
            raise HTTPException(404, "Không tìm thấy từ này.")
        if not entry.ipa:
            return {"ok": False, "problems": ["no_ipa"], "phones": []}
        # Silence before and after the word is cut first (step 3.7c): loudness and length are
        # judged on the speech, not on how long the learner waited before or after it.
        audio = quality.trim(audio)
        q = quality.check(audio, WORD_MIN_SECONDS, WORD_MIN_SPEECH)
        if not q.ok:
            return {"ok": False, "problems": list(q.problems), "phones": []}
        audio = quality.pad(audio, WORD_PAD_SECONDS)
        phones = phones_from_ipa(entry.ipa)
        try:
            scored = await asyncio.to_thread(self.score, audio, model_phones(phones))
        except Exception:  # the service refused (an unknown phone, no alignment) or is down
            return {"ok": False, "problems": ["not_analysed"], "phones": []}
        result = per_phone(phones, scored)
        tips = self._tips()["phones"]
        for p in result:
            p["how"] = tips.get(p["phone"], {}).get("how")
        # The audio is dropped here; only the per-sound scores are kept (step 3.7b).
        guide: list[dict[str, Any]] = []
        if self.pool is not None:
            scores = [
                {k: p[k] for k in ("phone", "gop", "closeness", "heard", "dropped")} for p in result
            ]
            with self.pool().connection() as conn:
                # One attempt per recording: analysing the same take again replaces it.
                conn.execute(
                    "insert into say_attempts(learner_id, word, phones, take_id) "
                    "values (%s,%s,%s,%s) on conflict (learner_id, word, take_id) "
                    "where take_id is not null do update set phones=excluded.phones",
                    (learner_uuid(learner_id), word, Jsonb(scores), take),
                )
                recent = conn.execute(
                    "select phones from say_attempts where learner_id=%s and word=%s "
                    "order by said_at desc, id desc limit %s",
                    (learner_uuid(learner_id), word, WINDOW),
                ).fetchall()
            guide = [self._guide(g) for g in repeated([r[0] for r in recent])]
        return {
            "ok": True,
            "problems": [],
            "ipa": entry.ipa,
            "phones": result,
            "heard": list(scored.get("recognised", [])),
            "guide": guide,
        }
