"""Word lists: authored YAML in `data/vocabulary/` (specs/vocabulary).

A word has a CEFR level and practice material; there is no prerequisite graph for vocabulary.
Everything the items need is checked on load, so a broken entry fails in CI instead of in front of
a learner.
"""

import re
from pathlib import Path
from typing import Annotated, Literal, Self

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.curriculum.course import LEVELS, Level

Pos = Literal["noun", "verb", "adjective", "adverb", "preposition", "conjunction"]
Lemma = Annotated[str, Field(pattern=r"^[a-z][a-z' -]*$", max_length=40)]
Slug = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=40)]
# A phonemic transcription between slashes, as in the word list (no spaces at the ends, no digits).
Ipa = Annotated[str, Field(pattern=r"^/[^/\s0-9][^/0-9]*[^/\s0-9]/$|^/[^/\s0-9]/$", max_length=60)]
BLANK = "___"


def occurrences(word: str, text: str) -> int:
    """How many times `word` occurs in `text` as a whole word, ignoring case."""
    return len(re.findall(rf"(?<![A-Za-z']){re.escape(word)}(?![A-Za-z'])", text, re.IGNORECASE))


def blank_out(word: str, text: str) -> str:
    """`text` with the one whole-word occurrence of `word` replaced by the blank."""
    return re.sub(
        rf"(?<![A-Za-z']){re.escape(word)}(?![A-Za-z'])", BLANK, text, count=1, flags=re.IGNORECASE
    )


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Example(_Model):
    """A sentence containing the target; the learner types the blanked answer."""

    text: str = Field(min_length=3)
    answer: str = Field(min_length=1)
    accepted: tuple[str, ...] = ()  # other correct answers (spelling variants), authored

    @model_validator(mode="after")
    def _answer_once(self) -> Self:
        if occurrences(self.answer, self.text) != 1:
            raise ValueError(f"the answer {self.answer!r} must occur exactly once in {self.text!r}")
        return self


class Collocation(_Model):
    phrase: str = Field(min_length=3)
    blank: str = Field(min_length=1)
    accepted: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _blank_once(self) -> Self:
        if occurrences(self.blank, self.phrase) != 1:
            raise ValueError(f"the blank {self.blank!r} must occur exactly once in {self.phrase!r}")
        return self


class Form(_Model):
    """Word family: the learner sees the base word and types this word's form in the sentence."""

    base: Lemma
    sentence: str = Field(min_length=3)
    answer: str = Field(min_length=1)
    accepted: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _one_blank(self) -> Self:
        if self.sentence.count(BLANK) != 1:
            raise ValueError(f"the sentence needs exactly one {BLANK}: {self.sentence!r}")
        return self


Origin = Literal["authored", "ngsl", "nawl"]


class Word(_Model):
    lemma: Lemma
    pos: Pos
    level: Level
    # authored: written for this project; ngsl/nawl: imported (specs/vocabulary-import), so the
    # level is estimated from frequency and the IPA was kept only where espeak-ng agreed.
    origin: Origin = "authored"
    ipa: Ipa | None = None  # British pronunciation, shown next to the word
    topic: Slug | None = None  # one of the list's topics (specs/vocabulary, topics)
    definition: str = Field(min_length=5)
    vi: str | None = Field(default=None, min_length=1)
    examples: tuple[Example, ...] = Field(min_length=1)
    collocations: tuple[Collocation, ...] = ()
    forms: tuple[Form, ...] = ()

    @model_validator(mode="after")
    def _definition_does_not_give_the_word_away(self) -> Self:
        if occurrences(self.lemma, self.definition):
            raise ValueError(f"{self.lemma}: the definition contains the word itself")
        return self

    @property
    def key(self) -> str:
        return f"{self.lemma}:{self.pos}"


class Topic(_Model):
    slug: Slug
    name_vi: str = Field(min_length=1)


class WordList(_Model):
    slug: Slug
    title_vi: str = Field(min_length=1)
    title_en: str = Field(min_length=1)
    status: Literal["draft", "reviewed"]  # reviewed = the owner has checked every entry
    topics: tuple[Topic, ...] = ()
    words: tuple[Word, ...] = Field(min_length=4)  # four options for a meaning question

    @model_validator(mode="after")
    def _unique(self) -> Self:
        keys = [w.key for w in self.words]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate lemma and part of speech")
        return self

    @model_validator(mode="after")
    def _topics_are_listed(self) -> Self:
        slugs = [t.slug for t in self.topics]
        if len(set(slugs)) != len(slugs):
            raise ValueError("duplicate topic")
        for w in self.words:
            if w.topic is not None and w.topic not in slugs:
                raise ValueError(f"{w.lemma}: topic {w.topic!r} is not in the list's topics")
        return self

    def get(self, key: str) -> Word | None:
        return next((w for w in self.words if w.key == key), None)

    def level_index(self, word: Word) -> int:
        return LEVELS.index(word.level)


def load_wordlist(path: Path, imported_dir: Path | None = None) -> WordList:
    """The list at `path`, plus the imported words of the same slug in `imported_dir` when there.

    One list for the learner (specs/vocabulary-import): the authored entry wins over an imported
    one for the same lemma, the topics are the authored list's, and the result is a draft when
    either part is.
    """
    authored = WordList.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    extra = imported_dir / path.name if imported_dir else None
    if extra is None or not extra.is_file():
        return authored
    imported = WordList.model_validate(yaml.safe_load(extra.read_text(encoding="utf-8")))
    if imported.slug != authored.slug:
        raise ValueError(f"{extra}: slug {imported.slug!r} is not {authored.slug!r}")
    lemmas = {w.lemma for w in authored.words}
    return WordList.model_validate(
        {
            **authored.model_dump(),
            "status": "draft" if "draft" in (authored.status, imported.status) else "reviewed",
            "words": [*authored.words, *(w for w in imported.words if w.lemma not in lemmas)],
        }
    )
