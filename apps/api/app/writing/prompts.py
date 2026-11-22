"""Writing prompts, authored in `data/writing/prompts.yaml` (specs/writing/step-2.1.md).

A Task 2 prompt names the parts of its question (step 2.11b): what the essay must answer, so code
can check that every part is answered. A `position` part asks for the writer's own view.
"""

from pathlib import Path
from typing import Literal, Self

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.curriculum.course import Level
from app.curriculum.figures import ChartFigure, Ident

PromptType = Literal[
    "opinion", "discussion", "problem-solution", "advantages-disadvantages", "two-part", "chart"
]


MAX_PARTS = 4


class Part(BaseModel):
    """One thing the question asks for, in English, as the learner sees it."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    text: str = Field(min_length=3, max_length=200)
    position: bool = False  # the writer's own view: agree or not, which view, which outweighs


class Prompt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: Ident
    task: Literal[1, 2]
    type: PromptType
    level: Level
    status: Literal["draft", "reviewed"]
    prompt: str = Field(min_length=20, max_length=1000)
    figure: ChartFigure | None = None  # Task 1: the chart the learner describes (step 2.5)
    parts: tuple[Part, ...] = Field(default=(), max_length=MAX_PARTS)  # Task 2 (step 2.11b)

    @model_validator(mode="after")
    def _figure_matches_task(self) -> Self:
        if (self.task == 1) != (self.figure is not None):
            raise ValueError(
                "a Task 1 prompt needs a figure, and a Task 2 prompt must not have one"
            )
        if self.task == 1 and self.parts:
            raise ValueError("a Task 1 prompt has no question parts")
        if len({p.text for p in self.parts}) != len(self.parts):
            raise ValueError("duplicate question part")
        if sum(p.position for p in self.parts) > 1:
            raise ValueError("at most one position part")
        return self


class PromptBank(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    prompts: tuple[Prompt, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique(self) -> Self:
        ids = [p.id for p in self.prompts]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate prompt id")
        if missing := [p.id for p in self.prompts if p.task == 2 and not p.parts]:
            raise ValueError(f"Task 2 prompts need their question parts: {', '.join(missing)}")
        return self

    def get(self, prompt_id: str) -> Prompt | None:
        return next((p for p in self.prompts if p.id == prompt_id), None)


def load_prompts(path: Path) -> PromptBank:
    return PromptBank.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
