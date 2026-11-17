"""A lesson as data (specs/grammar-lessons): scenes of typed actions, played the same way each time.

The action list is closed (OpenMAIC's idea, `docs/research/openmaic-study.md`): a generator, human
or model, can only use these, and each is validated here. Answer keys live in `checkpoints` and are
never sent to the browser.
"""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.curriculum.course import Level
from app.curriculum.figures import Ident


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


Text = Annotated[str, Field(min_length=1, max_length=400)]


class Say(_Model):
    """Sena says one English sentence (heard), with its Vietnamese subtitle."""

    do: Literal["say"]
    en: Text
    vi: Text


class ShowExample(_Model):
    """An example card; `target` is the phrase the lesson is about, highlighted in the subtitle."""

    do: Literal["show_example"]
    id: Ident
    en: Text
    vi: Text
    target: str = Field(min_length=1, max_length=60)


class Spotlight(_Model):
    do: Literal["spotlight"]
    example: Ident


class BoardTable(_Model):
    do: Literal["board_table"]
    rows: tuple[tuple[str, ...], ...] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def _rectangular(self) -> Self:
        widths = {len(r) for r in self.rows}
        if len(widths) != 1 or not 2 <= widths.pop() <= 4:
            raise ValueError("a board table has rows of 2 to 4 cells, all the same width")
        return self


class TimePoint(_Model):
    label: str = Field(min_length=1, max_length=30)
    at: float = Field(ge=-4, le=4)  # 0 is now; negative is the past


class TimeSpan(_Model):
    label: str = Field(min_length=1, max_length=30)
    start: float = Field(ge=-4, le=4)
    end: float = Field(ge=-4, le=4)
    open: bool = False  # still going on (drawn with an arrow past "now")

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.end <= self.start:
            raise ValueError("a time span must end after it starts")
        return self


class BoardTimeline(_Model):
    do: Literal["board_timeline"]
    points: tuple[TimePoint, ...] = ()
    spans: tuple[TimeSpan, ...] = ()

    @model_validator(mode="after")
    def _something(self) -> Self:
        if not self.points and not self.spans:
            raise ValueError("a timeline needs a point or a span")
        return self


class BoardWrite(_Model):
    do: Literal["board_write"]
    text: str = Field(min_length=1, max_length=80)


class BoardClear(_Model):
    do: Literal["board_clear"]


class Ask(_Model):
    do: Literal["ask"]
    checkpoint: Ident


class Pause(_Model):
    """Wait for the learner, e.g. after "What's different?"."""

    do: Literal["pause"]


Action = Annotated[
    Say
    | ShowExample
    | Spotlight
    | BoardTable
    | BoardTimeline
    | BoardWrite
    | BoardClear
    | Ask
    | Pause,
    Field(discriminator="do"),
]
WAITS = frozenset({"say", "ask", "pause"})  # the player waits until these finish


class Choice(_Model):
    text: str = Field(min_length=1, max_length=80)
    correct: bool = False
    misconception: Ident | None = None


class Checkpoint(_Model):
    """A quick check inside the lesson: graded by key, aided (never mastery evidence on its own)."""

    id: Ident
    en: Text  # the question, heard and shown
    vi: Text
    options: tuple[Choice, ...] = Field(min_length=2, max_length=4)
    explain_vi: Text  # why the answer is right, shown after any answer

    @model_validator(mode="after")
    def _one_key(self) -> Self:
        if sum(o.correct for o in self.options) != 1:
            raise ValueError(f"{self.id}: exactly one option must be correct")
        if len({o.text.casefold() for o in self.options}) != len(self.options):
            raise ValueError(f"{self.id}: options must differ")
        return self

    @property
    def key(self) -> str:
        return next(o.text for o in self.options if o.correct)


SceneKind = Literal["engage", "notice", "form", "contrast", "activate", "wrap"]


class Scene(_Model):
    id: Ident
    kind: SceneKind
    cites: tuple[str, ...] = ()  # chunk ids of a verified source (required outside samples)
    misconceptions: tuple[
        Ident, ...
    ] = ()  # this scene explains them: replayed after those mistakes
    actions: tuple[Action, ...] = Field(min_length=1, max_length=20)


class SourceRef(_Model):
    candidate: Ident  # a verified slug in data/sources/english-candidates.yaml
    chapter: str = Field(min_length=1)
    licence: str = Field(min_length=1)


class Lesson(_Model):
    course: Ident
    node: Ident
    level: Level
    status: Literal["sample", "draft", "reviewed"]
    title_en: str = Field(min_length=1)
    title_vi: str = Field(min_length=1)
    terms: tuple[str, ...] = ()  # grammar words the narration may use beyond the word list
    names: tuple[str, ...] = ()  # people and places in the examples (Mai, Nam)
    sources: tuple[SourceRef, ...] = ()
    scenes: tuple[Scene, ...] = Field(min_length=2, max_length=8)
    checkpoints: tuple[Checkpoint, ...] = ()

    @model_validator(mode="after")
    def _ids(self) -> Self:
        scenes = [s.id for s in self.scenes]
        if len(set(scenes)) != len(scenes):
            raise ValueError("scene ids must be unique")
        examples = [a.id for s in self.scenes for a in s.actions if isinstance(a, ShowExample)]
        if len(set(examples)) != len(examples):
            raise ValueError("example ids must be unique")
        checks = [c.id for c in self.checkpoints]
        if len(set(checks)) != len(checks):
            raise ValueError("checkpoint ids must be unique")
        return self

    def examples(self) -> dict[str, ShowExample]:
        return {a.id: a for s in self.scenes for a in s.actions if isinstance(a, ShowExample)}

    def checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        return next((c for c in self.checkpoints if c.id == checkpoint_id), None)

    @property
    def noncommercial(self) -> bool:
        """NonCommercial when any cited source is (specs/grammar-lessons)."""
        return any("NC" in s.licence.upper().replace("-", " ").split() for s in self.sources)
