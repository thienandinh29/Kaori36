"""The examiner test's authored files and timing (specs/speaking/step-5.4a.md). Pure and tested.

One test per YAML file in `data/speaking/tests/`: three Part 1 topics, one cue card with its closing
question, and the Part 3 questions. The questions are written for NodeTrail on common topics, never
copied from past papers or "forecast" lists. Each question gets a stable id and a time limit here,
so the web and the API agree on both.
"""

import hashlib
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, field_validator

# Seconds an answer may run before the examiner moves on. Part 2's two minutes and its one minute
# to prepare are the test's own; the Part 1, closing and Part 3 limits are assumptions (one place).
PART1_SECONDS = 40
PREPARE_SECONDS = 60
LONG_TURN_SECONDS = 120
CLOSING_SECONDS = 30
PART3_SECONDS = 60
GRACE_SECONDS = 5  # the browser stops at the limit; the server allows this much over it
MAX_QUESTION_CHARS = 250  # under the voice's 300-character limit

Part = Literal[1, 2, 3]


def _clean(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split())


def _question(text: str) -> str:
    q = _clean(text)
    if not q.endswith("?"):
        raise ValueError(f"a question ends with '?': {q!r}")
    if len(q) > MAX_QUESTION_CHARS or not q.isascii():
        raise ValueError(f"a question is plain English, at most {MAX_QUESTION_CHARS} chars: {q!r}")
    return q


class Topic(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    topic: str = Field(min_length=3, max_length=60)
    questions: tuple[str, ...] = Field(min_length=3, max_length=5)

    @field_validator("questions")
    @classmethod
    def _questions(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(_question(q) for q in value)


class CueCard(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    task: str = Field(min_length=10, max_length=120)  # "Describe a journey you remember well."
    points: tuple[str, ...] = Field(min_length=3, max_length=4)  # "You should say: ..."
    explain: str = Field(min_length=10, max_length=120)  # "and explain why ..."
    closing: str  # the rounding-off question after the long turn

    @field_validator("closing")
    @classmethod
    def _closing(cls, value: str) -> str:
        return _question(value)


class Discussion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    theme: str = Field(min_length=3, max_length=60)  # "We've been talking about <theme> ..."
    questions: tuple[str, ...] = Field(min_length=4, max_length=6)

    @field_validator("questions")
    @classmethod
    def _questions(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(_question(q) for q in value)


class SpeakingTest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^t\d{2}$")
    title: str = Field(min_length=3, max_length=80)
    status: Literal["draft", "reviewed"]
    author: str = Field(min_length=2, max_length=120)
    part1: tuple[Topic, ...] = Field(min_length=3, max_length=3)
    part2: CueCard
    part3: Discussion


@dataclass(frozen=True)
class Question:
    id: str  # p1-<topic>-<n>, p2-long, p2-closing, p3-<n> (1-based)
    part: Part
    text: str
    seconds: int  # the time allowed for the answer


def questions(test: SpeakingTest) -> list[Question]:
    """Every question of a test in the order the examiner asks them, with its time limit."""
    out = [
        Question(f"p1-{t}-{n}", 1, q, PART1_SECONDS)
        for t, topic in enumerate(test.part1, 1)
        for n, q in enumerate(topic.questions, 1)
    ]
    out.append(Question("p2-long", 2, test.part2.task, LONG_TURN_SECONDS))
    out.append(Question("p2-closing", 2, test.part2.closing, CLOSING_SECONDS))
    out += [Question(f"p3-{n}", 3, q, PART3_SECONDS) for n, q in enumerate(test.part3.questions, 1)]
    return out


def max_answer_seconds(question: Question) -> int:
    return question.seconds + GRACE_SECONDS


@dataclass(frozen=True)
class Loaded:
    test: SpeakingTest
    sha256: str  # of the file's bytes, stored with each sitting


def load_tests(folder: Path) -> dict[str, Loaded]:
    """All tests in the folder, refused at start-up when one is malformed or ids repeat."""
    out: dict[str, Loaded] = {}
    for path in sorted(folder.glob("*.yaml")):
        raw = path.read_bytes()
        test = SpeakingTest.model_validate(yaml.safe_load(raw.decode("utf-8")))
        if not path.stem.startswith(test.id + "-") and path.stem != test.id:
            raise ValueError(f"{path.name}: the file name starts with the test id {test.id}")
        if test.id in out:
            raise ValueError(f"test id {test.id} repeats")
        texts = [q.text.lower() for q in questions(test)]
        if len(set(texts)) != len(texts):
            raise ValueError(f"{test.id}: a question repeats within the test")
        out[test.id] = Loaded(test, hashlib.sha256(raw).hexdigest())
    return out
