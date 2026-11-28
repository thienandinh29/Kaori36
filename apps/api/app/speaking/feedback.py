"""The model's written feedback on one Speaking answer, checked by code (step 5.3b).

Spec: specs/speaking/step-5.3b.md.

The model sees only the question and the transcript (never the audio). It writes a few short
points in Vietnamese, each with the words it quotes. Code keeps a point only if its quote is an
exact substring of the transcript (NFC, whitespace and curly quotes folded) of at least three
words, and drops what the recogniser rather than the learner may have caused (a missing -s/-ed
ending) and anything that talks about a band. The points are hints from an AI reading a machine
transcript: never a score, never evidence, never mastery.
"""

import re
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.speaking.language import ending_only
from app.writing.feedback import DATA_RULE, MIN_QUOTE_WORDS, _norm

CONSENT = "speaking-feedback-v1"  # the version of the notice the learner accepts (messages/vi.ts)
MAX_POINTS = 5
MAX_TRIES = 3  # per answer
Area = Literal["answer", "grammar", "vocabulary", "linking"]


class PointOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["strength", "issue"]
    area: Area
    point_vi: str = Field(min_length=10, max_length=500)
    quote: str = Field(min_length=1, max_length=400)
    better: str | None = Field(default=None, max_length=240)


class FeedbackOut(BaseModel):
    """What the model must return (validated by the gateway)."""

    model_config = ConfigDict(extra="forbid")
    points: list[PointOut] = Field(min_length=1, max_length=8)


SYSTEM = (
    "You are an experienced IELTS Speaking teacher giving short feedback to a Vietnamese "
    "learner on ONE spoken answer. You only see a machine transcript of what they said: the "
    "speech recogniser may have mis-heard, added punctuation or capital letters, or fixed a "
    "mistake, so never comment on spelling, capital letters, punctuation, or a missing word "
    "ending such as -s, -es, -ed (it may be pronunciation or the recogniser). You did not "
    "hear the audio: say nothing about pronunciation, pace, pauses or fluency. Give 2 to 5 "
    "points, each a strength or an issue in one area: answer (did it answer the question; a "
    "reason or an example), grammar (a clear grammar error), vocabulary (a word choice or "
    "collocation), linking (how ideas connect). Write each point_vi in Vietnamese, simply "
    "and kindly, and be specific. Each point must have a quote: words copied EXACTLY from "
    "the transcript, at least 3 words, character for character, and the quote must itself "
    "show what the point says. For a grammar or vocabulary issue also give better: a more "
    "natural or correct way to say the same thing, in English, short. Never mention a band "
    "or any score. Never invent words that are not in the transcript. Return JSON only."
) + DATA_RULE


def part_of(question_id: str) -> int:
    """The IELTS part (1 to 3) of an authored question id such as p1-2-1, p2-long, p3-1."""
    m = re.match(r"^p([123])", question_id)
    return int(m.group(1)) if m else 0


def prompt(question: str, part: int, transcript: str) -> str:
    """The user message: the question and the transcript, nothing else."""
    return (
        f"Speaking Part {part} question:\n<<<\n{question}\n>>>\n\n"
        f"Transcript of the learner's answer (machine-made):\n<<<\n{transcript}\n>>>"
    )


_SCORE = re.compile(r"\bband\b|/\s*9\b|\bielts\s*\d", re.IGNORECASE)


@dataclass(frozen=True)
class Checked:
    points: list[dict[str, Any]]
    dropped: int  # points removed by a rule below
    quotes_checked: int


def check(out: FeedbackOut, transcript: str) -> Checked:
    """Keep the points whose quote is in the transcript; drop the rest. At most MAX_POINTS."""
    text = _norm(transcript)
    kept: list[dict[str, Any]] = []
    dropped = 0
    for p in out.points:
        quote = _norm(p.quote)
        better = _norm(p.better) if p.better else None
        ok = (
            len(quote.split()) >= MIN_QUOTE_WORDS
            and quote in text
            and not _SCORE.search(p.point_vi)
            and not (p.kind == "issue" and p.area in ("grammar", "vocabulary") and not better)
            and not (p.kind == "strength" and better)
            and not (better and better.lower() == quote.lower())
            and not (p.kind == "issue" and better and _ending_only_difference(quote, better))
        )
        if not ok:
            dropped += 1
            continue
        kept.append(
            {
                "kind": p.kind,
                "area": p.area,
                "point_vi": " ".join(p.point_vi.split()),
                "quote": quote,
                "better": better,
            }
        )
    return Checked(kept[:MAX_POINTS], dropped + max(len(kept) - MAX_POINTS, 0), len(out.points))


def _ending_only_difference(quote: str, better: str) -> bool:
    """Whether `better` differs from `quote` only by words that gained a -s/-ed ending."""
    a, b = quote.split(), better.split()
    if len(a) != len(b):
        return False
    differing = [(x, y) for x, y in zip(a, b, strict=True) if x.lower() != y.lower()]
    return bool(differing) and all(ending_only(x, y) for x, y in differing)
