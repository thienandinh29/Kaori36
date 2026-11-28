"""Grammar and vocabulary checks on a Speaking transcript (specs/speaking/step-5.3.md, 5.3a).

Code only, on our own machines: the Writing pipeline's tools run on the transcript, so nothing is
sent to a model provider. Grammar flags on speech are hints, never evidence: spoken grammar is not
written grammar, and the recogniser may have mis-heard or "corrected" the learner. A suggestion
that only adds an ending (-s, -es, -ed, -d) is kept apart as a possibly missing ending, never as a
grammar error: it may be pronunciation, grammar or the recogniser.
"""

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from spacy.lang.en.stop_words import STOP_WORDS

from app.lessons.graded import WordIndex
from app.speaking.measures import SHORT_ANSWER_SECONDS, is_filler
from app.writing import guardrails
from app.writing.analysis import words as split_words
from app.writing.descriptor_features import mtld, word_levels
from app.writing.error_map import ErrorMap
from app.writing.grammar import Annotator, Issue, analyse_grammar
from app.writing.languagetool import Match

HINT_CATEGORIES = {
    "GRAMMAR": "grammar",
    "CONFUSED_WORDS": "word",
}  # spelling, casing, punctuation: no
ENDINGS = ("s", "es", "ed", "d")
MAX_HINTS = 10
TOP_REPEATED = 5
MIN_REPEATS = 3


def ending_only(original: str, suggestion: str | None) -> bool:
    """Whether the suggestion only adds an ending (go -> goes, cat -> cats, walk -> walked)."""
    if not suggestion:
        return False
    a, b = original.strip().lower(), suggestion.strip().lower()
    if not a or not b or " " in a or " " in b or a == b:
        return False
    if b.startswith(a) and b[len(a) :] in ENDINGS:
        return True
    return a.endswith("y") and b in (a[:-1] + "ies", a[:-1] + "ied")


def spans(texts: Sequence[str]) -> list[tuple[int, int]]:
    """Character spans of the words in their space-joined text (how the transcript text is made)."""
    out, pos = [], 0
    for t in texts:
        out.append((pos, pos + len(t)))
        pos += len(t) + 1
    return out


def seconds_of(
    words: Sequence[Mapping[str, Any]], start: int, end: int
) -> tuple[float, float] | None:
    """The seconds covered by characters [start, end) of the transcript, by the words they touch."""
    touched = [
        w
        for w, (a, b) in zip(words, spans([str(w["word"]) for w in words]), strict=True)
        if a < end and start < b
    ]
    if not touched:
        return None
    return round(float(touched[0]["start"]), 2), round(float(touched[-1]["end"]), 2)


def hints(issues: Sequence[Issue], words: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i in sorted(issues, key=lambda i: i.start):
        kind = HINT_CATEGORIES.get(i.category)
        if kind is None:
            continue
        if kind == "grammar" and ending_only(i.text, i.suggestion):
            kind = "ending"
        when = seconds_of(words, i.start, i.end)
        out.append(
            {
                "kind": kind,
                "text": i.text,
                "suggestion": i.suggestion,
                "message_en": i.message_en,
                "rule_id": i.rule_id,
                "errant_type": i.errant_type,
                "start_s": None if when is None else when[0],
                "end_s": None if when is None else when[1],
            }
        )
    return out[:MAX_HINTS]


def vocabulary(text: str, index: WordIndex) -> dict[str, Any]:
    """Numbers about the words, fillers left out: diversity, share above B1, unknown, repeats."""
    tokens = [w for w in split_words(text) if not is_filler(w)]
    levels = word_levels(" ".join(tokens), index)
    content = Counter(w.lower() for w in tokens if w.lower() not in STOP_WORDS and len(w) > 2)
    return {
        "words": len(tokens),
        "mtld": mtld(tokens),
        "beyond_b1_share": levels.beyond_basic_share,
        "unknown_share": levels.unknown_share,
        "repeated": [{"word": w, "count": n} for w, n in content.most_common() if n >= MIN_REPEATS][
            :TOP_REPEATED
        ],
    }


def guard(text: str, question: str, templates: Sequence[str]) -> dict[str, Any]:
    """The memorised-phrase, repeated-run and question-word checks of Writing step 2.7."""
    g = guardrails.check(text, question, templates)
    return {
        "templates": g.templates,
        "template_words": g.template_words,
        "repeated_words": g.repeated_words,
        "repeated_sentences": g.repeated_sentences,
        "prompt_overlap": g.prompt_overlap,
        "off_topic": g.off_topic,
    }


@dataclass(frozen=True)
class LanguageStep:
    """What the worker needs, loaded once: the Writing grammar step's tools and the word list."""

    nlp: Any
    annotator: Annotator
    error_map: ErrorMap
    index: WordIndex
    templates: tuple[str, ...]
    matches: Callable[[str], list[Match]] | None  # None: LanguageTool is not configured

    def analyse(
        self, transcript: Mapping[str, Any], question: str, measures: Mapping[str, Any]
    ) -> dict[str, Any]:
        text = " ".join(
            str(w["word"]) for w in transcript.get("words", []) if not is_filler(str(w["word"]))
        )
        if not text or measures.get("speaking_seconds", 0) < SHORT_ANSWER_SECONDS:
            return {"skipped": "short"}
        result: dict[str, Any] = {
            "skipped": None,
            "guard": guard(text, question, self.templates),
            "vocabulary": vocabulary(text, self.index),
            "hints": None,
        }
        if self.matches is not None:
            # the matches are of the transcript as the recogniser wrote it, fillers included,
            # so that their offsets are the words' offsets
            full = " ".join(str(w["word"]) for w in transcript["words"])
            found = analyse_grammar(
                full, self.matches(full), self.nlp, self.annotator, self.error_map
            )
            result["hints"] = hints(found.issues, transcript["words"])
        return result


def build_step(settings: Any, grammar: Any) -> LanguageStep:
    """The language step from the Writing grammar step's tools and the word and phrase lists
    (the worker and the SPK-001 feature command build it the same way)."""
    from app.lessons.graded import build_index
    from app.vocabulary.wordlist import load_wordlist
    from app.writing import guardrails

    authored = load_wordlist(settings.vocab_dir / "core-seed.yaml")
    return LanguageStep(
        nlp=grammar.nlp,
        annotator=grammar.annotator,
        error_map=grammar.error_map,
        index=build_index(
            settings.vocab_imported_dir / "forms.yaml",
            [(w.lemma, w.level) for w in authored.words],
        ),
        templates=guardrails.load_templates(settings.writing_dir / "templates.yaml"),
        matches=grammar.client.matches if grammar.client is not None else None,
    )
