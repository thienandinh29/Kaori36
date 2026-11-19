"""Reading question types, checks against the passage, and answer-key grading.

Spec: specs/listening-reading/step-4.2a.md. No model decides anything here: the key grades, code
checks that every item rests on sentences really in its passage, and only items the owner approved
are served. Options and headings are shown in a fixed shuffled order per item (`presented`, step
4.3c): the generator's order gave answers away.
"""

import hashlib
import random
import re
import unicodedata
from typing import Annotated, Literal, Self, overload

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.graders.typed import grade_typed, normalise
from app.writing.analysis import paragraphs, words

BLANK = "___"
Skill = Literal["detail", "main_idea", "inference", "writers_view", "skimming"]
Status = Literal["draft", "needs_review", "verified", "approved"]
Slug = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)]
_QUOTES = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'})
TFNG_ANSWERS = {
    "true": "true", "t": "true", "yes": "true",
    "false": "false", "f": "false", "no": "false",
    "not given": "not_given", "not_given": "not_given", "ng": "not_given",
}  # fmt: skip


def _norm(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).translate(_QUOTES).split())


def _contains(haystack: str, needle: str) -> bool:
    """Whole-word, case-insensitive containment after normalisation."""
    pattern = rf"(?<![\w']){re.escape(_norm(needle).casefold())}(?![\w'])"
    return re.search(pattern, _norm(haystack).casefold()) is not None


# An option that points at other options ("both A and B", "all of the above") breaks once the
# options are shuffled, so code refuses it (step 4.3c).
_REFERS_WORDS = re.compile(
    r"\b(?:all|none|both|neither|either) of (?:the )?(?:above|these|them|the options)\b"
    r"|\b(?:options?|answers?|choices?) [A-D]\b",
    re.IGNORECASE,
)
_REFERS_LETTERS = re.compile(r"\b[A-D] (?:and|or|&) [A-D]\b")


def _refers_to_options(option: str) -> bool:
    return bool(_REFERS_WORDS.search(option) or _REFERS_LETTERS.search(option))


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: Slug
    text: Slug  # the bank text's slug
    skill: Skill
    evidence: tuple[str, ...] = ()
    origin: Literal["authored", "generated"] = "authored"
    status: Status = "draft"


class Tfng(_Base):
    kind: Literal["tfng"] = "tfng"
    statement: str = Field(min_length=5)
    key: Literal["true", "false", "not_given"]


class Mcq(_Base):
    kind: Literal["mcq"] = "mcq"
    stem: str = Field(min_length=5)
    options: tuple[str, ...] = Field(min_length=3, max_length=4)
    key: int = Field(ge=0)

    @model_validator(mode="after")
    def _key_in_range(self) -> Self:
        if self.key >= len(self.options):
            raise ValueError("key must index an option")
        return self


class Completion(_Base):
    kind: Literal["completion"] = "completion"
    sentence: str = Field(min_length=5)
    accepted: tuple[str, ...] = Field(min_length=1)
    max_words: int = Field(ge=1, le=3)

    @model_validator(mode="after")
    def _one_blank(self) -> Self:
        if self.sentence.count(BLANK) != 1:
            raise ValueError(f"the sentence needs exactly one {BLANK}")
        return self


class Headings(_Base):
    kind: Literal["headings"] = "headings"
    headings: tuple[str, ...] = Field(min_length=2)
    key: dict[int, int]  # paragraph index (0-based) -> heading index

    @model_validator(mode="after")
    def _shape(self) -> Self:
        if not self.key:
            raise ValueError("headings needs at least one paragraph")
        if len(self.headings) <= len(self.key):
            raise ValueError("there must be more headings than paragraphs")
        if any(not 0 <= h < len(self.headings) for h in self.key.values()):
            raise ValueError("every key must index a heading")
        return self


Item = Annotated[Tfng | Mcq | Completion | Headings, Field(discriminator="kind")]


def check(item: Tfng | Mcq | Completion | Headings, passage: str) -> list[str]:
    """Problems that keep the item from ever being served; empty means it passes."""
    problems: list[str] = []
    flat = _norm(passage)
    for q in item.evidence:
        if _norm(q) not in flat:
            problems.append(f"evidence not in the passage: {q!r}")
    needs_evidence = not (isinstance(item, Tfng) and item.key == "not_given")
    if needs_evidence and not isinstance(item, Headings) and not item.evidence:
        problems.append("no evidence sentence")
    if isinstance(item, Completion):
        before, after = item.sentence.split(BLANK)
        for a in item.accepted:
            if len(words(a)) > item.max_words:
                problems.append(f"answer {a!r} is longer than {item.max_words} words")
            if not _contains(passage, a):
                problems.append(f"answer {a!r} is not in the passage")
            elif item.evidence and not any(_contains(q, a) for q in item.evidence):
                problems.append(f"answer {a!r} is not in the evidence")
            if _contains(before, a) or _contains(after, a):
                problems.append(f"the sentence already contains the answer {a!r}")
    if isinstance(item, Mcq):
        if len({normalise(o) for o in item.options}) != len(item.options):
            problems.append("options are not distinct")
        if _contains(item.stem, item.options[item.key]):
            problems.append("the stem contains the key option")
        for o in item.options:
            if _refers_to_options(o):
                problems.append(f"an option refers to other options: {o!r}")
    if isinstance(item, Headings):
        count = len(paragraphs(passage))
        for p in item.key:
            if not 0 <= p < count:
                problems.append(f"paragraph {p} does not exist (the passage has {count})")
        if len(set(item.key.values())) != len(item.key):
            problems.append("two paragraphs share a heading")
    return problems


