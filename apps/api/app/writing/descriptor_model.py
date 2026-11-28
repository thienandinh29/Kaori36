"""The band model on descriptor features, as the app stores it (specs/writing/step-2.12.md).

Fitting is in `criteria_model.py`; this module is only what `data/writing/scorer.yaml` holds and
what the worker needs to predict: ridge weights and an isotonic map per model, applied to the
features of `descriptor_features.py`. It imports `scoring` only inside functions, because
`scoring.ScorerConfig` embeds `DescriptorsIn`.

- `kind: criteria`: one model per criterion (TR, CC, LR, GRA); the overall band is their plain
  mean, as the official scoring page says ("the score on the task is the average").
- `kind: overall`: one model of the overall band, used while there are too few essays with
  criterion bands (step 2.12, "Data it needs").
A cap (`caps.py`) lowers a criterion's band before the mean, and only a cap that is `applied`.
With `kind: overall` no cap clips anything (a cap acts there as a feature, never as a clip).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    from app.writing.scoring import Isotonic, Ridge

CRITERIA = ("tr", "cc", "lr", "gra")
MAX_FEATURES = 4
Number = float | int


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ModelIn(_Frozen):
    """One fitted model: which features, how a missing one is filled, ridge, then isotonic."""

    names: tuple[str, ...] = Field(max_length=MAX_FEATURES)
    medians: tuple[float, ...]
    means: tuple[float, ...]
    scales: tuple[float, ...]
    weights: tuple[float, ...]
    intercept: float
    xs: tuple[float, ...] = Field(min_length=2)
    ys: tuple[float, ...] = Field(min_length=2)
    alpha: float = Field(gt=0)

    @model_validator(mode="after")
    def _shapes(self) -> "ModelIn":
        n = len(self.names)
        if not all(len(v) == n for v in (self.medians, self.means, self.scales, self.weights)):
            raise ValueError("every per-feature list must have one value per feature name")
        if len(self.xs) != len(self.ys) or list(self.xs) != sorted(self.xs):
            raise ValueError("isotonic points must be sorted and paired")
        if list(self.ys) != sorted(self.ys):
            raise ValueError("an isotonic map must be non-decreasing")
        if any(s <= 0 for s in self.scales):
            raise ValueError("scales must be positive")
        return self

    def build(self) -> "Fitted":
        from app.writing.scoring import Isotonic, Ridge

        return Fitted(
            self.names,
            self.medians,
            Ridge(self.means, self.scales, self.weights, self.intercept),
            Isotonic(self.xs, self.ys),
            self.alpha,
        )


class DescriptorsIn(_Frozen):
    """The `descriptors:` block of scorer.yaml (written by the owner's evaluation)."""

    kind: Literal["criteria", "overall"]
    models: Mapping[str, ModelIn]
    residual_low: float = Field(le=0)  # cross-validated residual quantiles of the served method
    residual_high: float = Field(ge=0)
    essays: int = Field(ge=10)
    fitted_on: str

    @model_validator(mode="after")
    def _kind_matches_models(self) -> "DescriptorsIn":
        expected = set(CRITERIA) if self.kind == "criteria" else {"overall"}
        if set(self.models) != expected:
            raise ValueError(f"kind {self.kind} needs models for exactly {sorted(expected)}")
        return self

    def build(self) -> "DescriptorModel":
        return DescriptorModel(self.kind, {k: m.build() for k, m in self.models.items()})


@dataclass(frozen=True)
class Fitted:
    names: tuple[str, ...]
    medians: tuple[float, ...]
    ridge: "Ridge"
    isotonic: "Isotonic"
    alpha: float

    def predict(self, features: Mapping[str, Number | None]) -> float:
        row = [
            float(v) if (v := features.get(n)) is not None else m
            for n, m in zip(self.names, self.medians, strict=True)
        ]
        return self.isotonic(self.ridge(row))

    def to_in(self) -> ModelIn:
        r, iso = self.ridge, self.isotonic
        return ModelIn(
            names=self.names,
            medians=self.medians,
            means=r.means,
            scales=r.scales,
            weights=r.weights,
            intercept=r.intercept,
            xs=iso.xs,
            ys=iso.ys,
            alpha=self.alpha,
        )


@dataclass(frozen=True)
class Prediction:
    overall: float  # the plain mean of the criteria (kind criteria), or the overall model's output
    criteria: Mapping[str, float] | None  # after any applied caps; None for kind overall


@dataclass(frozen=True)
class DescriptorModel:
    kind: Literal["criteria", "overall"]
    models: Mapping[str, Fitted]

    def predict(
        self,
        features: Mapping[str, Number | None],
        caps: Mapping[str, int] | None = None,
    ) -> Prediction:
        """`caps` maps a criterion to the lowest cap that fired on it (applied rules only)."""
        if self.kind == "overall":
            return Prediction(self.models["overall"].predict(features), None)
        bands = {c: self.models[c].predict(features) for c in CRITERIA}
        for criterion, cap in (caps or {}).items():
            if criterion in bands:
                bands[criterion] = min(bands[criterion], float(cap))
        return Prediction(sum(bands.values()) / len(CRITERIA), bands)

    def to_in(
        self, residual_low: float, residual_high: float, essays: int, fitted_on: str
    ) -> DescriptorsIn:
        return DescriptorsIn(
            kind=self.kind,
            models={k: m.to_in() for k, m in self.models.items()},
            residual_low=residual_low,
            residual_high=residual_high,
            essays=essays,
            fitted_on=fitted_on,
        )


def lowest_caps(fired: Sequence[tuple[str, int]]) -> dict[str, int]:
    """The smallest cap per criterion from (criterion, cap) pairs of rules that apply."""
    out: dict[str, int] = {}
    for criterion, cap in fired:
        out[criterion] = min(cap, out.get(criterion, cap))
    return out
