"""A Task 2 question the learner typed (specs/writing/step-2.10.md). Pure, no model.

The check refuses what is clearly not a Task 2 question; the type is a guess from the wording and
only labels the prompt. An own question becomes a draft Task 2 `Prompt` with the id `own`.
"""

import re
import unicodedata

from app.writing.prompts import Prompt, PromptType

OWN_ID = "own"
MIN_CHARS, MAX_CHARS, MIN_WORDS = 40, 600, 8
LATIN_SHARE = 0.95  # letters that are A to Z: an English question, not a Vietnamese one

_LINK = re.compile(r"https?://|www\.", re.I)
# Task 1 wording: "the chart below shows", "summarise the information", "the two maps".
_TASK1 = re.compile(
    r"summari[sz]e the (main )?(information|features)"
    r"|\b(the|this|these|two|three) (pie |bar |line )?(charts?|graphs?|tables?|diagrams?|maps?)\b"
    r"|\b(charts?|graphs?|tables?|diagrams?|maps?) (below|above|shows?|illustrates?|gives?)\b",
    re.I,
)
_TYPES: tuple[tuple[PromptType, re.Pattern[str]], ...] = (
    ("discussion", re.compile(r"discuss both|both (these )?views|both sides", re.I)),
    ("advantages-disadvantages", re.compile(r"advantages?\b.*\bdisadvantages?|outweigh", re.I)),
    (
        "problem-solution",
        re.compile(r"(problems?|causes?|reasons?)\b.*\b(solutions?|solve|measures)", re.I),
    ),
    ("opinion", re.compile(r"agree or disagree|to what extent|do you agree", re.I)),
)

TOO_SHORT_VI = f"Đề bài cần ít nhất {MIN_WORDS} từ và {MIN_CHARS} ký tự."
TOO_LONG_VI = f"Đề bài dài quá: tối đa {MAX_CHARS} ký tự."
LINK_VI = "Đề bài không được chứa đường link."
NOT_ENGLISH_VI = "Đề bài cần viết bằng tiếng Anh, như trong đề thi."
TASK1_VI = "Đề Task 1 cần số liệu của biểu đồ, hiện chưa hỗ trợ. Hãy nhập một đề Task 2."


def normalise(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split())


def problem(text: str) -> str | None:
    """Why the question is refused (Vietnamese), or None when it is accepted."""
    q = normalise(text)
    if len(q) < MIN_CHARS or len(q.split()) < MIN_WORDS:
        return TOO_SHORT_VI
    if len(q) > MAX_CHARS:
        return TOO_LONG_VI
    if _LINK.search(q):
        return LINK_VI
    letters = [c for c in q if c.isalpha()]
    if not letters or sum(c.isascii() for c in letters) / len(letters) < LATIN_SHARE:
        return NOT_ENGLISH_VI
    if _TASK1.search(q):
        return TASK1_VI
    return None


def guess_type(text: str) -> PromptType:
    q = normalise(text)
    for kind, pattern in _TYPES:
        if pattern.search(q):
            return kind
    return "two-part" if q.count("?") >= 2 else "opinion"


def as_prompt(text: str) -> Prompt:
    """The learner's question as a draft Task 2 prompt; call `problem` first."""
    q = normalise(text)
    return Prompt(id=OWN_ID, task=2, type=guess_type(q), level="B2", status="draft", prompt=q)
