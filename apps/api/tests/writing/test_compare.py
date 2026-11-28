"""The five-way comparison and the owner's tools around it (specs/writing/step-2.12.md), on
synthetic essays whose bands depend on known features."""

import json
import random
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError

from app.evalkit import writing_score as ws
from app.evalkit.writing_compare import (
    EssayRow,
    choose_method,
    develop_descriptors,
    held_out_methods,
    range_report,
)
from app.writing.caps import applied_caps, load_caps
from app.writing.descriptor_model import DescriptorsIn
from app.writing.scoring import ScorerConfig, held_out_split, load_scorer_config

ROOT = Path(__file__).resolve().parents[4]
RULES = load_caps().rules


def text_with(paras: int) -> str:
    """150 words in `paras` paragraphs; one paragraph is one block (the no_paragraphing finding)."""
    words = ["learning"] * 150
    size = 150 // paras
    chunks = [" ".join(words[i * size : (i + 1) * size]) + "." for i in range(paras)]
    return "\n\n".join(chunks)


def synthetic(
    n: int = 70, seed: int = 4, criteria: bool = True
) -> tuple[list[ws.Essay], dict[str, float], dict[str, dict[str, Any]], dict[str, list[float]]]:
    rng = random.Random(seed)
    essays, raw, desc, feats = [], {}, {}, {}
    for i in range(n):
        eid = f"e{i:03}"
        err, mtld, paras = rng.uniform(0, 8), rng.uniform(40, 120), rng.choice([1, 3, 4, 5])
        gra = max(3.0, min(9.0, 8.0 - 0.6 * err + rng.gauss(0, 0.2)))
        lr = max(3.0, min(9.0, 4.0 + 0.04 * (mtld - 40) + rng.gauss(0, 0.2)))
        cc = 4.0 + 0.5 * (paras - 1) * (1 if paras > 1 else 0) + rng.gauss(0, 0.2)
        tr = 6.0 + rng.gauss(0, 0.6)
        crit = {
            k: round(v * 2) / 2
            for k, v in zip(("tr", "cc", "lr", "gra"), (tr, cc, lr, gra), strict=True)
        }
        band = round(sum(crit.values()) / 4 * 2) / 2
        essays.append(
            ws.Essay(eid, text_with(paras), band, "Question?", crit if criteria else None)
        )
        raw[eid] = 0.5 * band + rng.gauss(0, 0.2)
        desc[eid] = {"grammar_errors_per_100": err, "mtld": mtld, "paragraphs": paras,
                     "own_words": 150.0, "linking_per_100": rng.uniform(0, 6)}  # fmt: skip
        feats[eid] = [150.0, 15.0, 1.3, 4.0, err]
    return essays, raw, desc, feats


def rows(essays: list[ws.Essay], ids: set[str] | None = None) -> list[EssayRow]:
    return [
        EssayRow(e.id, e.text, e.band, e.criteria) for e in essays if ids is None or e.id in ids
    ]


def base(essays: list[ws.Essay], raw: dict[str, float], feats: dict[str, list[float]]) -> Any:
    test_ids = set(held_out_split([e.id for e in essays], 0.3, seed=1))
    report, cal = ws.develop(essays, raw, feats, test_ids)
    return test_ids, report, cal


