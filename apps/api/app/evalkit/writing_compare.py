"""The five-way comparison of band methods (specs/writing/step-2.12.md, "What is compared").

Pure: numbers in, a report out. `app.evalkit.writing_score` gathers the inputs and runs it.

1. constant (the training mean); 2. features (the five-feature ridge of step 2.3); 3. model (the
pinned scorer, calibrated); 4. criteria (the descriptor model, `criteria_model.py`, with the caps
that are applied); 5. blend (the mean of 3 and 4). All are cross-validated on the same folds of
the development essays; the test essays are read only by `held_out_methods`, once, at the end.

`choose_method` is the spec's rule: among methods whose QWK interval overlaps the best method's,
the simplest wins. That is the owner's recommendation to confirm, never an automatic switch.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app.writing.caps import CRITERIA, CapRule, applied_caps, cap_effect, code_findings
from app.writing.criteria_model import Example, choose_kind, fit_descriptor_model
from app.writing.descriptor_model import DescriptorModel, Number
from app.writing.scoring import (
    bootstrap_interval,
    fit_isotonic,
    kfold,
    mae,
    pearson,
    quantile,
    qwk,
    residual_band_range,
    within_half,
)

GATE_QWK = 0.7
# From the simplest to the most complex: what "the simpler model wins" means (spec 2.12).
SIMPLEST_FIRST = ("constant", "features", "criteria", "model", "blend")
SERVABLE = ("criteria", "model", "blend")  # the others are the baselines to beat
Descriptors = Mapping[str, Mapping[str, Number | None]]


@dataclass(frozen=True)
class EssayRow:
    """What the comparison needs of an essay (kept apart from the CLI's Essay)."""

    id: str
    text: str
    band: float
    criteria: Mapping[str, float] | None = None


@dataclass(frozen=True)
class DescriptorRun:
    report: dict[str, Any]
    model: DescriptorModel  # fitted on all the development essays
    how: str
    residuals: dict[str, tuple[float, float]]  # method -> (10th, 90th percentile), cross-validated


def metrics(
    examiner: Sequence[float], predicted: Sequence[float], words: Sequence[float], seed: int
) -> dict[str, Any]:
    return {
        "qwk": qwk(examiner, predicted),
        "qwk_interval": bootstrap_interval(examiner, predicted, qwk, seed=seed),
        "mae": round(mae(examiner, predicted), 4),
        "within_half_band": round(within_half(examiner, predicted), 4),
        "length_correlation": pearson(predicted, words),
    }


def residual_range(examiner: Sequence[float], predicted: Sequence[float]) -> tuple[float, float]:
    res = [b - p for b, p in zip(examiner, predicted, strict=True)]
    return min(0.0, quantile(res, 0.10)), max(0.0, quantile(res, 0.90))


def range_report(examiner: Sequence[float], predicted: Sequence[float]) -> dict[str, Any]:
    """How often the examiner's band falls in the range shown, from the same residuals."""
    low, high = residual_range(examiner, predicted)
    ranges = [residual_band_range(p, low, high) for p in predicted]
    n = len(examiner)
    return {
        "residual_low": round(low, 4),
        "residual_high": round(high, 4),
        "covers_examiner_band": round(
            sum(r.low <= b <= r.high for r, b in zip(ranges, examiner, strict=True)) / n, 4
        ),
        "shown_as_uncertain": round(sum(r.uncertain for r in ranges) / n, 4),
    }


def _overlap(a: Sequence[float], b: Sequence[float]) -> bool:
    return a[0] <= b[1] and b[0] <= a[1]


def choose_method(methods: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """The simplest servable method whose QWK interval overlaps the best one's (owner confirms).

    Only `criteria`, `model` and `blend` can be served; the constant and the feature baseline are
    what they must beat (step 2.3: a scorer that does not clearly beat the baselines is not used),
    so the report says whether each does: its interval lies wholly above the baseline's QWK.
    """
    scored = {
        m: v
        for m, v in methods.items()
        if m in SIMPLEST_FIRST and v.get("qwk") is not None and v.get("qwk_interval")
    }
    servable = {m: v for m, v in scored.items() if m in SERVABLE}
    if not servable:
        return {"method": None, "reason": "no servable method has a QWK with an interval yet"}
    best = max(servable, key=lambda m: servable[m]["qwk"])
    overlapping = [
        m
        for m in SIMPLEST_FIRST
        if m in servable and _overlap(servable[m]["qwk_interval"], servable[best]["qwk_interval"])
    ]
    pick = overlapping[0]
    q = servable[pick]["qwk"]
    baseline = scored.get("features")
    clearly = None if baseline is None else servable[pick]["qwk_interval"][0] > baseline["qwk"]
    notes = []
    if pick != best:
        notes.append("With few essays the intervals are wide, so this favours the simpler method.")
    if clearly is False:
        notes.append(
            "It does not clearly beat the feature baseline (its interval reaches the baseline's "
            "QWK): step 2.3 says the cheaper model is then kept, and this code serves no "
            "baseline, so more essays are the honest answer."
        )
    return {
        "method": pick,
        "best_by_qwk": best,
        "overlapping": overlapping,
        "meets_gate": q >= GATE_QWK,
        "clearly_beats_feature_baseline": clearly,
        "reason": (
            f"{best} has the highest QWK among the servable methods; {', '.join(overlapping)} "
            f"have intervals that overlap its; the simplest is {pick} (QWK {q:.2f}). "
            + " ".join(notes)
        ).strip(),
    }


def _cap_effects(
    rules: Sequence[CapRule],
    rows: Sequence[EssayRow],
    crit_pred: Mapping[str, Mapping[str, float]] | None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rules:
        entry: dict[str, Any] = {"rule": r.id, "criterion": r.criterion, "cap": r.cap,
                                 "source": r.source, "applied": r.applied}  # fmt: skip
        if r.source == "model":
            entry["evaluated"] = False
            entry["why"] = "needs 2.11b's structure of each essay (a model call); never applied"
            out.append(entry)
            continue
        entry["fired"] = sum(r.id in code_findings(e.text) for e in rows)
        sub = [
            e
            for e in rows
            if crit_pred is not None
            and e.criteria
            and r.criterion in e.criteria
            and e.id in crit_pred[r.criterion]
        ]
        if crit_pred is None or not sub:
            entry["evaluated"] = False
            entry["why"] = "no per-criterion model: the cap acts as a feature, never as a clip"
        else:
            eff = cap_effect(
                [e.criteria[r.criterion] for e in sub if e.criteria],
                [crit_pred[r.criterion][e.id] for e in sub],
                [r.id in code_findings(e.text) for e in sub],
                r.cap,
            )
            entry |= {
                "evaluated": True,
                "essays": len(sub),
                "mae_without": eff.mae_without,
                "mae_with": eff.mae_with,
                "helps": eff.helps,
            }
        out.append(entry)
    return out


def develop_descriptors(
    rows: Sequence[EssayRow],
    raw: Mapping[str, float],
    descriptors: Descriptors,
    words: Mapping[str, float],
    rules: Sequence[CapRule],
    base_methods: Mapping[str, Mapping[str, Any]],
    *,
    seed: int,
    k: int = 5,
) -> DescriptorRun:
    """Cross-validate the descriptor model and the blend on the development essays."""
    if len(rows) < 2 * k:
        raise ValueError(f"{len(rows)} development essays: too few for {k}-fold cross-validation")
    by_id = {e.id: e for e in rows}
    ids = [e.id for e in rows]

    def example(i: str) -> Example:
        return Example(descriptors[i], by_id[i].band, by_id[i].criteria)

    kind, _ = choose_kind([example(i) for i in ids])  # once, for every fold and the final fit
    pred: dict[str, dict[str, float]] = {"criteria": {}, "blend": {}}
    crit_pred: dict[str, dict[str, float]] = {c: {} for c in CRITERIA}
    for train, val in kfold(ids, k=k, seed=seed):
        model, _ = fit_descriptor_model([example(i) for i in train], kind=kind, seed=seed)
        iso = fit_isotonic([raw[i] for i in train], [by_id[i].band for i in train])
        for i in val:
            p = model.predict(descriptors[i], applied_caps(rules, by_id[i].text))
            pred["criteria"][i] = p.overall
            pred["blend"][i] = (iso(raw[i]) + p.overall) / 2
            for c, v in (p.criteria or {}).items():
                crit_pred[c][i] = v
    final, how = fit_descriptor_model([example(i) for i in ids], kind=kind, seed=seed)
    examiner = [by_id[i].band for i in ids]
    w = [words[i] for i in ids]
    methods = {m: metrics(examiner, [p[i] for i in ids], w, seed) for m, p in pred.items()}
    report: dict[str, Any] = {
        "methods": methods,
        "ranges": {m: range_report(examiner, [p[i] for i in ids]) for m, p in pred.items()},
        "descriptor_model": {
            "kind": final.kind,
            "how": how,
            "features": {n: list(m.names) for n, m in final.models.items()},
            "ridge_penalty": {n: m.alpha for n, m in final.models.items()},
        },
        "caps": _cap_effects(rules, rows, crit_pred if final.kind == "criteria" else None),
    }
    if final.kind == "criteria":
        report["per_criterion"] = {}
        for c in CRITERIA:
            have = [i for i in ids if by_id[i].criteria and c in (by_id[i].criteria or {})]
            truth = [(by_id[i].criteria or {})[c] for i in have]
            guess = [crit_pred[c][i] for i in have]
            report["per_criterion"][c] = {
                "essays": len(have),
                "qwk": qwk(truth, guess),
                "qwk_interval": bootstrap_interval(truth, guess, qwk, seed=seed),
                "mae": round(mae(truth, guess), 4),
            }
    report["choice"] = choose_method({**base_methods, **methods})
    residuals = {m: residual_range(examiner, [p[i] for i in ids]) for m, p in pred.items()}
    return DescriptorRun(report, final, how, residuals)


def held_out_methods(
    dev: Sequence[EssayRow],
    test: Sequence[EssayRow],
    descriptors: Descriptors,
    pinned: Sequence[float],
    words: Sequence[float],
    rules: Sequence[CapRule],
    *,
    seed: int,
) -> dict[str, dict[str, Any]]:
    """The descriptor model and the blend on the held-out essays; fitted on the development ones.

    `pinned` is the calibrated scorer's prediction for each test essay, in order.
    """
    model, _ = fit_descriptor_model(
        [Example(descriptors[e.id], e.band, e.criteria) for e in dev], seed=seed
    )
    own = [model.predict(descriptors[e.id], applied_caps(rules, e.text)).overall for e in test]
    examiner = [e.band for e in test]
    blend = [(a + b) / 2 for a, b in zip(pinned, own, strict=True)]
    return {
        "criteria": metrics(examiner, own, words, seed),
        "blend": metrics(examiner, blend, words, seed),
    }
