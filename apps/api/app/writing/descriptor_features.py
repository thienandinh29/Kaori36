"""Features chosen from the band descriptors, per criterion (specs/writing/step-2.12.md, 2.12b).

Pure functions over what steps 2.1, 2.2 and 2.7 already measure; no model. The evaluation
(`app.evalkit.writing_score`) chooses at most four per criterion on the development folds only;
`CANDIDATES` lists what it may choose from. 2.11b's structure findings are not features of the
served model, for the same reason as their caps (a band never comes from an LLM).

- MTLD (McCarthy and Jarvis, 2010): the mean length of runs of words that keep a type-token ratio
  above 0.72, forwards and backwards; unlike the type-token ratio it does not fall with length.
- Error kinds follow LanguageTool's category, as the result page groups them (step 2.9); the
  model's suggestions (`source == "llm"`) are never counted.
- Word levels come from the NGSL/NAWL form index (`app.lessons.graded.WordIndex`); a word the index
  does not know (a misspelling, a name, a rare word) is counted apart, never as advanced.
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from app.curriculum.course import LEVELS
from app.lessons.graded import WORD, WordIndex, build_index
from app.writing.analysis import linking_found, paragraphs, words
from app.writing.caps import Criterion
from app.writing.grammar import Complexity, GrammarResult, Issue, complexity
from app.writing.guardrails import _STOP, Guard, _stem


def load_word_index(forms_yaml: Path) -> WordIndex:
    """The word index the features use: the NGSL/NAWL forms only. The evaluation and the app must
    build it the same way, or a band fitted on one is applied to the other's numbers."""
    return build_index(forms_yaml)


MTLD_THRESHOLD = 0.72
MIN_MTLD_TOKENS = 50  # below this MTLD is unstable: no value
BASIC_LEVEL = "B1"  # words above this level count as beyond the core

KIND_BY_CATEGORY: Mapping[str, str] = {
    "GRAMMAR": "grammar",
    "CONFUSED_WORDS": "word",
    "TYPOS": "spelling",
    "PUNCTUATION": "punctuation",
    "CASING": "casing",
}


def _factors(tokens: Sequence[str], threshold: float) -> float:
    factors = 0.0
    types: set[str] = set()
    count = 0
    for t in tokens:
        types.add(t)
        count += 1
        if len(types) / count <= threshold:
            factors += 1
            types, count = set(), 0
    if count:  # the partial run at the end counts as the share of a factor it reached
        ttr = len(types) / count
        factors += (1 - ttr) / (1 - threshold)
    return factors


def mtld(tokens: Sequence[str], threshold: float = MTLD_THRESHOLD) -> float | None:
    """Lexical diversity, the mean of the forward and backward passes; None for short texts."""
    low = [t.lower() for t in tokens]
    if len(low) < MIN_MTLD_TOKENS:
        return None
    values = []
    for seq in (low, low[::-1]):
        f = _factors(seq, threshold)
        values.append(len(seq) / f if f > 0 else float(len(seq)))
    return round(sum(values) / 2, 2)


def errors_per_100_by_kind(issues: Sequence[Issue], word_count: int) -> dict[str, float]:
    counts = Counter(KIND_BY_CATEGORY.get(i.category, "other") for i in issues if i.source != "llm")
    n = max(1, word_count)
    return {k: round(100 * v / n, 2) for k, v in sorted(counts.items())}


def error_free_share(sentences: Sequence[str], issues: Sequence[Issue]) -> float | None:
    """The share of sentences with no grammar or word-choice error (spelling and casing aside)."""
    if not sentences:
        return None
    flagged = Counter(
        i.sentence
        for i in issues
        if i.source != "llm" and KIND_BY_CATEGORY.get(i.category) in ("grammar", "word")
    )
    clean = 0
    for s in sentences:
        if flagged[s] > 0:
            flagged[s] -= 1  # each issue marks one copy of a repeated sentence
        else:
            clean += 1
    return round(clean / len(sentences), 3)


@dataclass(frozen=True)
class WordLevels:
    known: int  # tokens the index knows
    beyond_basic: int  # of those, above BASIC_LEVEL
    unknown: int

    @property
    def beyond_basic_share(self) -> float | None:
        return round(self.beyond_basic / self.known, 3) if self.known else None

    @property
    def unknown_share(self) -> float | None:
        total = self.known + self.unknown
        return round(self.unknown / total, 3) if total else None


def word_levels(text: str, index: WordIndex, basic: str = BASIC_LEVEL) -> WordLevels:
    limit = LEVELS.index(basic)
    known = beyond = unknown = 0
    for token in WORD.findall(text):
        level = index.level_of(token)
        if level is None:
            unknown += 1
            continue
        known += 1
        if LEVELS.index(level) > limit:
            beyond += 1
    return WordLevels(known, beyond, unknown)


