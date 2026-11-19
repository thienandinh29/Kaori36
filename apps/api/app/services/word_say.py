"""Say a vocabulary word and see each sound's raw score (specs/pronunciation/step-3.7.md).

The voice policy holds (SPEC.md): owners only until a privacy review, with the same consent as
recordings (`voice-v1`), and the audio is analysed in memory and never stored. The pronunciation
service must be on. No mastery moves: thresholds wait for the gate.
"""

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app.pronunciation import quality
from app.pronunciation.word import per_phone, phones_from_ipa
from app.services.backend import learner_uuid
from app.services.recordings import CONSENT
from app.vocabulary.wordlist import shared_wordlist

Score = Callable[[bytes, list[str]], dict[str, Any]]
WORD_MIN_SECONDS = 0.6
WORD_MIN_SPEECH = 0.15


class WordSay:
    def __init__(
        self,
        vocab: Path,
        vocab_imported: Path | None,
        draft_learners: str,
        score: Score | None,
    ) -> None:
        self.vocab = vocab
        self.vocab_imported = vocab_imported
        self.owners = {learner_uuid(x.strip()) for x in draft_learners.split(",") if x.strip()}
        self.score = score

    def status(self, learner_id: str) -> dict[str, Any]:
        owner = learner_uuid(learner_id) in self.owners
        return {"analysis": owner and self.score is not None, "owner": owner, "consent": CONSENT}

    async def say(self, learner_id: str, word: str, consent: str, audio: bytes) -> dict[str, Any]:
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
        q = quality.check(audio, WORD_MIN_SECONDS, WORD_MIN_SPEECH)
        if not q.ok:
            return {"ok": False, "problems": list(q.problems), "phones": []}
        phones = phones_from_ipa(entry.ipa)
        try:
            scored = await asyncio.to_thread(self.score, audio, phones)
        except Exception:  # the service refused (an unknown phone, no alignment) or is down
            return {"ok": False, "problems": ["not_analysed"], "phones": []}
        # The audio is dropped here: nothing about this recording is stored.
        return {
            "ok": True,
            "problems": [],
            "ipa": entry.ipa,
            "phones": per_phone(phones, scored),
            "heard": list(scored.get("recognised", [])),
        }
