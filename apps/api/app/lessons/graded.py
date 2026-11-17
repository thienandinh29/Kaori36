"""Is the narration graded English? (specs/grammar-lessons, "Hearing and reading")

A word passes when its headword is at or below the lesson's level in the NGSL/NAWL form index
(`data-sa/vocabulary/forms.yaml`), or in the authored word list, or is a number, a name we allow, or
one of the lesson's own grammar terms. Inflected forms are mapped to their headword through the
lists' own form tables ("went" -> go, "children" -> child), so no lemmatizer is needed.
"""

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from app.curriculum.course import LEVELS, Level

WORD = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
CLITICS = ("n't", "'s", "'re", "'ve", "'ll", "'d", "'m")
# Names and words a lesson may always use (the mascot, places, the exam, the languages).
NAMES = frozenset(
    {"sena", "ielts", "english", "vietnamese", "vietnam", "hanoi", "hue", "da", "nang", "saigon"}
    | {"ho", "chi", "minh", "ok", "okay"}
)
LIMITS: Mapping[Level, int] = {"A1": 15, "A2": 15, "B1": 20, "B2": 20, "C1": 20}
SENTENCE = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class WordIndex:
    """form (lower case) -> the lowest level of any headword it belongs to."""

    levels: Mapping[str, Level]

    def level_of(self, word: str) -> Level | None:
        return self.levels.get(word.lower())


def build_index(forms_yaml: Path, authored: Iterable[tuple[str, Level]] = ()) -> WordIndex:
    raw = yaml.load(
        forms_yaml.read_text(encoding="utf-8"), Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    )
    levels: dict[str, Level] = {}

    def add(word: str, level: Level) -> None:
        old = levels.get(word)
        if old is None or LEVELS.index(level) < LEVELS.index(old):
            levels[word] = level

    for head, entry in raw.items():
        level, *forms = entry
        for w in (str(head), *map(str, forms)):
            add(w.lower(), level)
    for lemma, level in authored:
        add(lemma.lower(), level)
    return WordIndex(levels)


def _base(token: str) -> str:
    low = token.lower()
    for clitic in CLITICS:
        if low.endswith(clitic) and len(low) > len(clitic):
            return low[: -len(clitic)] if clitic != "n't" else low[:-3] or low
    return low


def off_level(text: str, level: Level, index: WordIndex, terms: Iterable[str] = ()) -> list[str]:
    """The words of `text` above `level` or unknown, in order, without repeats."""
    words = {t.lower() for term in terms for t in WORD.findall(term)}
    allowed = words | {w + "s" for w in words} | {w + "es" for w in words} | NAMES  # tense, tenses
    out: list[str] = []
    for token in WORD.findall(text):
        word = _base(token)
        if word in allowed or word in out:
            continue
        if word in ("ca", "wo", "sha"):  # can't, won't, shan't after the clitic is removed
            continue
        found = index.level_of(word)
        if found is None or LEVELS.index(found) > LEVELS.index(level):
            out.append(word)
    return out


def too_long(text: str, level: Level) -> list[str]:
    """Sentences longer than the level allows."""
    return [s for s in SENTENCE.split(text.strip()) if len(WORD.findall(s)) > LIMITS[level]]
