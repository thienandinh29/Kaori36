"""Did the learner repair the error, or remove it? (specs/writing/step-2.8.md). Pure."""

import re
import unicodedata
from typing import Literal

Outcome = Literal["deleted", "unchanged", "check"]
_WORD = re.compile(r"[\w']+")
MAX_LOST = 0.4  # more than this share of the sentence's other words gone: removed, not fixed


def _words(text: str) -> list[str]:
    flat = unicodedata.normalize("NFC", text).replace("\N{RIGHT SINGLE QUOTATION MARK}", "'")
    return [w.lower() for w in _WORD.findall(flat)]


def _contains(haystack: list[str], needle: list[str]) -> bool:
    n = len(needle)
    return n > 0 and any(haystack[i : i + n] == needle for i in range(len(haystack) - n + 1))


def judge(original: str, start: int, end: int, attempt: str) -> Outcome:
    """`start`/`end`: the error's span within `original`. "check" = let the usual rule decide."""
    before, span, after = (
        _words(original[:start]),
        _words(original[start:end]),
        _words(original[end:]),
    )
    got = _words(attempt)
    rest = before + after
    if rest:
        left = set(got)
        lost = sum(1 for w in rest if w not in left) / len(rest)
        neighbours = before[-1:] + after[:1]
        # More words gone than the error had, around the error: it was removed, not changed.
        shrank = len(got) < len(rest)
        if lost > MAX_LOST or (shrank and any(w not in left for w in neighbours)):
            return "deleted"
    elif not got:
        return "deleted"
    if _contains(got, before[-1:] + span + after[:1]):
        return "unchanged"
    return "check"
