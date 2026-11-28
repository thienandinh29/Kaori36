"""The band model on descriptor features (specs/writing/step-2.12.md, 2.12b), on synthetic essays
whose bands depend on known features, so what the fit keeps can be checked."""

import random
from typing import Any

import pytest
from pydantic import ValidationError

from app.writing.criteria_model import (
    MIN_CRITERIA_ESSAYS,
    Example,
    choose_kind,
    fit_descriptor_model,
    fit_model,
)
from app.writing.descriptor_model import (
    CRITERIA,
    DescriptorModel,
    DescriptorsIn,
    lowest_caps,
)
from app.writing.scoring import mae


def make(n: int, seed: int = 3, criteria: bool = True, signal: bool = True) -> list[Example]:
    """GRA falls with grammar errors, LR rises with MTLD; TR and CC follow other features."""
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        err, mtld, paras, own = (
            rng.uniform(0, 8),
            rng.uniform(40, 120),
            rng.choice([3, 4, 5]),
            rng.uniform(220, 360),
        )
        noise = {"clauses_per_sentence": rng.uniform(1, 2), "linking_per_100": rng.uniform(0, 6)}
        gra = max(3.0, min(9.0, 8.0 - 0.6 * err + rng.gauss(0, 0.2)))
        lr = max(3.0, min(9.0, 4.0 + 0.04 * (mtld - 40) + rng.gauss(0, 0.2)))
        cc = 5.0 + 0.5 * (paras - 3) + rng.gauss(0, 0.2)
        tr = 5.0 + 0.012 * (own - 220) + rng.gauss(0, 0.2)
        if not signal:
            gra, lr, cc, tr = (rng.choice([5.0, 6.0, 7.0]) for _ in range(4))
        feats = {"grammar_errors_per_100": err, "mtld": mtld, "paragraphs": paras,
                 "own_words": own, **noise}  # fmt: skip
        band = round((gra + lr + cc + tr) / 4 * 2) / 2
        crit = {"tr": tr, "cc": cc, "lr": lr, "gra": gra} if criteria else None
        out.append(Example(feats, band, crit))
    return out


def test_the_fit_keeps_the_features_that_carry_signal_and_beats_the_mean() -> None:
    train, test = make(80), make(40, seed=99)
    model, how = fit_descriptor_model(train)
    assert model.kind == "criteria" and "80 essays" in how
    assert model.models["gra"].names[0] == "grammar_errors_per_100"
    assert "mtld" in model.models["lr"].names and "paragraphs" in model.models["cc"].names
    assert len(model.models["gra"].names) <= 4
    mean = sum(e.band for e in train) / len(train)
    predicted = [model.predict(e.features).overall for e in test]
    assert mae([e.band for e in test], predicted) < 0.6 * mae([e.band for e in test], [mean] * 40)


def test_with_no_signal_the_model_is_the_mean_and_says_so() -> None:
    rows = make(60, signal=False)
    fitted = fit_model(
        [e.features for e in rows], [e.band for e in rows],
        ["clauses_per_sentence", "linking_per_100"],
    )  # fmt: skip
    assert fitted.names == ()  # nothing earned its place
    mean = sum(e.band for e in rows) / len(rows)
    assert fitted.predict({}) == pytest.approx(mean) and fitted.predict({"x": 1}) == fitted.predict(
        {}
    )


def test_too_few_criterion_bands_fall_back_to_one_model_of_the_overall_band() -> None:
    rows = make(MIN_CRITERIA_ESSAYS + 20)
    few = [Example(e.features, e.band, e.criteria if i < MIN_CRITERIA_ESSAYS - 1 else None)
           for i, e in enumerate(rows)]  # fmt: skip
    model, how = fit_descriptor_model(few)
    assert model.kind == "overall" and set(model.models) == {"overall"}
    assert f"{MIN_CRITERIA_ESSAYS - 1} essays carry all four" in how
    p = model.predict(rows[0].features, caps={"cc": 4})
    assert p.criteria is None and p.overall > 0  # no criterion to clip: a cap is not a clip here
    exactly, _ = fit_descriptor_model(rows[:MIN_CRITERIA_ESSAYS])
    assert exactly.kind == "criteria"


def test_a_missing_feature_takes_the_training_median_never_zero() -> None:
    rows = make(60)
    examples = [
        Example({**e.features, "mtld": None} if i % 3 == 0 else e.features, e.band, e.criteria)
        for i, e in enumerate(rows)
    ]
    model, _ = fit_descriptor_model(examples)
    lr = model.models["lr"]
    assert "mtld" in lr.names
    full = {"mtld": lr.medians[lr.names.index("mtld")]}
    assert lr.predict({"mtld": None}) == pytest.approx(lr.predict(full))
    assert lr.predict({"mtld": None}) != lr.predict({"mtld": 0.0})