def test_the_comparison_adds_criteria_and_blend_next_to_the_three_methods() -> None:
    essays, raw, desc, feats = synthetic()
    test_ids, report, _ = base(essays, raw, feats)
    dev = [e for e in essays if e.id not in test_ids]
    run = develop_descriptors(
        rows(dev), raw, desc, {e.id: 150.0 for e in essays}, RULES, report["methods"], seed=1
    )
    r = run.report
    assert set(r["methods"]) == {"criteria", "blend"} and set(r["ranges"]) == {"criteria", "blend"}
    assert r["descriptor_model"]["kind"] == "criteria" and run.model.kind == "criteria"
    assert r["descriptor_model"]["features"]["gra"][0] == "grammar_errors_per_100"
    assert r["methods"]["criteria"]["qwk"] > r["methods"]["criteria"]["qwk_interval"][0] - 1e-9
    assert r["methods"]["criteria"]["mae"] < report["methods"]["constant"]["mae"]
    assert set(r["per_criterion"]) == {"tr", "cc", "lr", "gra"}
    assert (
        r["per_criterion"]["gra"]["essays"] == len(dev) and r["per_criterion"]["gra"]["qwk"] > 0.7
    )
    assert 0.5 <= r["ranges"]["criteria"]["covers_examiner_band"] <= 1.0
    assert r["choice"]["method"] in ("features", "criteria", "model", "blend")
    assert set(run.residuals) == {"criteria", "blend"}
    with pytest.raises(ValueError, match="too few"):
        develop_descriptors(rows(dev)[:9], raw, desc, {}, RULES, {}, seed=1)


def test_without_enough_criterion_bands_one_model_of_the_overall_band_is_compared() -> None:
    essays, raw, desc, feats = synthetic(n=60, criteria=False)
    test_ids, report, _ = base(essays, raw, feats)
    dev = [e for e in essays if e.id not in test_ids]
    run = develop_descriptors(
        rows(dev), raw, desc, {e.id: 150.0 for e in essays}, RULES, report["methods"], seed=1
    )
    assert run.report["descriptor_model"]["kind"] == "overall" and "per_criterion" not in run.report
    assert "only 0 essays carry all four" in run.report["descriptor_model"]["how"]
    assert run.model.predict(desc[dev[0].id]).criteria is None


def test_each_cap_is_reported_with_what_it_does_to_the_error_where_it_fires() -> None:
    essays, raw, desc, feats = synthetic()
    test_ids, report, _ = base(essays, raw, feats)
    dev = [e for e in essays if e.id not in test_ids]
    caps = {
        c["rule"]: c
        for c in develop_descriptors(
            rows(dev), raw, desc, {e.id: 150.0 for e in essays}, RULES, report["methods"], seed=1
        ).report["caps"]
    }
    para = caps["no_paragraphing"]
    one_block = sum(e.text.count("\n\n") == 0 for e in dev)
    assert para["fired"] == one_block > 0 and para["evaluated"] and para["essays"] == len(dev)
    assert para["mae_without"] is not None and para["helps"] in (True, False)
    for rule in ("part_missing", "position_missing", "position_changed"):
        assert caps[rule]["evaluated"] is False and "model call" in caps[rule]["why"]
    assert not any(c["applied"] for c in caps.values())  # nothing is applied before it is measured


def test_applied_caps_come_from_applied_code_rules_only() -> None:
    rule = RULES[0].model_copy(update={"applied": True, "status": "measured"})
    assert rule.id == "no_paragraphing"
    assert applied_caps([rule], text_with(1)) == {"cc": 5}
    assert applied_caps([rule], text_with(4)) == {}
    assert applied_caps(RULES, text_with(1)) == {}  # proposed rules clip nothing


def test_held_out_methods_fit_on_development_essays_and_never_read_test_bands() -> None:
    essays, raw, desc, feats = synthetic()
    test_ids, _, cal = base(essays, raw, feats)
    dev, test = rows(essays, {e.id for e in essays} - test_ids), rows(essays, test_ids)
    pinned = [cal.build().isotonic(raw[e.id]) for e in test]
    words = [150.0] * len(test)
    got = held_out_methods(dev, test, desc, pinned, words, RULES, seed=1)
    assert set(got) == {"criteria", "blend"} and got["criteria"]["qwk"] > 0.5
    flipped = [EssayRow(e.id, e.text, 9.0 - e.band, e.criteria) for e in test]  # the truth changes
    again = held_out_methods(dev, flipped, desc, pinned, words, RULES, seed=1)
    assert again["criteria"]["qwk"] != got["criteria"]["qwk"]  # scored against different bands
    altered = {**desc, **{e.id: {**desc[e.id], "mtld": 0.0} for e in test}}
    assert held_out_methods(dev, test, altered, pinned, words, RULES, seed=1) != got  # inputs count