def servable(item: Tfng | Mcq | Completion | Headings, passage: str) -> bool:
    """Only the owner's approved items that pass every check reach a learner."""
    return item.status == "approved" and not check(item, passage)


def grade(item: Tfng | Mcq | Completion | Headings, answer: object) -> float:
    """1.0 or 0.0, except headings: the share of paragraphs right. From the key only."""
    if isinstance(item, Tfng):
        given = TFNG_ANSWERS.get(normalise(str(answer)).replace("-", " "))
        return float(given == item.key)
    if isinstance(item, Mcq):
        return float(
            isinstance(answer, int) and not isinstance(answer, bool) and answer == item.key
        )
    if isinstance(item, Completion):
        text = str(answer)
        if len(words(text)) > item.max_words:
            return 0.0
        return float(grade_typed(text, item.accepted))
    if not isinstance(answer, dict):
        return 0.0
    right = sum(1 for p, h in item.key.items() if answer.get(p) == h)
    return right / len(item.key)


def learner_view(item: Tfng | Mcq | Completion | Headings) -> dict[str, object]:
    """What the learner sees: no key, no accepted answers, no evidence.

    Callers pass `presented(item)`, so options and headings are in the shown order.
    """
    hidden = {"key", "accepted", "evidence", "status", "origin"}
    return item.model_dump(mode="json", exclude=hidden)


# --- The shown order (specs/listening-reading/step-4.3c.md) ---
#
# The generator's order gave answers away: the multiple-choice key was B in half the bank and many
# headings lists followed the paragraphs. Every surface (learners, the owner's review, the expert
# portal, the blind checker) shows `presented(item)`; every stored answer is in the stored order
# (`to_stored`), so a stored item, its key and every recorded answer keep one meaning.


def _order(item_id: str, n: int) -> list[int]:
    """Position i shows stored entry order[i]: a uniform shuffle, fixed per item id."""
    order = list(range(n))
    random.Random(hashlib.sha256(f"reading-order:{item_id}".encode()).hexdigest()).shuffle(order)
    return order


def _index(value: object, n: int) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and 0 <= value < n:
        return value
    return None


@overload
def presented(item: Mcq) -> Mcq: ...
@overload
def presented(item: Headings) -> Headings: ...
@overload
def presented(
    item: Tfng | Mcq | Completion | Headings,
) -> Tfng | Mcq | Completion | Headings: ...
def presented(
    item: Tfng | Mcq | Completion | Headings,
) -> Tfng | Mcq | Completion | Headings:
    """The item as everyone sees it: options or headings in their shown order, the key remapped."""
    if isinstance(item, Mcq):
        order = _order(item.id, len(item.options))
        options = tuple(item.options[i] for i in order)
        return item.model_copy(update={"options": options, "key": order.index(item.key)})
    if isinstance(item, Headings):
        order = _order(item.id, len(item.headings))
        key = {p: order.index(h) for p, h in item.key.items()}
        headings = tuple(item.headings[i] for i in order)
        return item.model_copy(update={"headings": headings, "key": key})
    return item


def to_stored(item: Tfng | Mcq | Completion | Headings, answer: object) -> object:
    """An answer given against `presented(item)`, in the stored order (graded and kept so).

    Anything that is not a valid position is returned unchanged, so it stays wrong.
    """
    if isinstance(item, Mcq):
        i = _index(answer, len(item.options))
        return answer if i is None else _order(item.id, len(item.options))[i]
    if isinstance(item, Headings) and isinstance(answer, dict):
        order = _order(item.id, len(item.headings))
        out: dict[object, object] = {}
        for p, h in answer.items():
            i = _index(h, len(order))
            out[p] = h if i is None else order[i]
        return out
    return answer


def to_presented(item: Tfng | Mcq | Completion | Headings, answer: object) -> object:
    """A stored-order answer (a learner's or the checker's) in the shown order."""
    if isinstance(item, Mcq):
        i = _index(answer, len(item.options))
        return answer if i is None else _order(item.id, len(item.options)).index(i)
    if isinstance(item, Headings) and isinstance(answer, dict):
        order = _order(item.id, len(item.headings))
        out: dict[object, object] = {}
        for p, h in answer.items():
            i = _index(h, len(order))
            out[p] = h if i is None else order.index(i)
        return out
    return answer
