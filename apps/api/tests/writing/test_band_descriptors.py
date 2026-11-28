"""The band from descriptor features, served (specs/writing/step-2.12.md, step 4).

Nothing is served unless scorer.yaml's `method` says so; the committed file says "scorer" and has no
calibration, so no learner sees a different band because of this code."""

import random
import shutil
from pathlib import Path
from uuid import UUID

import pytest

from app.services.writing import (
    BAND_DOWN_VI,
    BAND_HIDDEN_VI,
    BAND_MISMATCH_VI,
    BAND_NO_GRAMMAR_VI,
    BAND_OFF_VI,
    BAND_REASONS_VI,
    GrammarStep,
    _descriptor_features,
    band_for,
    load_grammar_step,
)
from app.writing import guardrails
from app.writing.caps import load_caps
from app.writing.criteria_model import Example, fit_descriptor_model
from app.writing.descriptor_features import DescriptorFeatures, load_word_index
from app.writing.grammar import Complexity, GrammarResult
from app.writing.scoring import CalibrationIn, ScorerConfig, load_scorer_config
from tests.writing.test_band import CALIBRATED, CONFIG, OTHER, OWNER, FakeScorer

ROOT = Path(__file__).resolve().parents[4]
RULES = load_caps().rules


def features(**over: float | None) -> DescriptorFeatures:
    base: dict[str, float | int | None] = {
        "grammar_errors_per_100": 2.0, "error_free_sentence_share": 0.8,
        "clauses_per_sentence": 1.5, "complex_sentence_share": 0.4, "mtld": 80.0,
        "beyond_b1_share": 0.1, "unknown_word_share": 0.03, "spelling_word_errors_per_100": 0.5,
        "prompt_words_per_100": 6.0, "paragraphs": 4, "linking_groups_used": 5,
        "linking_per_100": 3.0, "top_linker_share": 0.2, "own_words": 260, "prompt_overlap": 0.7,
    }  # fmt: skip
    return DescriptorFeatures(**(base | over))  # type: ignore[arg-type]


def fitted() -> ScorerConfig:
    """A config whose descriptor model was fitted on synthetic essays (paragraphs drive CC)."""
    rng = random.Random(2)
    examples = []
    for _ in range(60):
        err, paras = rng.uniform(0, 8), rng.choice([1, 3, 4, 5])
        crit = {
            "gra": 8.0 - 0.5 * err + rng.gauss(0, 0.2),
            "cc": 4.0 + 0.5 * (paras - 1) + rng.gauss(0, 0.2),
            "lr": 6.0 + rng.gauss(0, 0.3),
            "tr": 6.0 + rng.gauss(0, 0.3),
        }
        feats = {"grammar_errors_per_100": err, "paragraphs": paras, "mtld": 80.0}
        examples.append(Example(feats, round(sum(crit.values()) / 2) / 2, crit))
    model, how = fit_descriptor_model(examples)
    block = model.to_in(-0.5, 0.5, 60, how)
    return CALIBRATED.model_copy(update={"method": "descriptors", "descriptors": block})


DESCRIPTORS = fitted()
BLEND = DESCRIPTORS.model_copy(update={"method": "blend"})
ONE_BLOCK = " ".join(["learning"] * 200)
PARAGRAPHED = "\n\n".join([" ".join(["learning"] * 50) for _ in range(4)])


def step(scorer: FakeScorer | None, config: ScorerConfig, rules: tuple = ()) -> GrammarStep:  # type: ignore[type-arg]
    return GrammarStep(
        nlp=None, annotator=None, error_map=None, course=None, client=None,  # type: ignore[arg-type]
        draft_learners=frozenset({OWNER}), scorer=scorer, scorer_config=config,
        cap_rules=rules,
    )  # fmt: skip