def test_the_simplest_servable_method_wins_when_the_intervals_overlap() -> None:
    def m(q: float, low: float, high: float) -> dict[str, Any]:
        return {"qwk": q, "qwk_interval": [low, high]}

    pick = choose_method({
        "features": m(0.50, 0.30, 0.62), "criteria": m(0.66, 0.50, 0.80),
        "model": m(0.74, 0.60, 0.86), "blend": m(0.80, 0.66, 0.90),
    })  # fmt: skip
    assert pick["method"] == "criteria" and pick["best_by_qwk"] == "blend"
    assert pick["overlapping"] == ["criteria", "model", "blend"] and pick["meets_gate"] is False
    assert pick["clearly_beats_feature_baseline"] is False  # 0.50 is inside criteria's interval
    assert "does not clearly beat the feature baseline" in pick["reason"]
    clear = choose_method({"features": m(0.2, 0.1, 0.3), "model": m(0.8, 0.7, 0.9)})
    assert clear["method"] == "model" and clear["meets_gate"] is True
    assert clear["clearly_beats_feature_baseline"] is True and "baseline" not in clear["reason"]


def test_a_baseline_is_never_the_recommendation_however_well_it_scores() -> None:
    def m(q: float, low: float, high: float) -> dict[str, Any]:
        return {"qwk": q, "qwk_interval": [low, high]}

    pick = choose_method({"features": m(0.9, 0.8, 0.95), "criteria": m(0.4, 0.2, 0.6)})
    assert pick["method"] == "criteria" and pick["clearly_beats_feature_baseline"] is False
    assert (
        choose_method({"constant": m(0.0, -0.1, 0.1), "features": m(0.6, 0.4, 0.7)})["method"]
        is None
    )
    assert choose_method({"model": {"qwk": None, "qwk_interval": None}})["method"] is None


def test_range_coverage_is_the_share_of_examiner_bands_inside_the_range() -> None:
    examiner = [5.0, 5.5, 6.0, 6.5, 7.0, 7.5]
    perfect = range_report(examiner, examiner)
    assert perfect["covers_examiner_band"] == 1.0 and perfect["residual_low"] == 0.0
    noisy = range_report(examiner, [5.0, 6.5, 5.0, 7.5, 6.0, 8.5])
    assert 0.5 <= noisy["covers_examiner_band"] <= 1.0 and noisy["residual_low"] < 0


# --- the owner's input file ------------------------------------------------------------------


def line(**over: Any) -> str:
    return json.dumps({"id": "a", "text": "x", "band": 6.5} | over)


def load(tmp_path: Path, *lines: str) -> list[ws.Essay]:
    f = tmp_path / "essays.jsonl"
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ws.load_essays(f)


def test_essays_may_carry_criterion_bands_a_question_and_who_marked_them(tmp_path: Path) -> None:
    plain = load(tmp_path, line())[0]
    assert plain.criteria is None and plain.question == "" and plain.marked_by == ""
    full = load(
        tmp_path,
        line(question="Q?", tr=6, cc=6.5, lr=6, gra=7, marked_by="examiner", source="Cambridge 19"),
    )[0]
    assert full.criteria == {"tr": 6.0, "cc": 6.5, "lr": 6.0, "gra": 7.0}
    assert (full.question, full.marked_by, full.source) == ("Q?", "examiner", "Cambridge 19")


def test_a_site_marking_is_not_an_examiner_band_and_partial_criteria_are_refused(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="needs marked_by"):
        load(tmp_path, line(source="https://example.org/essay"))
    ok = load(tmp_path, line(source="https://example.org/essay", marked_by="trained_rater"))
    assert ok[0].marked_by == "trained_rater"
    with pytest.raises(ValueError, match="marked_by must be one of"):
        load(tmp_path, line(marked_by="the website"))
    with pytest.raises(ValueError, match="all four criterion bands"):
        load(tmp_path, line(tr=6, cc=6))
    with pytest.raises(ValueError, match="not an IELTS band"):
        load(tmp_path, line(tr=6.3, cc=6, lr=6, gra=6))


