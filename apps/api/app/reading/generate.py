"""Generate Reading questions for one text (specs/listening-reading/step-4.2b.md).

The generator (gateway task `reading_items`, DeepSeek) writes questions in a small JSON shape;
code assigns ids, builds 4.2a items and checks them against the passage. The model never
decides an id, a status or whether an item is kept.
"""

import re
from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.reading.items import BLANK, Completion, Headings, Mcq, Skill, Tfng, check
from app.writing.analysis import paragraphs

ReadingItem = Tfng | Mcq | Completion | Headings

SYSTEM = (
    "You write IELTS-style Reading questions for Vietnamese learners of English. Every answer "
    "must be decided by the passage alone, never by general knowledge. Quote the passage exactly "
    "in `evidence`. Answer only with the JSON asked for."
)


class _Out(BaseModel):
    model_config = ConfigDict(extra="ignore")
    skill: Skill
    evidence: list[str] = Field(default_factory=list)


class GenTfng(_Out):
    statement: str
    key: Literal["true", "false", "not_given"]


class GenMcq(_Out):
    stem: str
    options: list[str] = Field(min_length=3, max_length=4)
    key: int


class GenCompletion(_Out):
    sentence: str
    accepted: list[str] = Field(min_length=1)
    max_words: int = Field(ge=1, le=3)


class GenHeadings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    headings: list[str]
    key: list[int]  # heading index for paragraph 0, 1, 2, ...


class Generated(BaseModel):
    model_config = ConfigDict(extra="ignore")
    tfng: list[GenTfng] = Field(default_factory=list)
    mcq: list[GenMcq] = Field(default_factory=list)
    completion: list[GenCompletion] = Field(default_factory=list)
    headings: GenHeadings | None = None

    @field_validator("tfng", "mcq", "completion", mode="before")
    @classmethod
    def _one_or_many(cls, value: object) -> object:
        """ "Write one question" is often answered with an object rather than a list of one."""
        return [value] if isinstance(value, dict) else value


LONG_PASSAGE_WORDS = 450


def prompt(passage: str) -> str:
    n = len(paragraphs(passage))
    headings = (
        f"- `headings`: one item: {n + 2} short headings and, for each of the {n} paragraphs in "
        "order, the index of its heading (two extra headings fit no paragraph). Every paragraph "
        "gets a different heading: no index appears twice in `key`.\n"
        if n >= 3
        else "- `headings`: null.\n"
    )
    # An IELTS-length passage gets about an exam's worth of questions (about 13 per passage);
    # a short one keeps the first bank's set, so earlier items keep their meaning.
    long = len(passage.split()) >= LONG_PASSAGE_WORDS
    tfng = (
        "five statements, keys `true`, `false` or `not_given`; one or two must be `not_given`, "
        "and at least one each `true` and `false`"
        if long
        else "two statements, keys `true`, `false` or `not_given`; exactly one must be `not_given`"
    )
    mcq, completion = (
        ("three questions", "three sentences") if long else ("one question", "one sentence")
    )
    return (
        f"Passage:\n\n{passage}\n\nWrite:\n"
        f"- `tfng`: {tfng} (`not_given`: the passage says nothing either way; give it no "
        "evidence).\n"
        f"- `mcq`: {mcq}, each with 4 options and `key`, the 0-based index of the one right "
        "option. A stem must not contain its right option's words.\n"
        f"- `completion`: {completion}, each with exactly one ___ and `accepted`, the answer "
        "copied word for word from the passage, at most `max_words` words (1-3).\n"
        + headings
        + "Each of tfng, mcq and completion has `skill` (detail, main_idea, inference, "
        "writers_view or skimming) and `evidence`: the passage sentences, copied exactly, that "
        "decide the answer."
    )


Dropped = tuple[str, str, list[str], dict[str, object]]  # id, kind, problems, what was written


def build(
    slug: str, passage: str, out: Generated, base: str | None = None
) -> tuple[list[ReadingItem], list[Dropped]]:
    """Items that pass every code check, and the dropped ones with what the model wrote.

    `base`: the start of every item id, the slug for a text's first passage version, else
    `{slug}-v{n}`, so a changed passage's items never collide with the old version's.
    """
    raw: list[tuple[str, dict[str, object]]] = []
    stem = base or slug
    for i, t in enumerate(out.tfng):
        raw.append(("tfng", {"id": f"{stem}-tfng-{i + 1}", **t.model_dump()}))
    for i, m in enumerate(out.mcq):
        raw.append(("mcq", {"id": f"{stem}-mcq-{i + 1}", **m.model_dump()}))
    for i, c in enumerate(out.completion):
        data = c.model_dump()
        # Models write the gap as "______" as often as "___"; one run of underscores is one gap.
        data["sentence"] = re.sub(r"_{3,}", BLANK, data["sentence"])
        raw.append(("completion", {"id": f"{stem}-completion-{i + 1}", **data}))
    if out.headings is not None:
        raw.append(("headings", {
            "id": f"{stem}-headings-1", "skill": "main_idea", "headings": out.headings.headings,
            "key": dict(enumerate(out.headings.key)),
        }))  # fmt: skip
    kinds: dict[str, type[ReadingItem]] = {
        "tfng": Tfng, "mcq": Mcq, "completion": Completion, "headings": Headings,
    }  # fmt: skip
    kept: list[ReadingItem] = []
    dropped: list[Dropped] = []
    for kind, data in raw:
        data |= {"text": slug, "origin": "generated", "status": "draft"}
        try:
            item = kinds[kind].model_validate(data)
        except ValidationError as exc:
            dropped.append((str(data["id"]), kind, [e["msg"] for e in exc.errors()][:5], data))
            continue
        problems = check(item, passage)
        if problems:
            dropped.append((item.id, kind, problems, data))
        else:
            kept.append(item)
    return kept, dropped


def ids(items: Sequence[ReadingItem]) -> list[str]:
    return [i.id for i in items]
