"""A target-band rewrite of one paragraph, checked by code (specs/writing/step-2.4.md, point 4).

The model rewrites and gives reasons; the code decides what changed (its own word-level diff) and
shows a reason only next to a change that really exists. Length must stay close to the original:
a rewrite, not a new paragraph. LanguageTool and the scorer checks run in the worker.

Meaning checks (step 2.9, pure, Bronze thresholds): a rewrite is refused when it brings in facts
the learner did not write (a number, a year, a percentage, a name), flips a negation, or keeps too
few of the paragraph's content words to still be the learner's argument. A model of another family
judging claim by claim is specified for later; these checks catch the clear cases only.
"""

import difflib
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.writing.analysis import words
from app.writing.scoring import BAND_MAX

DEFAULT_TARGET = 6.5  # no band yet (the owner's decision, 14 Nov)
LENGTH_RATIO = (0.6, 1.6)
_CURLY = chr(0x2019)  # a curly apostrophe, as phones and models type it
_TOKEN = re.compile(r"\w+(?:['" + _CURLY + r"]\w+)*|[^\w\s]")


class ChangeOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    original: str = Field(max_length=400)
    revised: str = Field(max_length=400)
    why_vi: str = Field(min_length=5, max_length=500)


class RewriteOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    paragraph: str = Field(min_length=20, max_length=4000)
    changes: list[ChangeOut] = Field(max_length=25)


SYSTEM = (
    "You help a Vietnamese learner improve one paragraph of an IELTS Writing Task 2 essay. Rewrite "
    "the paragraph at the target band: keep the learner's ideas, opinion and examples, keep about "
    "the same length, and change only what raises the level (grammar, word choice, linking, "
    "sentence variety). Never add a new example, statistic, number, date, name or claim, and "
    "never turn a statement into its opposite. Write the paragraph in English. Then list each "
    "change with the exact original words, the exact revised words, and why, in Vietnamese, "
    "simply. Return JSON only."
)


def prompt(task_prompt: str, paragraph: str, target_band: float) -> str:
    return (
        f"Task 2 question:\n{task_prompt}\n\nTarget band: {target_band:.1f}\n\n"
        f"Paragraph to rewrite:\n{paragraph}"
    )


def target_band(score: dict[str, Any] | None) -> float:
    """Half a band above the top of the estimated range; 6.5 without a range."""
    if not score or score.get("uncertain"):
        return DEFAULT_TARGET
    return min(BAND_MAX, float(score["band_high"]) + 0.5)


def split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if words(p)]


@dataclass(frozen=True)
class Change:
    original: str
    revised: str
    why_vi: str | None = None


def _norm(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).replace(_CURLY, "'").lower().split())


def _join(tokens: Sequence[str]) -> str:
    return re.sub(r" ([^\w\s])", r"\1", " ".join(tokens))


def diff(original: str, rewrite: str) -> list[Change]:
    """What really changed, word by word (the code's own diff, not the model's list)."""
    a, b = _TOKEN.findall(original), _TOKEN.findall(rewrite)
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if op != "equal":
            out.append(Change(_join(a[i1:i2]), _join(b[j1:j2])))
    return out


def _words(text: str) -> list[str]:
    return _TOKEN.findall(_norm(text))


def _within(part: Sequence[str], whole: Sequence[str]) -> bool:
    """`part` appears as consecutive tokens of `whole` (an empty part is within anything)."""
    n = len(part)
    return n == 0 or any(list(whole[i : i + n]) == list(part) for i in range(len(whole) - n + 1))


def attach_reasons(
    changes: Sequence[Change],
    claimed: Sequence[ChangeOut],
    original: str = "",
    rewrite: str = "",
) -> tuple[list[Change], int]:
    """Give real changes the model's reasons; a reason never stands without a real change.

    A model entry often explains several small edits at once ("is -> are, add 'the'"). When an
    entry's before-text is really in the original and its after-text really in the rewrite, the
    code's changes it covers are shown as one combined change with that reason. Otherwise each
    change gets the reason of the entry whose words contain it, or none. Entries that match no
    real change are dropped and counted.
    """
    orig_words, new_words = _words(original), _words(rewrite)
    # an entry counts only if what it says was there, and what it says is now there, really are
    real = [
        not (original or rewrite)
        or (_within(_words(m.original), orig_words) and _within(_words(m.revised), new_words))
        for m in claimed
    ]
    owner: list[int | None] = []
    for c in changes:
        found = None
        for n, m in enumerate(claimed):
            if real[n] and (c.original or c.revised) \
                    and _within(_words(c.original), _words(m.original)) \
                    and _within(_words(c.revised), _words(m.revised)):  # fmt: skip
                found = n
                break
        owner.append(found)
    out: list[Change] = []
    emitted: set[int] = set()
    for c, k in zip(changes, owner, strict=True):
        if k is None:
            out.append(Change(c.original, c.revised))
            continue
        m = claimed[k]
        if owner.count(k) > 1 and original and rewrite:
            if k not in emitted:  # one combined change, shown once, with its reason
                out.append(Change(m.original.strip(), m.revised.strip(), m.why_vi.strip()))
                emitted.add(k)
            continue
        out.append(Change(c.original, c.revised, m.why_vi.strip() if k not in emitted else None))
        emitted.add(k)
    return out, len(claimed) - len(emitted)