# --- scorer.yaml -----------------------------------------------------------------------------


def fitted_block(essays: list[ws.Essay], raw: dict[str, float], desc: Any) -> DescriptorsIn:
    from app.writing.criteria_model import Example, fit_descriptor_model

    model, how = fit_descriptor_model([Example(desc[e.id], e.band, e.criteria) for e in essays])
    return model.to_in(-0.5, 0.5, len(essays), how)


def test_the_descriptors_block_and_the_calibration_live_side_by_side_in_scorer_yaml(
    tmp_path: Path,
) -> None:
    essays, raw, desc, feats = synthetic()
    _, _, cal_in = base(essays, raw, feats)
    path = tmp_path / "scorer.yaml"
    shutil.copy(ROOT / "data" / "writing" / "scorer.yaml", path)
    block = fitted_block(essays, raw, desc)
    with pytest.raises(ValidationError, match="needs the pinned scorer's calibration"):
        ws.write_descriptors(block, "blend", path)  # refused before anything is written
    assert "descriptors:" not in path.read_text(encoding="utf-8")
    ws.write_calibration(cal_in, path)
    ws.write_descriptors(block, "descriptors", path)
    loaded = load_scorer_config(path)
    assert loaded.method == "descriptors" and loaded.descriptors is not None
    assert loaded.descriptors.build().kind == "criteria" and loaded.calibration is not None
    ws.write_calibration(cal_in, path)  # rewriting the calibration keeps the descriptors
    again = load_scorer_config(path)
    assert again.descriptors == loaded.descriptors and again.method == "descriptors"
    ws.write_descriptors(block, "blend", path)  # and the other way round, one method line
    text = path.read_text(encoding="utf-8")
    assert text.count("method:") == 1 and text.count("descriptors:") == 1
    assert text.count("calibration:") == 1 and text.startswith("# The band scorer")
    assert load_scorer_config(path).method == "blend"
    with pytest.raises(ValueError, match="descriptors or blend"):
        ws.write_descriptors(block, "scorer", path)


def test_a_method_that_needs_the_descriptors_block_cannot_be_configured_without_it() -> None:
    base_cfg = yaml.safe_load((ROOT / "data" / "writing" / "scorer.yaml").read_text("utf-8"))
    assert ScorerConfig.model_validate(base_cfg).method == "scorer"  # the file as committed
    with pytest.raises(ValidationError, match="needs the descriptors block"):
        ScorerConfig.model_validate({**base_cfg, "method": "descriptors"})


def test_the_committed_scorer_file_still_shows_no_band() -> None:
    cfg = load_scorer_config(ROOT / "data" / "writing" / "scorer.yaml")
    assert cfg.method == "scorer" and cfg.descriptors is None and cfg.calibration is None


def test_final_test_reports_every_method_and_whether_each_meets_the_gate() -> None:
    essays, raw, desc, feats = synthetic(seed=9)
    test_ids = set(held_out_split([e.id for e in essays], 0.3, seed=2))
    _, cal = ws.develop(essays, raw, feats, test_ids)
    config = load_scorer_config(ROOT / "data" / "writing" / "scorer.yaml").model_copy(
        update={"calibration": cal}
    )
    by_text = {e.text + e.id: raw[e.id] for e in essays}
    tagged = [ws.Essay(e.id, e.text + e.id, e.band, "", e.criteria) for e in essays]
    report = ws.final_test(
        tagged, lambda t: by_text.get(t, 3.0), feats, test_ids, config, desc, RULES
    )
    assert set(report["methods"]) == {"model", "constant", "features", "criteria", "blend"}
    assert set(report["gate"]["by_method"]) == set(report["methods"])
    assert (
        report["gate"]["by_method"]["criteria"] is True
        and report["gate"]["by_method"]["constant"] is False
    )
