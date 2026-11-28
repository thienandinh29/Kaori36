"""One answer's feature row for SPK-001 (pure): numbers from steps 5.2 and 5.3a, nothing new.

Every feature is a number or None (None: not measurable for this answer, for example the grammar
hint rate when LanguageTool was not used, or MTLD under 50 words). Nothing here decides anything;
the owner's model reads these rows.
"""

from collections.abc import Mapping
from typing import Any

FEATURES = (
    "words",
    "recording_seconds",
    "speaking_seconds",
    "share_of_time",
    "speech_rate",
    "articulation_rate",
    "pauses_per_minute",
    "long_pauses_per_minute",
    "pauses_between_per_minute",
    "pauses_inside_per_minute",
    "longest_run_words",
    "longest_run_seconds",
    "fillers_per_100_words",
    "mtld",
    "beyond_b1_share",
    "unknown_share",
    "grammar_hints_per_100_words",
    "endings_per_100_words",
    "template_words_share",
    "repeated_words_share",
)


def _per_minute(count: float | None, seconds: float) -> float | None:
    return None if count is None or seconds <= 0 else round(count / seconds * 60, 2)


def _per_100(count: float | None, words: float) -> float | None:
    return None if count is None or words <= 0 else round(count / words * 100, 2)


def _share(part: float | None, whole: float) -> float | None:
    return None if part is None or whole <= 0 else round(part / whole, 3)


def row(measures: Mapping[str, Any], language: Mapping[str, Any] | None) -> dict[str, float | None]:
    """The features of one answer from its stored `measures` and `language` (5.2 and 5.3a)."""
    words = float(measures.get("words") or 0)
    span = float(measures.get("speaking_seconds") or 0)
    pauses = measures.get("pauses") or {}
    run = measures.get("longest_run") or {}
    lang = language or {}
    checked = lang.get("skipped") is None and "guard" in lang
    vocab = lang.get("vocabulary") or {} if checked else {}
    guard = lang.get("guard") or {} if checked else {}
    hints = lang.get("hints") if checked else None
    return {
        "words": words,
        "recording_seconds": measures.get("recording_seconds"),
        "speaking_seconds": span,
        "share_of_time": measures.get("share_of_time"),
        "speech_rate": measures.get("speech_rate"),
        "articulation_rate": measures.get("articulation_rate"),
        "pauses_per_minute": pauses.get("per_minute"),
        "long_pauses_per_minute": _per_minute(pauses.get("long"), span) if pauses else None,
        "pauses_between_per_minute": _per_minute(pauses.get("between_clauses"), span)
        if pauses
        else None,
        "pauses_inside_per_minute": _per_minute(pauses.get("inside_clause"), span)
        if pauses
        else None,
        "longest_run_words": run.get("words"),
        "longest_run_seconds": run.get("seconds"),
        "fillers_per_100_words": _per_100((measures.get("fillers") or {}).get("count"), words),
        "mtld": vocab.get("mtld"),
        "beyond_b1_share": vocab.get("beyond_b1_share"),
        "unknown_share": vocab.get("unknown_share"),
        # a missing -s/-ed ending is kept apart from grammar, as on the result page
        "grammar_hints_per_100_words": _per_100(
            None if hints is None else sum(1 for h in hints if h["kind"] == "grammar"), words
        ),
        "endings_per_100_words": _per_100(
            None if hints is None else sum(1 for h in hints if h["kind"] == "ending"), words
        ),
        "template_words_share": _share(guard.get("template_words"), words) if guard else None,
        "repeated_words_share": _share(guard.get("repeated_words"), words) if guard else None,
    }
