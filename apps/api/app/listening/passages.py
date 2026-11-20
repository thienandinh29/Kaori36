"""A Reading passage read aloud, in parts the voice can say (specs/listening-reading/step-4.4c.md).

The server voice takes at most 300 characters at a time, so a passage is read sentence by sentence;
a longer sentence is cut at a semicolon or comma, else between words. Joined, the parts give back
every word of the passage in order (tested), so nothing the questions depend on is skipped.
"""

import re

from app.listening.items import sentences

MAX_PART = 280  # under the voice's 300-character limit
SKILL_COMPETENCY = {"detail": "listening-detail"}  # every other Reading skill: the main idea
OTHER = "listening-main-idea"
LISTENED_KINDS = ("tfng", "mcq", "completion")  # headings need the paragraphs on screen


def _cut(sentence: str) -> list[str]:
    if len(sentence) <= MAX_PART:
        return [sentence]
    for sep in ("; ", ", "):
        pieces = sentence.split(sep)
        if len(pieces) > 1:
            out: list[str] = []
            cur = ""
            for i, p in enumerate(pieces):
                piece = p + (sep.strip() if i < len(pieces) - 1 else "")
                cand = f"{cur} {piece}".strip()
                if cur and len(cand) > MAX_PART:
                    out.append(cur)
                    cur = piece
                else:
                    cur = cand
            if cur:
                out.append(cur)
            if all(len(x) <= MAX_PART for x in out):
                return out
    words, out2, cur2 = sentence.split(), [], ""
    for w in words:
        cand = f"{cur2} {w}".strip()
        if cur2 and len(cand) > MAX_PART:
            out2.append(cur2)
            cur2 = w
        else:
            cur2 = cand
    return [*out2, cur2] if cur2 else out2


def parts(passage: str) -> list[str]:
    """What the voice reads, in order."""
    return [p for s in sentences(passage) for p in _cut(s)]


def words(text: str) -> list[str]:
    return re.findall(r"[\w']+", text.lower())


def competency(skill: str) -> str:
    return SKILL_COMPETENCY.get(skill, OTHER)
