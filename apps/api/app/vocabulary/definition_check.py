"""Blind check of model-written definitions (specs/vocabulary-import/step-tsl-bsl.md, step 5).

The checker, a model of another family, sees only a definition and four headwords, and names the
word the definition describes. Kept only when it names the right one. "Cannot tell" or a wrong word
drops the entry; no reply decides nothing (lessons.md: a failed call is not a judgement).
"""

import hashlib
import random
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.vocabulary.wordlist import Word

TASK = "vocab_check"
BATCH = 40
CANNOT_TELL = "?"
Verdict = Literal["right", "wrong", "cannot_tell", "no_reply"]

SYSTEM = """You check dictionary definitions. For each numbered item you get one definition in easy
English and four English words. Answer with the ONE word the definition describes, copied exactly
from the four, or "?" when the definition fits none of them or more than one equally well.
Use only the definition and the four words; do not guess from the item's number or order."""


class Question(BaseModel):
    id: int
    lemma: str  # the right answer: never sent to the checker
    definition: str
    options: tuple[str, str, str, str]


class Answer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    word: str = Field(max_length=60)


class Reply(BaseModel):
    answers: list[Answer]


def _rng(lemma: str) -> random.Random:
    """A seed from the word itself: a rerun asks the same question (and hits the cache)."""
    return random.Random(int(hashlib.sha256(lemma.encode()).hexdigest()[:12], 16))


def question(n: int, word: Word, pool: Sequence[Word]) -> Question:
    """Three other words of the same part of speech (any part of speech if too few), shuffled."""
    same = sorted({w.lemma for w in pool if w.pos == word.pos and w.lemma != word.lemma})
    if len(same) < 3:
        same = sorted({w.lemma for w in pool if w.lemma != word.lemma})
    if len(same) < 3:
        raise ValueError("need three other words for a blind check")
    rng = _rng(word.lemma)
    options = [*rng.sample(same, 3), word.lemma]
    rng.shuffle(options)
    return Question(
        id=n, lemma=word.lemma, definition=word.definition, options=(options[0], options[1],
        options[2], options[3]),
    )  # fmt: skip


def prompt(batch: Sequence[Question]) -> str:
    lines = []
    for q in batch:
        lines.append(f"{q.id}. Definition: {q.definition}")
        lines.append(f"   Words: {', '.join(q.options)}")
    return "\n".join(lines)


def verdict(q: Question, answer: str | None) -> Verdict:
    if answer is None:
        return "no_reply"
    picked = answer.strip().strip(".\"'").lower()
    if picked == CANNOT_TELL or picked not in q.options:
        return "cannot_tell"  # "?" or a word that is not one of the four
    return "right" if picked == q.lemma else "wrong"


def verdicts(batch: Sequence[Question], reply: Reply | None) -> dict[str, Verdict]:
    """lemma -> verdict for one batch; a missing answer in a reply is "no_reply"."""
    by_id = {a.id: a.word for a in reply.answers} if reply else {}
    return {q.lemma: verdict(q, by_id.get(q.id)) for q in batch}


@dataclass
class CheckCounts:
    right: int = 0
    wrong: int = 0
    cannot_tell: int = 0
    no_reply: int = 0

    def add(self, v: Verdict) -> None:
        setattr(self, v, getattr(self, v) + 1)
