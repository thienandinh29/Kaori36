"""Dictionary search over the word list (specs/vocabulary/step-dictionary.md). Pure.

Ranked groups: headword equal, headword prefix, headword contains (3+ letters), the Vietnamese
meaning contains the query as whole syllables with its diacritics, and, for a query typed without
diacritics, the same with diacritics removed. Inside a group: easier level first, then alphabetical.
"""

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from app.curriculum.course import LEVELS
from app.vocabulary.wordlist import Word

MAX_QUERY = 40


def normalise(text: str) -> str:
    """NFC, case-folded, single spaces."""
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def fold(text: str) -> str:
    """`text` without Vietnamese diacritics (đ becomes d)."""
    decomposed = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def has_diacritics(text: str) -> bool:
    return fold(text) != text


@dataclass(frozen=True)
class Found:
    words: list[Word]
    total: int


def _has_phrase(text: str, q: str) -> bool:
    """`q` occurs in `text` as whole syllables (Vietnamese syllables are separated by spaces)."""
    return re.search(rf"(?<!\w){re.escape(q)}(?!\w)", text) is not None


def rank(word: Word, q: str) -> int | None:
    """The match group of `word` for the normalised query `q` (0 best), or None."""
    lemma = word.lemma.casefold()
    if lemma == q:
        return 0
    if lemma.startswith(q):
        return 1
    if len(q) >= 3 and q in lemma:
        return 2
    vi = normalise(word.vi or "")
    if vi and _has_phrase(vi, q):
        return 3
    if vi and not has_diacritics(q) and _has_phrase(fold(vi), q):
        return 4
    return None


def search(words: Sequence[Word], query: str, limit: int) -> Found:
    q = normalise(query)[:MAX_QUERY]
    if not q:
        return Found([], 0)
    hits = [(r, w) for w in words if (r := rank(w, q)) is not None]
    hits.sort(key=lambda x: (x[0], LEVELS.index(x[1].level), x[1].lemma, x[1].pos))
    return Found([w for _, w in hits[:limit]], len(hits))
