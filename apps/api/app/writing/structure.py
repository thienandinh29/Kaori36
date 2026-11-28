"""Task Response and Coherence structure checks (specs/writing/step-2.11.md, 2.11b).

The model only describes the essay: the position stated in the introduction and the conclusion,
each body paragraph's main idea, which parts of the question it answers, and how it develops
its point. Every description must quote the paragraph it describes; code checks each quote and
then decides the findings: no position and a position that flips between introduction and
conclusion (issues), and, as hints only, a part of the question no body paragraph seems to answer
and a body paragraph that only asserts its point. The "answers" lists are the model's own claim
and have no quote to check, so `part_missing` stays a hint until export_review has measured it.
Nothing here is evidence: no finding moves mastery.

A finding is made only from checked descriptions. When a description fails its quote check the
code does not know, and says nothing rather than guess.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.writing.feedback import DATA_RULE, MIN_QUOTE_WORDS, _norm
from app.writing.prompts import Part

MIN_PARAGRAPHS = 3  # an introduction, a body paragraph and a conclusion
MAX_BODY = 10

Stance = Literal["first", "second", "balanced", "none"]
Development = Literal["example", "explanation", "none"]
FLIPS = {("first", "second"), ("second", "first")}


class PositionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stance: Stance
    quote: str | None = Field(default=None, max_length=600)


class BodyOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    paragraph: int = Field(ge=1, le=50)
    main_idea: str = Field(max_length=600)
    answers: list[int] = Field(default_factory=list, max_length=8)
    development: Development
    development_quote: str | None = Field(default=None, max_length=600)


class StructureOut(BaseModel):
    """What the model must return (validated by the gateway)."""

    model_config = ConfigDict(extra="forbid")
    introduction: PositionOut
    conclusion: PositionOut
    body: list[BodyOut] = Field(max_length=MAX_BODY)


SYSTEM = (
    "You describe the structure of an IELTS Writing Task 2 essay. Do not judge or score it: only "
    "describe what is there. The essay is given paragraph by paragraph as [P1], [P2], ...; P1 is "
    "the introduction, the last paragraph is the conclusion, and the others are body paragraphs. "
    "The parts of the question are numbered; a part marked (position) asks for the writer's own "
    "view. For the introduction and for the conclusion, give the writer's position on the "
    "position part as stance: 'first' (agrees, supports the first view, the advantages "
    "outweigh, or positive), 'second' (disagrees, supports the second view, the disadvantages "
    "outweigh, or negative), 'balanced' (partly agrees, or weighs both equally), or 'none' (no "
    "position stated in that paragraph, or the question has no position part); with quote = the "
    "words stating it, copied exactly from that paragraph, or null when stance is 'none'. For "
    "every body paragraph give: paragraph (its number), main_idea (the words that state its "
    "main idea, copied exactly from that paragraph), answers (the numbers of the question parts "
    "it answers; empty if none), development ('example' if it supports its point with a "
    "specific example, 'explanation' if it explains its point with a reason, a consequence or a "
    "contrast, 'none' if it only states its point) and development_quote (the words that give "
    "the example or explanation, copied exactly from that paragraph, or null when development "
    "is 'none'). Every quote is at least 3 words, character for character. Return JSON only."
) + DATA_RULE


def prompt(task_prompt: str, parts: Sequence[Part], paragraphs: Sequence[str]) -> str:
    """The user message: the question, its numbered parts, and the numbered paragraphs."""
    numbered = "\n".join(
        f"{i}. {p.text}{' (position)' if p.position else ''}" for i, p in enumerate(parts, 1)
    )
    essay = "\n\n".join(f"[P{i}] {p}" for i, p in enumerate(paragraphs, 1))
    return (
        f"Task 2 question:\n<<<\n{task_prompt}\n>>>\n\n"
        f"Parts of the question:\n<<<\n{numbered}\n>>>\n\n"
        f"Essay:\n<<<\n{essay}\n>>>"
    )


@dataclass(frozen=True)
class Position:
    stance: str | None  # None: the model's description failed its quote check
    quote: str | None


@dataclass(frozen=True)
class Body:
    paragraph: int
    main_idea: str
    answers: tuple[int, ...]
    development: str | None  # None: claimed an example or explanation but its quote failed


@dataclass(frozen=True)
class Finding:
    kind: Literal["part_missing", "position_missing", "position_changed", "undeveloped"]
    criterion: Literal["tr"]  # Coherence gets the paragraph outline, not a finding yet
    level: Literal["issue", "hint"]
    part: int | None  # 1-based, into `parts`
    paragraph: int | None  # 1-based, into the essay's paragraphs
    quotes: tuple[str, ...]


@dataclass(frozen=True)
class Structure:
    parts: tuple[Part, ...]
    answered: tuple[bool | None, ...]  # per part; None when the code cannot tell
    introduction: Position
    conclusion: Position
    body: tuple[Body, ...]
    body_paragraphs: int
    dropped: int  # body descriptions removed: wrong paragraph, repeated, or quote not found
    findings: tuple[Finding, ...]

    def to_json(self, model: str) -> dict[str, Any]:
        return {
            "parts": [
                {"text": p.text, "position": p.position, "answered": a}
                for p, a in zip(self.parts, self.answered, strict=True)
            ],
            "introduction": {"stance": self.introduction.stance, "quote": self.introduction.quote},
            "conclusion": {"stance": self.conclusion.stance, "quote": self.conclusion.quote},
            "body": [
                {
                    "paragraph": b.paragraph,
                    "main_idea": b.main_idea,
                    "answers": list(b.answers),
                    "development": b.development,
                }
                for b in self.body
            ],
            "body_paragraphs": self.body_paragraphs,
            "dropped": self.dropped,
            "findings": [
                {
                    "kind": f.kind,
                    "criterion": f.criterion,
                    "level": f.level,
                    "part": f.part,
                    "paragraph": f.paragraph,
                    "quotes": list(f.quotes),
                }
                for f in self.findings
            ],
            "model": model,
        }


def _quote_in(quote: str | None, paragraph: str) -> str | None:
    """The quote, normalised, when it is long enough and found in the paragraph."""
    if quote is None:
        return None
    q = _norm(quote).strip(" .,;:")
    if len(re.findall(r"\w+", q)) >= MIN_QUOTE_WORDS and q in _norm(paragraph):
        return q
    return None


def _position(out: PositionOut, paragraph: str) -> Position:
    if out.stance == "none":
        return Position("none", None)
    quote = _quote_in(out.quote, paragraph)
    return Position(out.stance, quote) if quote else Position(None, None)


def verify(paragraphs: Sequence[str], parts: Sequence[Part], out: StructureOut) -> Structure:
    """Check every description against its paragraph, then decide the findings by rule."""
    n = len(paragraphs)
    if n < MIN_PARAGRAPHS:
        raise ValueError("structure checks need an introduction, a body and a conclusion")
    intro = _position(out.introduction, paragraphs[0])
    concl = _position(out.conclusion, paragraphs[-1])
    body: list[Body] = []
    seen: set[int] = set()
    dropped = 0
    for d in out.body:
        if not 2 <= d.paragraph <= n - 1 or d.paragraph in seen:
            dropped += 1
            continue
        text = paragraphs[d.paragraph - 1]
        main = _quote_in(d.main_idea, text)
        if main is None:
            dropped += 1
            continue
        seen.add(d.paragraph)
        answers = tuple(dict.fromkeys(a for a in d.answers if 1 <= a <= len(parts)))
        development: str | None = d.development
        if d.development != "none" and _quote_in(d.development_quote, text) is None:
            development = None
        body.append(Body(d.paragraph, main, answers, development))
    body.sort(key=lambda b: b.paragraph)
    complete = len(seen) == n - 2  # every body paragraph has a checked description

    findings: list[Finding] = []
    answered: list[bool | None] = []
    stated = {p.stance for p in (intro, concl)}
    for i, part in enumerate(parts, 1):
        by_body = any(i in b.answers for b in body)
        if part.position:
            if by_body or stated & {"first", "second", "balanced"}:
                answered.append(True)
            elif complete and stated == {"none"}:
                answered.append(False)
                findings.append(Finding("position_missing", "tr", "issue", i, None, ()))
            else:
                answered.append(None)
        elif by_body:
            answered.append(True)
        elif complete:
            answered.append(False)
            findings.append(Finding("part_missing", "tr", "hint", i, None, ()))
        else:
            answered.append(None)
    if any(p.position for p in parts) and (intro.stance, concl.stance) in FLIPS:
        quotes = tuple(q for q in (intro.quote, concl.quote) if q)
        findings.append(Finding("position_changed", "tr", "issue", None, None, quotes))
    for b in body:
        if b.development == "none":
            findings.append(Finding("undeveloped", "tr", "hint", None, b.paragraph,
                                    (b.main_idea,)))  # fmt: skip
    return Structure(tuple(parts), tuple(answered), intro, concl, tuple(body), n - 2, dropped,
                     tuple(findings))  # fmt: skip
