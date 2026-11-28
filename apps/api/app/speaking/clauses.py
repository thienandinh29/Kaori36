"""Where the clauses end in a Speaking transcript (specs/speaking/step-5.2.md); approximate.

The recogniser's punctuation is not used: it follows the audio, and it puts a full stop at a long
pause, which would let a pause decide its own class (found on the real recogniser, 28 Nov 2026).
The words are parsed without punctuation and without fillers (um, uh, ...). A clause starts at a
sentence start in the parse; at a coordinating conjunction or subordinator that joins clauses; at a
relative or wh-word; and at the left edge of a separate finite clause (a verb with its own subject,
attached to another clause). Each parsed token is traced back to its word by character position.
A filler is transparent: a gap is a clause boundary when the next real word starts a clause, or
when only fillers come before it. Run-on speech parses unreliably: expect missed boundaries.
"""

import re
from collections.abc import Callable, Sequence
from typing import Any

from app.speaking.wer import FILLERS

_EDGE = re.compile(r"^[^\w']+|[^\w']+$")
_WH_TAGS = {"WDT", "WP", "WP$", "WRB"}
_CLAUSE_HEADS = {"VERB", "AUX"}
_CLAUSE_DEPS = {"conj", "parataxis", "advcl", "ccomp", "relcl", "acl"}
_SUBJECTS = {"nsubj", "nsubjpass", "expl"}


def _plain(word: str) -> str:
    return _EDGE.sub("", word)


def _is_filler(word: str) -> bool:
    return _plain(word).lower() in FILLERS


def _starts(content: Sequence[str], nlp: Callable[[str], Any]) -> set[int]:
    """Indices into `content` (the real words) of the words that start a clause, not the first."""
    spans: list[tuple[int, int]] = []
    pos = 0
    for w in content:
        spans.append((pos, pos + len(w)))
        pos += len(w) + 1

    def word_at(char: int) -> int | None:
        return next((k for k, (a, b) in enumerate(spans) if a <= char < b), None)

    doc = list(nlp(" ".join(content)))
    marked: set[int] = set()
    for token in doc:
        j = word_at(token.idx)
        if j is None or token.idx != spans[j][0]:
            continue  # not the first token of its word
        if (
            token.is_sent_start
            or token.tag_ in _WH_TAGS
            or (token.dep_ in ("mark", "cc") and token.head.pos_ in _CLAUSE_HEADS)
        ):
            marked.add(j)
    for token in doc:
        if (
            token.pos_ in _CLAUSE_HEADS
            and token.dep_ in _CLAUSE_DEPS
            and any(c.dep_ in _SUBJECTS for c in token.children)
        ):
            j = word_at(token.left_edge.idx)
            # not when a conjunction or subordinator right before it already started the clause
            if j is not None and token.left_edge.idx == spans[j][0] and j - 1 not in marked:
                marked.add(j)
    marked.discard(0)
    return marked


def clause_boundaries(texts: Sequence[str], nlp: Callable[[str], Any]) -> set[int]:
    """The word indices after which a clause ends (the last word is not listed)."""
    content = [i for i, t in enumerate(texts) if _plain(t) and not _is_filler(t)]
    starts = (
        {content[j] for j in _starts([_plain(texts[i]) for i in content], nlp)}
        if len(content) >= 2
        else set()
    )
    real = set(content)
    boundaries: set[int] = set()
    for i in range(len(texts) - 1):
        following = next((k for k in range(i + 1, len(texts)) if k in real), None)
        if following is None:
            continue  # only fillers or punctuation follow
        if not any(k <= i for k in real):
            boundaries.add(i)  # only fillers come before: the clause has not begun
        elif following in starts:
            boundaries.add(i)
    return boundaries
