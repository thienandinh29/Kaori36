"""Layer 2 of the two maps: IELTS competencies and links to foundations (specs/two-layer-map).

The file is `data/maps/ielts-competencies.yaml`. Foundations live elsewhere (grammar and
pronunciation courses, vocabulary bands); `app.competencies.check` resolves every link.
"""

from datetime import date
from pathlib import Path
from typing import Literal

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.config import REPO_ROOT

MAP_PATH = REPO_ROOT / "data" / "maps" / "ielts-competencies.yaml"
Skill = Literal["reading", "listening", "writing", "speaking"]
VOCAB_BANDS = ("vocab-a1", "vocab-a2", "vocab-b1", "vocab-b2", "vocab-c1", "vocab-nawl")


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Link(_M):
    node: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    kind: Literal["requires", "helps"]


class Competency(_M):
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    skill: Skill
    name_vi: str = Field(min_length=1)
    name_en: str = Field(min_length=1)
    links: tuple[Link, ...] = Field(min_length=1)

    @property
    def requires(self) -> tuple[str, ...]:
        return tuple(x.node for x in self.links if x.kind == "requires")


class Target(_M):
    overall: float = Field(ge=4.0, le=9.0, multiple_of=0.5)
    exam_date: date


class Balance(_M):
    review_share_max: float = Field(gt=0, le=1)
    foundations_in_a_row_max: int = Field(ge=1)


class CompetencyMap(_M):
    status: Literal["proposed", "reviewed"]
    target: Target
    balance: Balance
    competencies: tuple[Competency, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique(self) -> "CompetencyMap":
        slugs = [c.slug for c in self.competencies]
        if len(set(slugs)) != len(slugs):
            raise ValueError("competency slugs must be unique")
        for c in self.competencies:
            nodes = [x.node for x in c.links]
            if len(set(nodes)) != len(nodes):
                raise ValueError(f"{c.slug}: a foundation is linked twice")
        return self


def load_map(path: Path = MAP_PATH) -> CompetencyMap:
    return CompetencyMap.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
