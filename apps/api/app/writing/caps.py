"""Descriptor caps for Task 2 (specs/writing/step-2.12.md, 2.12a). Pure functions, no model.

A cap is a rule from the public band descriptors: if a finding holds, that criterion's band is at
most `cap`. The rules and the descriptor lines they rest on are in `data/writing/caps.yaml`.

- `fire` says which rules hold for an essay, with their evidence.
- `apply_caps` lowers criterion bands only for rules that are `applied` and found by code; a rule
  found from the model's structure (2.11b) is never applied, because a band never comes from an LLM
  (SPEC.md). It stays a note, shown as "có thể bị giới hạn".
- `cap_effect` is the evaluation's test of a rule: MAE on the essays where it fires, with and
  without the cap. A rule that raises it is switched off, whatever the descriptor says.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.writing.analysis import paragraphs, words
from app.writing.structure import Structure

Criterion = Literal["tr", "cc", "lr", "gra"]
CRITERIA: tuple[Criterion, ...] = ("tr", "cc", "lr", "gra")
FindingId = Literal["no_paragraphing", "part_missing", "position_missing", "position_changed"]
CODE_FINDINGS: frozenset[str] = frozenset({"no_paragraphing"})
MODEL_FINDINGS: frozenset[str] = frozenset({"part_missing", "position_missing", "position_changed"})
# One block of fewer words than this is too short to call "unparagraphed"; the length rules apply.
MIN_WORDS_FOR_PARAGRAPHING = 120

DEFAULT_PATH = Path(__file__).resolve().parents[4] / "data" / "writing" / "caps.yaml"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Scoring(_Model):
    quote: str
    note: str


class Source(_Model):
    title: str
    url: str = Field(pattern=r"^https://")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    read: date
    scoring: Scoring


class CapRule(_Model):
    id: FindingId
    criterion: Criterion
    cap: int = Field(ge=1, le=8)  # criterion bands are whole numbers; a cap of 9 caps nothing
    source: Literal["code", "model"]
    applied: bool
    status: Literal["proposed", "measured"]
    finding: str
    descriptor: tuple[str, ...] = Field(min_length=1)
    reading: str

    @model_validator(mode="after")
    def _consistent(self) -> "CapRule":
        expected = "code" if self.id in CODE_FINDINGS else "model"
        if self.source != expected:
            raise ValueError(f"{self.id}: found by {expected}, not {self.source}")
        if self.source == "model" and self.applied:
            raise ValueError(f"{self.id}: a model finding never changes a band (SPEC.md)")
        if self.applied and self.status != "measured":
            raise ValueError(f"{self.id}: a cap is applied only after it is measured")
        if not any(line.startswith(f"Band {self.cap}:") for line in self.descriptor):
            raise ValueError(f"{self.id}: quote the band {self.cap} line it caps at")
        return self


class CapsFile(_Model):
    source: Source
    rules: tuple[CapRule, ...]

    @model_validator(mode="after")
    def _unique(self) -> "CapsFile":
        ids = [r.id for r in self.rules]
        if len(set(ids)) != len(ids):
            raise ValueError("rule ids must be unique")
        return self


def load_caps(path: Path = DEFAULT_PATH) -> CapsFile:
    return CapsFile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


@dataclass(frozen=True)
class Fired:
    rule: CapRule
    evidence: tuple[str, ...]  # quotes from the essay, or what code counted

    @property
    def applies(self) -> bool:
        return self.rule.applied and self.rule.source == "code"


def code_findings(text: str) -> dict[str, tuple[str, ...]]:
    """What code finds in the essay itself, with its evidence."""
    found: dict[str, tuple[str, ...]] = {}
    n = len(words(text))
    if len(paragraphs(text)) == 1 and n >= MIN_WORDS_FOR_PARAGRAPHING:
        found["no_paragraphing"] = (f"1 paragraph, {n} words",)
    return found


def model_findings(structure: Structure | None) -> dict[str, tuple[str, ...]]:
    """2.11b's issues (not its hints), with their quotes. Never applied to a band."""
    if structure is None:
        return {}
    found: dict[str, tuple[str, ...]] = {}
    for f in structure.findings:
        if f.level == "issue" and f.kind in MODEL_FINDINGS:
            found.setdefault(f.kind, ())
            found[f.kind] = found[f.kind] + tuple(q for q in f.quotes if q not in found[f.kind])
    return found


def fire(rules: Sequence[CapRule], text: str, structure: Structure | None) -> tuple[Fired, ...]:
    found = code_findings(text) | model_findings(structure)
    return tuple(Fired(r, found[r.id]) for r in rules if r.id in found)


def apply_caps(bands: Mapping[Criterion, float], fired: Sequence[Fired]) -> dict[Criterion, float]:
    """Each criterion's band, lowered to the smallest applied cap that fired on it."""
    out = dict(bands)
    for f in fired:
        if f.applies and f.rule.criterion in out:
            out[f.rule.criterion] = min(out[f.rule.criterion], float(f.rule.cap))
    return out


def notes(fired: Sequence[Fired]) -> tuple[Fired, ...]:
    """Rules that held but do not change the band: shown as "có thể bị giới hạn"."""
    return tuple(f for f in fired if not f.applies)


@dataclass(frozen=True)
class CapEffect:
    fired: int  # essays where the rule held
    mae_without: float | None
    mae_with: float | None

    @property
    def helps(self) -> bool | None:
        """None when it never fired; otherwise whether the cap does not make the error worse."""
        if self.mae_without is None or self.mae_with is None:
            return None
        return self.mae_with <= self.mae_without


def cap_effect(
    examiner: Sequence[float], predicted: Sequence[float], fired: Sequence[bool], cap: int
) -> CapEffect:
    """MAE on the essays where a rule fired, with the prediction capped and without."""
    if not len(examiner) == len(predicted) == len(fired):
        raise ValueError("examiner, predicted and fired must be the same length")
    idx = [i for i, f in enumerate(fired) if f]
    if not idx:
        return CapEffect(0, None, None)
    without = sum(abs(examiner[i] - predicted[i]) for i in idx) / len(idx)
    capped = sum(abs(examiner[i] - min(predicted[i], cap)) for i in idx) / len(idx)
    return CapEffect(len(idx), without, capped)