def test_a_feature_missing_from_most_essays_is_not_used() -> None:
    rows = make(60)
    sparse = [
        {**e.features, "linking_per_100": 3.0 if i < 10 else None} for i, e in enumerate(rows)
    ]
    fitted = fit_model(sparse, [e.band for e in rows], ["linking_per_100", "paragraphs"])
    assert "linking_per_100" not in fitted.names


def test_the_overall_is_the_plain_mean_and_an_applied_cap_lowers_one_criterion_first() -> None:
    model, _ = fit_descriptor_model(make(80))
    feats = make(1, seed=7)[0].features
    plain = model.predict(feats)
    assert plain.criteria is not None
    assert plain.overall == pytest.approx(sum(plain.criteria.values()) / 4)
    capped = model.predict(feats, caps={"cc": 4})
    assert capped.criteria is not None and capped.criteria["cc"] == min(plain.criteria["cc"], 4.0)
    assert capped.overall <= plain.overall and capped.criteria["tr"] == plain.criteria["tr"]
    assert model.predict(feats, caps={"cc": 9}).overall == pytest.approx(
        plain.overall
    )  # never raises


def test_the_stored_form_round_trips_and_predicts_the_same() -> None:
    model, _ = fit_descriptor_model(make(80))
    stored = model.to_in(-0.5, 0.5, 80, "test")
    again = DescriptorsIn.model_validate(stored.model_dump()).build()
    feats = make(1, seed=11)[0].features
    assert again.predict(feats).overall == pytest.approx(model.predict(feats).overall)
    assert isinstance(again, DescriptorModel) and again.kind == "criteria"


def test_the_stored_form_refuses_what_the_app_could_not_use() -> None:
    model, _ = fit_descriptor_model(make(80))
    good: dict[str, Any] = model.to_in(-0.5, 0.5, 80, "x").model_dump()
    with pytest.raises(ValidationError, match="exactly"):
        DescriptorsIn.model_validate(good | {"kind": "overall"})
    cc = good["models"]["cc"]
    falling = tuple(9.0 - i for i in range(len(cc["xs"])))  # paired with xs, but decreasing
    broken = {**good, "models": {**good["models"], "cc": {**cc, "ys": falling}}}
    with pytest.raises(ValidationError, match="non-decreasing"):
        DescriptorsIn.model_validate(broken)
    models = good["models"]
    five = {
        **models["gra"],
        "names": ("a",) * 5,
        "medians": (0.0,) * 5,
        "means": (0.0,) * 5,
        "scales": (1.0,) * 5,
        "weights": (0.0,) * 5,
    }
    with pytest.raises(ValidationError):
        DescriptorsIn.model_validate({**good, "models": {**models, "gra": five}})
    zero = {**models["tr"], "scales": (0.0,) * len(models["tr"]["names"])}
    with pytest.raises(ValidationError, match="positive"):
        DescriptorsIn.model_validate({**good, "models": {**models, "tr": zero}})
    assert set(good["models"]) == set(CRITERIA)


def test_lowest_caps_keeps_the_smallest_per_criterion() -> None:
    assert lowest_caps([("cc", 5), ("tr", 6), ("cc", 4)]) == {"cc": 4, "tr": 6}
    assert lowest_caps([]) == {}


def test_a_fit_needs_at_least_four_matching_essays() -> None:
    with pytest.raises(ValueError, match="at least four"):
        fit_model([{"a": 1.0}] * 3, [5.0] * 3, ["a"])
    with pytest.raises(ValueError, match="at least four"):
        fit_model([{"a": 1.0}] * 5, [5.0] * 4, ["a"])


def test_a_fold_keeps_the_kind_decided_for_the_whole_set() -> None:
    """49 development essays are enough for a model per criterion, but a fold of 39 is not: the
    fold must still fit what the report is about, not fall back to the overall model."""
    rows = make(MIN_CRITERIA_ESSAYS + 9)
    kind, how = choose_kind(rows)
    assert kind == "criteria" and "49 essays" in how
    fold = fit_descriptor_model(rows[:39], kind=kind)[0]
    assert fold.kind == "criteria" and set(fold.models) == set(CRITERIA)
    assert fit_descriptor_model(rows[:39])[0].kind == "overall"  # left to itself it would differ
    assert fit_descriptor_model(rows, kind="overall")[0].kind == "overall"  # and it can be forced
