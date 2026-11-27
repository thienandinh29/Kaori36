"""Why the key is right and what each wrong option tempted (CP4b on the bank's own questions).

`specs/listening-reading/spec.md`, "Why the wrong answer tempted you", step 1. Pure: the model's
output shape, the prompt, and code's checks. One DeepSeek call per question (gateway task
`reading_explain`) returns, for the key, `why_key_vi` and its quotes; for each wrong option of a
multiple-choice question, a trap from the closed list, `why_vi` and quotes; and the question's
sub-skill tags (`step-4.3e.md`, Bronze). For T/F/NG and completion only the key's part is written:
code names those traps from the learner's answer.

Nothing here is shown to a learner. The blind check by another family and its planted test come
before anything is (the next step); headings questions are not explained yet.
"""

import hashlib
import json
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.reading.items import BLANK, Completion, Headings, Mcq, Tfng, _contains
from app.reading.own_test import MCQ_TRAPS, vietnamese

ExplainedItem = Tfng | Mcq | Completion
EXPLAINED_KINDS = ("tfng", "mcq", "completion")
LETTERS = "ABCD"
MIN_WHY, MAX_WHY = 20, 400
MIN_QUOTE_WORDS = 3
MAX_QUOTES = 3

# The sub-skills of step 4.3e (a closed list; Bronze until a teacher labels a sample).
SKILL_TAGS = ("scan_detail", "paraphrase", "inference", "vocab_context", "fng_logic", "main_idea")
MAX_TAGS = 3

# "Bài không nói…": a NOT GIVEN key has no deciding sentence, so the text must say so.
NOT_STATED = re.compile(
    r"không (?:hề |được |có )?(?:nói|đề cập|nhắc|cho biết|khẳng định|nêu)|không có thông tin",
    re.IGNORECASE,
)
# Learners see options shuffled (step 4.3c): an explanation never names an option by letter.
LETTER_REF = re.compile(r"(?i:đáp án|lựa chọn|phương án|option|choice)\s+[A-D]\b")

SYSTEM = (
    "You explain IELTS Reading questions to Vietnamese learners. Write every explanation in "
    "Vietnamese, quoting the passage exactly (in English) for the words it rests on. Rely on the "
    "passage alone, never on general knowledge. Never name an option by its letter: the learner "
    "sees the options in another order, so refer to an option by quoting it. Answer only with the "
    "JSON asked for."
)


class OptionOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    option: int  # the wrong option's index in the order given (0 = the first)
    trap: str
    why_vi: str
    quotes: list[str] = Field(default_factory=list)


class ExplainOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    key_quotes: list[str] = Field(default_factory=list)
    why_key_vi: str
    options: list[OptionOut] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)


def fingerprint(item: ExplainedItem | Headings) -> str:
    """The question's fingerprint: an edited question drops its explanation."""
    data = item.model_dump(mode="json", exclude={"status"})
    text = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(unicodedata.normalize("NFC", text).encode()).hexdigest()


def _question(item: ExplainedItem) -> str:
    if isinstance(item, Tfng):
        key = {"true": "TRUE", "false": "FALSE", "not_given": "NOT GIVEN"}[item.key]
        return f"TRUE / FALSE / NOT GIVEN statement: {item.statement}\nKey: {key}"
    if isinstance(item, Mcq):
        options = "\n".join(f"{i}. {o}" for i, o in enumerate(item.options))
        return (
            f"Multiple choice: {item.stem}\nOptions (index. text):\n{options}\n"
            f"Key: option {item.key}"
        )
    return (
        f"Sentence completion (NO MORE THAN {item.max_words} WORD(S)): "
        f"{item.sentence.replace(BLANK, '_____')}\nKey: {' / '.join(item.accepted)}"
    )


def prompt(passage: str, item: ExplainedItem) -> str:
    evidence = "\n".join(f"- {e}" for e in item.evidence) or "- (none: the passage does not say)"
    if isinstance(item, Mcq):
        wrong = [i for i in range(len(item.options)) if i != item.key]
        options = (
            f"- `options`: one entry for EACH wrong option ({', '.join(map(str, wrong))}): "
            f"`option` (its index), `trap` (one of: {', '.join(MCQ_TRAPS)}), `why_vi` (why it is "
            "wrong, 1-2 sentences) and `quotes` (the passage words that tempt or contradict it; "
            "empty if the passage says nothing about it).\n"
        )
    else:
        options = "- `options`: an empty list.\n"
    return (
        "<<<PASSAGE\n" + passage + "\nPASSAGE>>>\n\n"
        f"Question:\n{_question(item)}\nThe sentences that decide the key:\n{evidence}\n\n"
        "Return JSON with:\n"
        "- `key_quotes`: 1-3 exact quotes from the passage that decide the key (for NOT GIVEN, the "
        "closest related sentence);\n"
        "- `why_key_vi`: why the key is right, 1-3 Vietnamese sentences (for NOT GIVEN, say what "
        "the passage does not state);\n"
        + options
        + f"- `skills`: 1-{MAX_TAGS} of {', '.join(SKILL_TAGS)}: what answering needs.\n"
    )