def prompt_words_per_100(text: str, prompt: str) -> float:
    """How often the essay repeats the prompt's own content words, per 100 words."""
    keys = {_stem(x) for x in words(prompt) if x.lower() not in _STOP and len(x) > 2}
    essay = words(text)
    used = sum(1 for x in essay if _stem(x) in keys)
    return round(100 * used / max(1, len(essay)), 2)


@dataclass(frozen=True)
class Linking:
    groups_used: int
    per_100_words: float
    top_share: float | None  # the most used linking word's share of all linking words


def linking(text: str, groups: Mapping[str, Sequence[str]]) -> Linking:
    found = linking_found(text, groups)
    counts = Counter({w: n for items in found.values() for w, n in items.items()})
    total = sum(counts.values())
    n = max(1, len(words(text)))
    top = round(max(counts.values()) / total, 3) if total else None
    return Linking(len(found), round(100 * total / n, 2), top)


@dataclass(frozen=True)
class DescriptorFeatures:
    # Grammatical Range and Accuracy
    grammar_errors_per_100: float | None  # None: grammar was not checked (no LanguageTool)
    error_free_sentence_share: float | None
    clauses_per_sentence: float
    complex_sentence_share: float
    # Lexical Resource
    mtld: float | None
    beyond_b1_share: float | None
    unknown_word_share: float | None
    spelling_word_errors_per_100: float | None
    prompt_words_per_100: float
    # Coherence and Cohesion
    paragraphs: int
    linking_groups_used: int
    linking_per_100: float
    top_linker_share: float | None
    # Task Response
    own_words: int
    prompt_overlap: float | None

    def as_dict(self) -> dict[str, float | int | None]:
        return asdict(self)


def measure(
    text: str,
    prompt: str,
    *,
    issues: Sequence[Issue],
    sentences: Sequence[str],
    complexity: Complexity,
    index: WordIndex,
    linking_groups: Mapping[str, Sequence[str]],
    own_words: int,
    prompt_overlap: float | None,
) -> DescriptorFeatures:
    n = len(words(text))
    kinds = errors_per_100_by_kind(issues, n)
    levels = word_levels(text, index)
    link = linking(text, linking_groups)
    return DescriptorFeatures(
        grammar_errors_per_100=kinds.get("grammar", 0.0),
        error_free_sentence_share=error_free_share(sentences, issues),
        clauses_per_sentence=complexity.clauses_per_sentence,
        complex_sentence_share=complexity.complex_sentence_share,
        mtld=mtld(words(text)),
        beyond_b1_share=levels.beyond_basic_share,
        unknown_word_share=levels.unknown_share,
        spelling_word_errors_per_100=round(kinds.get("spelling", 0.0) + kinds.get("word", 0.0), 2),
        prompt_words_per_100=prompt_words_per_100(text, prompt),
        paragraphs=len(paragraphs(text)),
        linking_groups_used=link.groups_used,
        linking_per_100=link.per_100_words,
        top_linker_share=link.top_share,
        own_words=own_words,
        prompt_overlap=prompt_overlap,
    )


def measure_essay(
    text: str,
    prompt: str,
    *,
    grammar: GrammarResult | None,
    nlp: Any,
    index: WordIndex,
    linking_groups: Mapping[str, Sequence[str]],
    guard: Guard,
) -> DescriptorFeatures:
    """The features of one essay, the one way the evaluation and the app both compute them.

    Without a grammar analysis (LanguageTool off or down) the three features that count its
    errors are None, never 0: an essay is not error-free because nobody looked.
    """
    parsed = [s for s in nlp(text).sents if words(s.text)]
    f = measure(
        text,
        prompt,
        issues=grammar.issues if grammar else (),
        sentences=list(grammar.sentences) if grammar else [s.text for s in parsed],
        complexity=grammar.complexity if grammar else complexity(parsed),
        index=index,
        linking_groups=linking_groups,
        own_words=guard.own_words,
        prompt_overlap=guard.prompt_overlap,
    )
    if grammar is None:
        return replace(
            f,
            grammar_errors_per_100=None,
            error_free_sentence_share=None,
            spelling_word_errors_per_100=None,
        )
    return f


# What the evaluation may choose from, per criterion (at most four each, on the development folds).
CANDIDATES: Mapping[Criterion, tuple[str, ...]] = {
    "gra": ("grammar_errors_per_100", "error_free_sentence_share", "clauses_per_sentence",
            "complex_sentence_share"),
    "lr": ("mtld", "beyond_b1_share", "unknown_word_share", "spelling_word_errors_per_100",
           "prompt_words_per_100"),
    "cc": ("paragraphs", "linking_groups_used", "linking_per_100", "top_linker_share"),
    "tr": ("own_words", "prompt_overlap"),
}  # fmt: skip
