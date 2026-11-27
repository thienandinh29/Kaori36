"""Words worth keeping from a pasted Reading passage (step 4.3d part 2, "Vocabulary"): pure.

From the passage: the words of the NGSL/NAWL form index above the learner's level (the last level
test's vocabulary level, else B1), and the B1-or-harder words of the sentences that decided the
learner's wrong answers. Words outside the lists are listed too, with no definition. Each word comes
with the passage sentence it appears in; a kept word becomes a saved-phrase card whose gap-fill is
that sentence. No model call: the levels and definitions are the word list's own (draft until a
teacher checks a sample).
"""

import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from app.curriculum.course import LEVELS, Level

WORD = re.compile(r"[A-Za-z]+(?:-[A-Za-z]+)*")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+|\n+")
MIN_LETTERS = 3
MAX_SENTENCE_CHARS = 600  # learner_phrases.sentence
MAX_WORDS = 40
DEFAULT_LEVEL: Level = "B1"
DECIDING_FLOOR: Level = "B1"  # deciding sentences add their words from this level up


@dataclass(frozen=True)
class FormIndex:
    """form (lower case) -> (headword, the headword's level); the lowest level wins."""

    forms: Mapping[str, tuple[str, Level]]

    def get(self, form: str) -> tuple[str, Level] | None:
        return self.forms.get(form.lower())


def build_form_index(forms_yaml: Path) -> FormIndex:
    raw = yaml.load(
        forms_yaml.read_text(encoding="utf-8"), Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    )
    forms: dict[str, tuple[str, Level]] = {}
    for head, entry in raw.items():
        level, *rest = entry
        for f in (str(head), *map(str, rest)):
            old = forms.get(f.lower())
            if old is None or LEVELS.index(level) < LEVELS.index(old[1]):
                forms[f.lower()] = (str(head), level)
    return FormIndex(forms)


@dataclass(frozen=True)
class Gloss:
    definition: str  # English, from the word list
    vi: str | None


@dataclass(frozen=True)
class PassageWord:
    headword: str  # the list's headword, or the form itself when the word is not in the lists
    form: str  # as written in the sentence: the gap-fill's answer
    level: Level | None  # None: not in NGSL/NAWL
    sentence: str
    deciding: bool  # in a sentence that decided a wrong answer
    gloss: Gloss | None

    def to_json(self) -> dict[str, object]:
        return {
            "headword": self.headword, "form": self.form, "level": self.level,
            "sentence": self.sentence, "deciding": self.deciding,
            "definition": self.gloss.definition if self.gloss else None,
            "vi": self.gloss.vi if self.gloss else None,
        }  # fmt: skip


def sentences(passage: str) -> list[str]:
    return [s.strip() for s in SENTENCE_END.split(passage) if s.strip()]


def deciding_sentences(passage: str, quotes: Iterable[str]) -> set[str]:
    """The passage sentences that hold (or overlap) a quoted deciding sentence."""
    flat = [" ".join(q.split()).lower() for q in quotes if q.strip()]
    return {
        s for s in sentences(passage)
        if any(q in " ".join(s.split()).lower() or " ".join(s.split()).lower() in q for q in flat)
    }  # fmt: skip


def _above(level: Level, floor: Level) -> bool:
    return LEVELS.index(level) > LEVELS.index(floor)


def words(
    passage: str,
    learner_level: Level,
    index: FormIndex,
    deciding: set[str] = frozenset(),  # type: ignore[assignment]
    gloss: Callable[[str], Gloss | None] = lambda _: None,
    limit: int = MAX_WORDS,
) -> list[PassageWord]:
    """The words to offer, one per headword at its first useful occurrence.

    Order: words of deciding sentences first, then listed words by level (nearest the learner
    first), then words outside the lists. A capitalised word outside the lists is taken as a name
    and left out; so is a word whose only sentence is longer than a card can hold.
    """
    found: dict[str, PassageWord] = {}
    order: list[str] = []
    for sentence in sentences(passage):
        if len(sentence) > MAX_SENTENCE_CHARS:
            continue
        in_deciding = sentence in deciding
        for match in WORD.finditer(sentence):
            form = match.group(0)
            if len(form) < MIN_LETTERS:
                continue
            entry = index.get(form)
            if entry is None:
                if form[0].isupper() or "-" in form:
                    continue  # a name, or a compound the lists cannot place
                head, level = form.lower(), None
            else:
                head, level = entry
                wanted = _above(level, learner_level) or (
                    in_deciding and not _above(DECIDING_FLOOR, level)
                )
                if not wanted:
                    continue
            old = found.get(head)
            if old is not None and (old.deciding or not in_deciding):
                continue
            if old is None:
                order.append(head)
            found[head] = PassageWord(head, form, level, sentence, in_deciding, gloss(head))

    def rank(head: str) -> tuple[int, int, int]:
        w = found[head]
        level_rank = LEVELS.index(w.level) if w.level else len(LEVELS)
        return (0 if w.deciding else 1, level_rank, order.index(head))

    return [found[h] for h in sorted(order, key=rank)][:limit]


def learner_level(vocab_level: str | None) -> tuple[Level, str]:
    """The level words are offered above, and where it came from (`level_test` or `default`)."""
    if vocab_level in LEVELS:
        return vocab_level, "level_test"
    return DEFAULT_LEVEL, "default"


def pick(offered: Sequence[PassageWord], forms: Iterable[str]) -> list[PassageWord]:
    """The offered words the learner chose, by form (the server never takes a sentence from the
    browser: it recomputes the offer and keeps only what is in it)."""
    wanted = {f.lower() for f in forms}
    return [w for w in offered if w.form.lower() in wanted]
