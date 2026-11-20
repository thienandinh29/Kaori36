"""Checks before any band (specs/writing/step-2.7.md): padding, memorised templates, the prompt.

Pure functions, no model. Scorers reward length and fluent boilerplate: doubling an essay raised
about 80% of essays by a point in one adversarial study, and memorised openers are common in exam
preparation. These checks find text that is not the learner's own answer, so it is not counted
towards the length a band needs, and a band is withheld when much of the essay is such text.

Nothing here judges the learner's English. The thresholds are a first proposal (Bronze), not
measured on examiner-scored essays.
"""

import unicodedata
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from app.writing.analysis import sentences, words

SHINGLE = 8  # a run of 8 words seen before counts as repeated
MIN_SENTENCE_WORDS = 5  # shorter repeated sentences ("I agree.") are ordinary
PADDING_SHARE = 0.15  # more than this share of words repeated or templated: no band
PROMPT_OVERLAP_LOW = 0.15  # fewer prompt words than this used: the essay may be off topic
MIN_PROMPT_WORDS = 5

_STOPWORDS = (
    "a an the and or but if of to in on at by for with from as is are was were be been being "
    "this that these those it its they them their there here what which who whom whose why how "
    "when where do does did done have has had having will would can could should may might must "
    "not no nor so than too very some any each every all both more most other such own same "
    "you your we our us i my me he she his her him one many much few people person "
    "agree disagree extent discuss views opinion give reasons example examples include relevant "
    "knowledge experience write least words essay think believe argue others"
)
_STOP = frozenset(_STOPWORDS.split())


def _norm(text: str) -> str:
    return " ".join(
        w.lower()
        for w in words(
            unicodedata.normalize("NFC", text).replace("\N{RIGHT SINGLE QUOTATION MARK}", "'")
        )
    )


def _stem(word: str) -> str:
    w = word.lower().replace("'", "")
    for suffix in ("ing", "ed", "es", "s"):
        if len(w) > len(suffix) + 3 and w.endswith(suffix):
            return w[: -len(suffix)]
    return w


def load_templates(path: Path) -> tuple[str, ...]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return tuple(_norm(t) for t in raw["templates"])


@dataclass(frozen=True)
class Guard:
    words: int
    repeated_words: int  # words inside a run of 8 seen earlier in the essay
    repeated_sentences: list[str] = field(default_factory=list)
    template_words: int = 0
    templates: list[str] = field(default_factory=list)  # the phrases found, as the list has them
    own_words: int = 0  # words minus repeated and templated ones: what counts towards the length
    padded: bool = False  # more than PADDING_SHARE of the essay: no band
    prompt_overlap: float | None = None  # share of the prompt's content words used
    prompt_words_used: list[str] = field(default_factory=list)
    off_topic: bool = False  # few prompt words used: a warning, never a judgement

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def repeated(text: str) -> tuple[int, list[str]]:
    """Words in 8-word runs that appeared earlier, and sentences said twice or more."""
    w = [x.lower() for x in words(text)]
    seen: set[tuple[str, ...]] = set()
    covered = [False] * len(w)
    for i in range(len(w) - SHINGLE + 1):
        run = tuple(w[i : i + SHINGLE])
        if run in seen:
            covered[i : i + SHINGLE] = [True] * SHINGLE
        else:
            seen.add(run)
    counts = Counter(_norm(s) for s in sentences(text))
    again = [s for s, n in counts.items() if n > 1 and len(s.split()) >= MIN_SENTENCE_WORDS]
    return sum(covered), again


def templates_found(text: str, templates: Sequence[str]) -> tuple[int, list[str]]:
    """Memorised phrases in the essay (word for word, ignoring case and punctuation)."""
    flat = f" {_norm(text)} "
    found = [t for t in templates if f" {t} " in flat]
    return sum(len(t.split()) * flat.count(f" {t} ") for t in found), found


def prompt_overlap(text: str, prompt: str) -> tuple[float | None, list[str]]:
    """The share of the prompt's content words (crudely stemmed) that the essay uses."""
    keys = {_stem(x) for x in words(prompt) if x.lower() not in _STOP and len(x) > 2}
    keys -= {_stem(s) for s in _STOP}
    if len(keys) < MIN_PROMPT_WORDS:
        return None, []
    used = keys & {_stem(x) for x in words(text)}
    return round(len(used) / len(keys), 2), sorted(used)


def check(text: str, prompt: str | None, templates: Sequence[str]) -> Guard:
    n = len(words(text))
    rep, sents = repeated(text)
    tpl, found = templates_found(text, templates)
    own = max(n - rep - tpl, 0)
    overlap, used = prompt_overlap(text, prompt) if prompt else (None, [])
    return Guard(
        words=n,
        repeated_words=rep,
        repeated_sentences=sents,
        template_words=tpl,
        templates=found,
        own_words=own,
        padded=n > 0 and (rep + tpl) / n > PADDING_SHARE,
        prompt_overlap=overlap,
        prompt_words_used=used,
        off_topic=overlap is not None and overlap < PROMPT_OVERLAP_LOW,
    )