def test_the_descriptor_band_is_a_range_and_needs_no_scoring_service() -> None:
    score, why = band_for("essay", 2, 260, OWNER, step(None, DESCRIPTORS), features())
    assert why is None and score is not None
    assert score["band_low"] <= score["band_high"] and score["uncertain"] is False
    assert (score["model"], score["status"], score["truncated"]) == ("descriptors", "draft", False)
    assert "per criterion" in str(score["revision"])  # what it was fitted on
    assert "band" not in score  # never a point


def test_more_errors_give_a_lower_band() -> None:
    clean, _ = band_for(
        "e", 2, 260, OWNER, step(None, DESCRIPTORS), features(grammar_errors_per_100=0.5)
    )
    messy, _ = band_for(
        "e", 2, 260, OWNER, step(None, DESCRIPTORS), features(grammar_errors_per_100=7.0)
    )
    assert clean is not None and messy is not None
    assert messy["band_high"] < clean["band_high"]


@pytest.mark.parametrize(
    ("task", "words", "learner", "feats", "why"),
    [
        (1, 260, OWNER, features(), BAND_REASONS_VI["task1"]),
        (2, 149, OWNER, features(), BAND_REASONS_VI["too_short"]),
        (2, 260, OTHER, features(), BAND_HIDDEN_VI),  # draft: the owner only
        (2, 260, OWNER, None, BAND_NO_GRAMMAR_VI),  # grammar not checked: no error-free guess
    ],
)
def test_when_there_is_no_descriptor_band_the_learner_is_told_why(
    task: int, words: int, learner: UUID, feats: DescriptorFeatures | None, why: str
) -> None:
    assert band_for("e", task, words, learner, step(None, DESCRIPTORS), feats) == (None, why)


def test_a_validated_descriptor_band_is_shown_to_everyone() -> None:
    validated = DESCRIPTORS.model_copy(update={"status": "validated"})
    score, _ = band_for("e", 2, 260, OTHER, step(None, validated), features())
    assert score is not None and score["status"] == "validated"


def test_the_blend_is_the_mean_of_the_scorer_and_the_descriptor_model() -> None:
    own, _ = band_for("e", 2, 260, OWNER, step(None, DESCRIPTORS), features())
    scorer_only = CALIBRATED  # raw 4.0 -> 6.0 on its calibration (test_band)
    scored, _ = band_for("e", 2, 260, OWNER, step(FakeScorer(4.0), scorer_only))
    mixed, why = band_for("e", 2, 260, OWNER, step(FakeScorer(4.0), BLEND), features())
    assert why is None and own is not None and scored is not None and mixed is not None
    assert mixed["model"] == "blend"
    mid_own = (own["band_low"] + own["band_high"]) / 2
    mid_scored = (scored["band_low"] + scored["band_high"]) / 2
    assert min(mid_own, mid_scored) - 1.0 <= (mixed["band_low"] + mixed["band_high"]) / 2
    assert (mixed["band_low"] + mixed["band_high"]) / 2 <= max(mid_own, mid_scored) + 1.0


@pytest.mark.parametrize(
    ("scorer", "why"),
    [
        (None, BAND_OFF_VI),
        (FakeScorer(down=True), BAND_DOWN_VI),
        (FakeScorer(revision="f" * 40), BAND_MISMATCH_VI),
    ],
)
def test_the_blend_needs_the_pinned_scorer_and_says_when_it_is_missing(
    scorer: FakeScorer | None, why: str
) -> None:
    assert band_for("e", 2, 260, OWNER, step(scorer, BLEND), features()) == (None, why)


def test_the_scorer_method_is_unchanged_by_any_of_this() -> None:
    assert CONFIG.method == "scorer" and CALIBRATED.method == "scorer"
    score, why = band_for("e", 2, 260, OWNER, step(FakeScorer(4.0), CALIBRATED), features())
    assert why is None and score is not None and score["model"] == CONFIG.model
    assert band_for("e", 2, 260, OWNER, step(None, CALIBRATED)) == (None, BAND_OFF_VI)