@dataclass(frozen=True)
class OptionExplanation:
    option: int
    trap: str
    why_vi: str
    quotes: tuple[str, ...]


@dataclass(frozen=True)
class Explanation:
    key_quotes: tuple[str, ...]
    why_key_vi: str
    options: tuple[OptionExplanation, ...]
    skills: tuple[str, ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "key_quotes": list(self.key_quotes), "why_key_vi": self.why_key_vi,
            "options": [
                {"option": o.option, "trap": o.trap, "why_vi": o.why_vi, "quotes": list(o.quotes)}
                for o in self.options
            ],
            "skills": list(self.skills),
        }  # fmt: skip


def _quote_problems(quotes: Sequence[str], passage: str, where: str) -> list[str]:
    out = []
    if len(quotes) > MAX_QUOTES:
        out.append(f"{where}: more than {MAX_QUOTES} quotes")
    for q in quotes:
        if len(q.split()) < MIN_QUOTE_WORDS:
            out.append(f"{where}: quote too short: {q!r}")
        elif not _contains(passage, q.strip(" .,;:")):
            out.append(f"{where}: quote not in the passage: {q!r}")
    return out


def _text_problems(text: str, quotes: Sequence[str], where: str) -> list[str]:
    out = []
    if not MIN_WHY <= len(text.strip()) <= MAX_WHY:
        out.append(f"{where}: {len(text.strip())} characters (needs {MIN_WHY}-{MAX_WHY})")
    if not vietnamese(text, quotes):
        out.append(f"{where}: not in Vietnamese")
    if LETTER_REF.search(text):
        out.append(f"{where}: names an option by letter")
    return out


def _overlaps(quotes: Sequence[str], evidence: Sequence[str]) -> bool:
    return any(_contains(e, q.strip(" .,;:")) or _contains(q, e) for q in quotes for e in evidence)


def check(
    out: ExplainOut, passage: str, item: ExplainedItem
) -> tuple[Explanation | None, list[str]]:
    """Code's checks (spec, "Code checks"); an explanation with any problem is not kept."""
    problems: list[str] = []
    key_quotes = [q.strip() for q in out.key_quotes if q.strip()]
    not_given = isinstance(item, Tfng) and item.key == "not_given"
    if not key_quotes:
        problems.append("key: no quote")
    problems += _quote_problems(key_quotes, passage, "key")
    if not not_given and key_quotes and item.evidence and not _overlaps(key_quotes, item.evidence):
        problems.append("key: the quote is not the question's deciding sentence")
    problems += _text_problems(out.why_key_vi, key_quotes, "key")
    if not_given and not NOT_STATED.search(out.why_key_vi):
        problems.append("key: a NOT GIVEN explanation must say what the passage does not state")
    options: list[OptionExplanation] = []
    if isinstance(item, Mcq):
        wrong = {i for i in range(len(item.options)) if i != item.key}
        seen: set[int] = set()
        for o in out.options:
            where = f"option {o.option}"
            if o.option == item.key:
                problems.append("the key is given a trap")
                continue
            if o.option not in wrong or o.option in seen:
                problems.append(f"{where}: not a wrong option, or repeated")
                continue
            seen.add(o.option)
            if o.trap not in MCQ_TRAPS:
                problems.append(f"{where}: trap {o.trap!r} is not on the list")
            quotes = [q.strip() for q in o.quotes if q.strip()]
            problems += _quote_problems(quotes, passage, where)
            problems += _text_problems(o.why_vi, quotes, where)
            options.append(OptionExplanation(o.option, o.trap, o.why_vi.strip(), tuple(quotes)))
        if seen != wrong:
            problems.append(f"options not explained: {sorted(wrong - seen)}")
    skills = list(dict.fromkeys(s.strip() for s in out.skills))
    if not 1 <= len(skills) <= MAX_TAGS:
        problems.append(f"{len(skills)} skill tags (needs 1-{MAX_TAGS})")
    problems += [f"skill tag {s!r} is not on the list" for s in skills if s not in SKILL_TAGS]
    if problems:
        return None, problems
    explanation = Explanation(
        tuple(key_quotes), out.why_key_vi.strip(), tuple(sorted(options, key=lambda o: o.option)),
        tuple(skills),
    )  # fmt: skip
    return explanation, []
