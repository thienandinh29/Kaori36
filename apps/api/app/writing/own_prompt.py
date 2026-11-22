"""A Task 2 question the learner typed (specs/writing/step-2.10.md). Pure, no model.

The check refuses what is clearly not a Task 2 question; the type is a guess from the wording and
only labels the prompt. An own question becomes a draft Task 2 `Prompt` with the id `own`.

Step 2.11b: code proposes the question's parts from its wording (no model in a request); the
learner ticks the ones the question really asks before writing. Only proposed parts can be
ticked, so nothing but the learner's own question reaches the model.
"""

import re
import unicodedata
from collections.abc import Sequence

from app.writing.prompts import MAX_PARTS, Part, Prompt, PromptType

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


NO_PARTS_VI = "Hãy giữ ít nhất một phần của đề mà bài cần trả lời."
BAD_PARTS_VI = "Các phần của đề không khớp với đề bài. Bạn kiểm tra lại đề nhé."

_VERB = r"(?:believe|think|argue|feel|say|claim|consider)s?"
_VIEWS = re.compile(
    rf"\b(?:some|many|most) (?:people|experts|parents|students)? ?{_VERB} (?:that )?(?P<a>[^.;?]+?)"
    rf"(?:,? (?:while|whereas|but)|[.;]) ?(?:some |many )?(?:others?|other people) {_VERB} "
    r"(?:that )?(?P<b>[^.;?]+)[.;?]",
    re.I,
)
_OPINION = re.compile(
    r"\b(?:give|state|include) your (?:own )?opinion|\byour (?:own )?opinion\b", re.I
)
_POSITION_QUESTION = re.compile(
    r"positive or (?:a )?negative|agree or disagree|do you (?:think|agree|believe)|outweigh"
    r"|is (?:this|it) (?:a )?(?:good|bad)",
    re.I,
)


def _clean(text: str) -> str:
    return " ".join(text.split()).strip(" ,.;:?")


_AND_WH = re.compile(r",? and (?=(?:what|why|how|which|who|where|when|is|are|do|does)\b)", re.I)


def _questions(q: str) -> list[str]:
    """The direct questions in the wording, each ending in '?'; "Why…, and what…?" is two."""
    found: list[str] = []
    for s in re.findall(r"[^.?!]*\?", q):
        for piece in _AND_WH.split(s):
            if len(_clean(piece).split()) >= 3:
                text = _clean(piece)
                found.append(text[0].upper() + text[1:] + "?")
    return found


def propose_parts(text: str) -> tuple[Part, ...]:
    """What the question asks for, guessed from its wording; the learner confirms by ticking."""
    q = normalise(text)
    kind = guess_type(q)
    parts: list[Part] = []
    if kind == "discussion":
        m = _VIEWS.search(q)
        if m:
            parts += [Part(text=f"the view that {_clean(m['a'])}"[:200]),
                      Part(text=f"the view that {_clean(m['b'])}"[:200])]  # fmt: skip
        else:
            parts += [Part(text="the first view"), Part(text="the second view")]
    elif kind == "advantages-disadvantages":
        parts += [Part(text="the advantages"), Part(text="the disadvantages")]
        if re.search(r"outweigh", q, re.I):
            parts.append(
                Part(text="whether the advantages outweigh the disadvantages", position=True)
            )
    elif kind == "problem-solution":
        named = next((w for w in ("causes", "reasons", "problems")
                      if re.search(rf"\b{w[:-1]}s?\b", q, re.I)), "problems")  # fmt: skip
        parts += [Part(text=f"the {named}"), Part(text="the solutions")]
    elif kind == "opinion" and re.search(r"agree or disagree|do you agree", q, re.I):
        parts.append(Part(text="how far you agree or disagree", position=True))
    else:
        for question in _questions(q):
            position = bool(_POSITION_QUESTION.search(question)) and not any(
                p.position for p in parts
            )
            parts.append(Part(text=question[:200], position=position))
    if _OPINION.search(q) and not any(p.position for p in parts):
        parts.append(Part(text="your own opinion", position=True))
    if not parts:
        parts.append(Part(text="your answer to the question", position=True))
    unique = list({p.text.lower(): p for p in parts}.values())
    return tuple(unique[:MAX_PARTS])


def parts_problem(text: str, chosen: Sequence[str] | None) -> str | None:
    """Why the ticked parts are refused (Vietnamese): none ticked, or one that was not proposed."""
    if chosen is None:
        return None
    if not chosen:
        return NO_PARTS_VI
    proposed = {p.text for p in propose_parts(text)}
    if any(c not in proposed for c in chosen):
        return BAD_PARTS_VI
    return None


def as_prompt(text: str, chosen: Sequence[str] | None = None) -> Prompt:
    """The learner's question as a draft Task 2 prompt; call `problem` and `parts_problem` first.

    `chosen` are the parts the learner kept; None (an essay from before step 2.11b) keeps all.
    """
    q = normalise(text)
    parts = tuple(p for p in propose_parts(q) if chosen is None or p.text in chosen)
    return Prompt(id=OWN_ID, task=2, type=guess_type(q), level="B2", status="draft", prompt=q,
                  parts=parts)  # fmt: skip