def test_an_applied_cap_lowers_the_criterion_before_the_mean_and_a_proposed_one_does_not() -> None:
    proposed = step(None, DESCRIPTORS, RULES)
    para = next(r for r in RULES if r.id == "no_paragraphing")
    # A cap of 3 (a stand-in: the real cap is 5) is far enough below a five-paragraph CC that the
    # range must move; the real value is measured before it is applied.
    strict = para.model_copy(update={"applied": True, "status": "measured", "cap": 3})
    applied = step(None, DESCRIPTORS, (strict,))
    rich = features(paragraphs=5)  # the model expects a high CC for five paragraphs
    base, _ = band_for(ONE_BLOCK, 2, 260, OWNER, proposed, rich)
    capped, _ = band_for(ONE_BLOCK, 2, 260, OWNER, applied, rich)
    same, _ = band_for(PARAGRAPHED, 2, 260, OWNER, applied, rich)  # not one block: nothing fires
    assert base is not None and capped is not None and same is not None
    assert capped["band_high"] < base["band_high"] and capped["band_low"] < base["band_low"]
    assert (same["band_low"], same["band_high"]) == (base["band_low"], base["band_high"])


# --- the features the worker computes ---------------------------------------------------------


def test_features_are_computed_only_when_a_descriptor_method_serves_a_task_2_with_grammar() -> None:
    nlp = pytest.importorskip("spacy").load("en_core_web_sm")
    index = load_word_index(ROOT / "data-sa" / "vocabulary" / "forms.yaml")
    base = step(None, DESCRIPTORS)
    base.nlp, base.word_index = nlp, index
    text = "Learning is good. It helps people.\n\nStudents learn many things at school."
    sentences = ("Learning is good.", "It helps people.", "Students learn many things at school.")
    grammar = GrammarResult((), sentences, Complexity(3, 1.0, 0.0))
    g = guardrails.check(text, "Is learning good?", ())
    wd = ROOT / "data" / "writing"
    got = _descriptor_features(text, None, 2, grammar, g, base, wd)
    assert got is not None and got.paragraphs == 2 and got.grammar_errors_per_100 == 0.0
    assert got.error_free_sentence_share == 1.0
    assert _descriptor_features(text, None, 1, grammar, g, base, wd) is None  # Task 1
    assert _descriptor_features(text, None, 2, None, g, base, wd) is None  # no grammar analysis
    plain = step(None, CONFIG)
    plain.nlp, plain.word_index = nlp, index
    assert _descriptor_features(text, None, 2, grammar, g, plain, wd) is None  # method: scorer


# --- loading the worker's step ----------------------------------------------------------------


def test_a_method_that_needs_the_word_index_stops_the_worker_at_start(tmp_path: Path) -> None:
    pytest.importorskip("spacy")
    writing = tmp_path / "writing"
    shutil.copytree(ROOT / "data" / "writing", writing)
    scorer = writing / "scorer.yaml"
    from app.evalkit import writing_score as ws

    ws.write_calibration(
        CalibrationIn(xs=(3.0, 5.0), ys=(4.0, 8.0), residual_low=-0.4, residual_high=0.6,
                      essays=70, fitted_on="synthetic"), scorer)  # fmt: skip
    ws.write_descriptors(DESCRIPTORS.descriptors, "descriptors", scorer)  # type: ignore[arg-type]
    assert load_scorer_config(scorer).method == "descriptors"
    courses = ROOT / "data" / "courses"
    with pytest.raises(ValueError, match="needs"):
        load_grammar_step(writing, courses, "")
    with pytest.raises(ValueError, match="needs"):
        load_grammar_step(writing, courses, "", forms_yaml=tmp_path / "missing.yaml")
    ok = load_grammar_step(writing, courses, "", forms_yaml=ROOT / "data-sa/vocabulary/forms.yaml")
    assert ok.word_index is not None and {r.id for r in ok.cap_rules} >= {"no_paragraphing"}
    plain = load_grammar_step(ROOT / "data" / "writing", courses, "")  # the committed file
    assert plain.word_index is None and plain.cap_rules == ()
