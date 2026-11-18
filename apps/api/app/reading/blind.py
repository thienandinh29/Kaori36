"""Blind check of a Reading item (specs/listening-reading/step-4.2b.md).

The checker sees the passage and the learner's view of the question only: no key, no accepted
answers, no evidence. Its reply is turned into an answer and graded by `items.grade`, the same
function that grades learners. Full marks gives `verified`; anything else gives `needs_review`.
"""

import re
from collections.abc import Awaitable, Callable
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.reading.items import Completion, Headings, Mcq, Tfng, grade
from app.writing.analysis import paragraphs

ReadingItem = Tfng | Mcq | Completion | Headings
LETTERS = "ABCD"

SYSTEM = (
    "You answer IELTS Reading questions using only the passage given. Do not use outside "
    "knowledge. Answer only with the JSON asked for."
)


class Reply(BaseModel):
    model_config = ConfigDict(extra="ignore")
    answer: str


Ask = Callable[[str, str], Awaitable[Reply | None]]  # (system, prompt) -> reply, None if unusable


def question(item: ReadingItem, passage: str) -> str:
    """The prompt: the passage (paragraphs numbered for headings) and the question, never a key."""
    if isinstance(item, Headings):
        paras = paragraphs(passage)
        body = "\n\n".join(f"Paragraph {i}: {p}" for i, p in enumerate(paras))
        heads = "\n".join(f"{i}. {h}" for i, h in enumerate(item.headings))
        wanted = ", ".join(f"{p}:<heading number>" for p in sorted(item.key))
        return (
            f"Passage:\n\n{body}\n\nChoose the right heading for each paragraph from this list "
            f"(some headings are not used):\n{heads}\n\n"
            f'Return {{"answer": "{wanted}"}}.'
        )
    head = f"Passage:\n\n{passage}\n\n"
    if isinstance(item, Tfng):
        return head + (
            f"Statement: {item.statement}\n\nDoes the passage agree with the statement? "
            "Answer TRUE if it agrees, FALSE if it contradicts it, NOT GIVEN if the passage "
            "says nothing about it.\n"
            'Return {"answer": "TRUE"}, {"answer": "FALSE"} or {"answer": "NOT GIVEN"}.'
        )
    if isinstance(item, Mcq):
        options = "\n".join(f"{LETTERS[i]}. {o}" for i, o in enumerate(item.options))
        return head + (
            f"Question: {item.stem}\n{options}\n\nChoose one letter.\n"
            'Return {"answer": "<letter>"}.'
        )
    return head + (
        f"Complete the sentence with NO MORE THAN {item.max_words} WORD"
        f"{'S' if item.max_words > 1 else ''} taken from the passage:\n{item.sentence}\n\n"
        'Return {"answer": "<the words>"}.'
    )


def answer_of(item: ReadingItem, reply: Reply) -> object:
    """The reply as the answer `items.grade` expects for this kind."""
    text = reply.answer.strip()
    if isinstance(item, Mcq):
        letter = text[:1].upper()
        return LETTERS.index(letter) if letter and letter in LETTERS[: len(item.options)] else -1
    if isinstance(item, Headings):
        pairs = re.findall(r"(\d+)\s*[:=-]\s*(\d+)", text)
        return {int(p): int(h) for p, h in pairs}
    return text


Outcome = Literal["verified", "needs_review"]


async def check(item: ReadingItem, passage: str, ask: Ask) -> tuple[Outcome, str | None]:
    """The outcome and the checker's raw answer (None when its reply was unusable)."""
    reply = await ask(SYSTEM, question(item, passage))
    if reply is None:
        return "needs_review", None
    right = grade(item, answer_of(item, reply)) == 1.0
    return ("verified" if right else "needs_review"), reply.answer[:200]