MIN_CONTENT_KEPT = 0.4  # share of the original's content words the rewrite keeps (Bronze, step 2.9)
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*%?")
_NUMBER_TEXT = (
    "one two three four five six seven eight nine ten eleven twelve twenty thirty forty fifty "
    "hundred thousand million billion half quarter percent dozen"
)
_NUMBER_WORDS = frozenset(_NUMBER_TEXT.split())
_NEGATION_TEXT = "not no never nobody nothing none nor neither cannot without"
_NEGATIONS = frozenset(_NEGATION_TEXT.split())
_FUNCTION_TEXT = (
    "a an the and or but if so of to in on at by for with from as is are was were be been being am "
    "this that these those it its they them their there here what which who whom whose when where "
    "why how do does did have has had will would can could should may might must not no very also "
    "i me my we our us you your he she his her him one some any each every all both more most many "
    "much other such than too just only even then however therefore moreover furthermore addition "
    "firstly secondly finally conclusion example instance because while although though whereas "
    "into about over under after before between through during"
)
_FUNCTION = frozenset(_FUNCTION_TEXT.split())


def _stem(word: str) -> str:
    w = word.lower().replace("'", "").replace(_CURLY, "")
    for suffix in ("ing", "ed", "es", "s", "ly"):
        if len(w) > len(suffix) + 3 and w.endswith(suffix):
            return w[: -len(suffix)]
    return w


def _negations(text: str) -> int:
    toks = [t.lower() for t in _TOKEN.findall(unicodedata.normalize("NFC", text))]
    return sum(t in _NEGATIONS or t.endswith(("n't", "n" + _CURLY + "t")) for t in toks)


def _names(text: str) -> set[str]:
    """Capitalised words not at the start of a sentence (names, places, organisations)."""
    out: set[str] = set()
    for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
        toks = [t for t in _TOKEN.findall(sentence) if t[0].isalnum()]
        out |= {t.lower() for t in toks[1:] if t[0].isupper() and t.lower() != "i"}
    return out


def meaning_problems(original: str, rewrite: str) -> list[str]:
    """Why the rewrite may no longer be the learner's paragraph; empty when none is found.

    `new_facts`: a number, number word, or name the original does not have. `negation`: the count
    of negations changed (a statement may have been turned around). `content`: fewer than
    MIN_CONTENT_KEPT of the original's content words (crudely stemmed) are still there.
    """
    a, b = unicodedata.normalize("NFC", original), unicodedata.normalize("NFC", rewrite)
    problems = []
    nums_a = set(_NUMBER.findall(a)) | {w.lower() for w in words(a)} & _NUMBER_WORDS
    nums_b = set(_NUMBER.findall(b)) | {w.lower() for w in words(b)} & _NUMBER_WORDS
    if nums_b - nums_a or _names(b) - _names(a) - {w.lower() for w in words(a)}:
        problems.append("new_facts")
    if _negations(a) != _negations(b):
        problems.append("negation")
    content = {_stem(w) for w in words(a) if w.lower() not in _FUNCTION and len(w) > 2}
    if content:
        kept = content & {_stem(w) for w in words(b)}
        if len(kept) / len(content) < MIN_CONTENT_KEPT:
            problems.append("content")
    return problems


def length_ok(original: str, rewrite: str) -> bool:
    a, b = len(words(original)), len(words(rewrite))
    return a > 0 and LENGTH_RATIO[0] <= b / a <= LENGTH_RATIO[1]


def sentence_with(text: str, phrase: str) -> str | None:
    """The sentence of `text` that contains `phrase` (for a saved phrase's review card)."""
    for s in re.split(r"(?<=[.!?])\s+", text.strip()):
        if _norm(phrase) in _norm(s):
            return s.strip()
    return None


def as_json(changes: Sequence[Change]) -> list[dict[str, Any]]:
    return [asdict(c) for c in changes]
