"""Fitting the band model on descriptor features (specs/writing/step-2.12.md, 2.12b). Pure.

For each model: pick at most four features from the candidates of its criterion by forward
selection, scored by cross-validated MAE inside the training essays only; pick the ridge penalty
the same way; fit; then calibrate the ridge output to the band scale with isotonic regression.
A feature stays out unless it lowers the inner MAE by `MIN_GAIN` bands, so with essays that carry
no signal the model is the training mean (a constant), and the report says which features it kept.

Missing feature values (a text too short for MTLD, no prompt to overlap) are replaced by the
training median. Nothing here sees a test essay.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from statistics import median
from typing import Literal

from app.writing.caps import CRITERIA
from app.writing.descriptor_features import CANDIDATES
from app.writing.descriptor_model import (
    MAX_FEATURES,
    DescriptorModel,
    Fitted,
    Number,
)
from app.writing.scoring import Isotonic, clip_band, fit_isotonic, fit_ridge, kfold, mae

ALPHAS = (0.3, 1.0, 3.0, 10.0, 30.0)
MIN_GAIN = 0.005  # bands of inner-CV MAE a feature must save to be kept
MIN_CRITERIA_ESSAYS = 40  # essays with all four criterion bands, for one model per criterion
MIN_PRESENT = 0.5  # a feature present in fewer essays than this share is not used
INNER_FOLDS = 5

Features = Mapping[str, Number | None]


@dataclass(frozen=True)
class Example:
    features: Features
    band: float  # the overall examiner band
    criteria: Mapping[str, float] | None = None  # tr, cc, lr, gra when the essay carries them


def _present(rows: Sequence[Features], name: str) -> list[float]:
    return [float(v) for r in rows if (v := r.get(name)) is not None]


def _matrix(
    rows: Sequence[Features], names: Sequence[str], medians: Sequence[float]
) -> list[list[float]]:
    return [
        [
            float(v) if (v := r.get(n)) is not None else m
            for n, m in zip(names, medians, strict=True)
        ]
        for r in rows
    ]


def _cv_mae(
    x: Sequence[Sequence[float]], y: Sequence[float], alpha: float, k: int, seed: int
) -> float:
    ids = [str(i) for i in range(len(y))]
    out: dict[int, float] = {}
    for train, val in kfold(ids, k=k, seed=seed):
        t = [int(i) for i in train]
        ridge = fit_ridge([x[i] for i in t], [y[i] for i in t], alpha)
        for i in map(int, val):
            out[i] = clip_band(ridge(x[i]))
    order = range(len(y))
    return mae([y[i] for i in order], [out[i] for i in order])


def fit_model(
    rows: Sequence[Features],
    y: Sequence[float],
    candidates: Sequence[str],
    *,
    max_features: int = MAX_FEATURES,
    k: int = INNER_FOLDS,
    seed: int = 0,
) -> Fitted:
    """One model: selected features, ridge, isotonic. Needs at least four essays."""
    if len(rows) != len(y) or len(rows) < 4:
        raise ValueError("need at least four essays with matching bands")
    k = max(2, min(k, len(rows) // 2))
    usable = [n for n in candidates if len(_present(rows, n)) >= MIN_PRESENT * len(rows)]
    med = {n: median(_present(rows, n)) for n in usable}
    chosen: list[str] = []
    alpha = ALPHAS[1]
    mean = sum(y) / len(y)
    best = mae(y, [mean] * len(y))  # the constant, in-sample: slightly optimistic, a hard bar
    while len(chosen) < max_features:
        step: tuple[float, str, float] | None = None
        for name in (n for n in usable if n not in chosen):
            names = [*chosen, name]
            x = _matrix(rows, names, [med[n] for n in names])
            for a in ALPHAS:
                err = _cv_mae(x, y, a, k, seed)
                if step is None or err < step[0]:
                    step = (err, name, a)
        if step is None or step[0] > best - MIN_GAIN:
            break
        best, alpha = step[0], step[2]
        chosen.append(step[1])
    medians = tuple(med[n] for n in chosen)
    x = _matrix(rows, chosen, medians)
    ridge = fit_ridge(x, y, alpha)
    # No feature earned its place: the constant. (Isotonic on identical inputs would keep the
    # lowest band, not the mean, so the map is written out.)
    iso = fit_isotonic([ridge(r) for r in x], y) if chosen else Isotonic((0.0, 1.0), (mean, mean))
    return Fitted(tuple(chosen), medians, ridge, iso, alpha)


def choose_kind(examples: Sequence[Example]) -> tuple[Literal["criteria", "overall"], str]:
    """Which model to fit, decided once from the whole development set.

    The cross-validation must evaluate that same choice in every fold: a fold has fewer essays, and
    must not quietly fall back to a different kind of model than the one the report is about.
    """
    full = sum(1 for e in examples if e.criteria and all(c in e.criteria for c in CRITERIA))
    if full >= MIN_CRITERIA_ESSAYS:
        return "criteria", f"one model per criterion, {full} essays with all four criterion bands"
    return "overall", (
        f"one model of the overall band: only {full} essays carry all four criterion bands "
        f"(need {MIN_CRITERIA_ESSAYS})"
    )


def fit_descriptor_model(
    examples: Sequence[Example],
    *,
    kind: Literal["criteria", "overall"] | None = None,
    seed: int = 0,
    k: int = INNER_FOLDS,
) -> tuple[DescriptorModel, str]:
    """One model per criterion or one overall (`kind`, else `choose_kind`), and a note on it."""
    chosen, how = choose_kind(examples)
    kind = kind or chosen
    if kind == "criteria":
        full = [e for e in examples if e.criteria and all(c in e.criteria for c in CRITERIA)]
        models: dict[str, Fitted] = {
            c: fit_model(
                [e.features for e in full],
                [e.criteria[c] for e in full if e.criteria],
                CANDIDATES[c],
                seed=seed,
                k=k,
            )
            for c in CRITERIA
        }
        return DescriptorModel("criteria", models), how
    union = tuple(dict.fromkeys(n for c in CRITERIA for n in CANDIDATES[c]))
    model = fit_model(
        [e.features for e in examples], [e.band for e in examples], union, seed=seed, k=k
    )
    return DescriptorModel("overall", {"overall": model}), how
