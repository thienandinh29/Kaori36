"""Measured features of a reading text (specs/listening-reading/step-4.1.md). Pure functions.

No CEFR claim is made here: the owner labels some texts later to see how well the numbers track
a level.
"""

from collections.abc import Collection
from dataclasses import asdict, dataclass
from typing import Any

from app.writing.analysis import sentences, words

LONG_WORD_LETTERS = 7
TTR_WINDOW = 100  # a fixed window, so a longer text does not look less varied


@dataclass(frozen=True)
class TextFeatures:
    words: int
    sentences: int
    mean_sentence_words: float
    long_word_share: float
    type_token_ratio: float  # over the first TTR_WINDOW words
    unknown_share: float | None  # share of words outside the known set, or None without a set

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def _letters(word: str) -> int:
    return sum(c.isalpha() for c in word)


def _normal(word: str) -> str:
    return word.lower().replace("\u2019", "'").strip("'-")


def features(text: str, known: Collection[str] | None = None) -> TextFeatures:
    ws = [_normal(w) for w in words(text)]
    n = len(ws)
    sents = sentences(text)
    window = ws[:TTR_WINDOW]
    unknown = None
    if known is not None and n:
        unknown = round(sum(1 for w in ws if w not in known) / n, 3)
    return TextFeatures(
        words=n,
        sentences=len(sents),
        mean_sentence_words=round(n / len(sents), 2) if sents else 0.0,
        long_word_share=round(sum(1 for w in ws if _letters(w) >= LONG_WORD_LETTERS) / n, 3)
        if n
        else 0.0,
        type_token_ratio=round(len(set(window)) / len(window), 3) if window else 0.0,
        unknown_share=unknown,
    )
