"""Writing competency observations from code checks (specs/two-layer-map/writing-evidence.md)."""

from pathlib import Path

from app.writing.competency import load_rules, observations

RULES = load_rules(
    Path(__file__).resolve().parents[4] / "data" / "writing" / "competency-rules.yaml"
)
KNOWN = {"the", "city", "is", "big", "and", "people", "like", "it"}


def result(**over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "words": 260, "min_words": 250, "long_enough": True, "paragraphs": 4,
        "avg_sentence_words": 16.0, "linking_groups_used": 3,
        "linking": {"contrast": {"however": 1}, "opinion": {"i believe": 1},
                    "example": {"for instance": 1}},
        "grammar": {"counts": {"VERB:SVA": 2, "DET": 1}},
        "complexity": {"sentences": 16, "clauses_per_sentence": 1.6, "complex_sentence_share": 0.4},
    }  # fmt: skip
    return base | over


def by_rule(obs: list) -> dict[str, bool]:  # type: ignore[type-arg]
    return {f"{o.competency}/{o.rule}": o.passed for o in obs}


def test_a_task2_essay_observes_task2_competencies_only() -> None:
    text = "The city is big and people like it. Sustainability matters enormously."
    got = by_rule(observations(RULES, result(), text, 2, KNOWN))
    assert not any(k.startswith("writing-task1/") for k in got)
    assert got["writing-task2-response/position_stated"] is True
    assert got["writing-coherence/linking_variety"] is True
    assert got["writing-grammar/error_rate"] is True  # 3 errors in 260 words = 1.15 per 100
    assert got["writing-grammar/complex_sentences"] is True
    assert got["writing-lexical/beyond_b1"] is True  # 3 of 12 words outside the known set


def test_failures_and_missing_inputs() -> None:
    weak = result(paragraphs=2, linking_groups_used=1, linking={},
                  grammar={"counts": {"DET": 12}}, avg_sentence_words=34.0)  # fmt: skip
    got = by_rule(observations(RULES, weak, "the city", 2, KNOWN))
    assert got["writing-task2-response/paragraphs"] is False
    assert got["writing-task2-response/position_stated"] is False
    assert got["writing-coherence/sentence_length"] is False
    assert got["writing-grammar/error_rate"] is False  # 12 in 260 words = 4.6 per 100
    assert got["writing-lexical/beyond_b1"] is False
    # No grammar check, no complexity: no grammar observation at all, nothing guessed.
    none = by_rule(observations(RULES, result(grammar=None, complexity=None), "x", 2, KNOWN))
    assert not any(k.startswith("writing-grammar/") for k in none)


def test_task1_checks_against_the_chart() -> None:
    t1 = {"overview": True,
          "numbers": [{"text": "40%", "supported": True}, {"text": "55%", "supported": False}],
          "features": [{"covered": True}, {"covered": True}, {"covered": False}]}  # fmt: skip
    got = by_rule(observations(RULES, result(min_words=150, task1=t1), "x", 1, KNOWN))
    assert got["writing-task1/overview"] is True
    assert got["writing-task1/numbers_supported"] is False  # one number the chart cannot support
    assert got["writing-task1/features_covered"] is True
    assert not any(k.startswith("writing-task2-response/") for k in got)
    nonum = by_rule(observations(RULES, result(task1=t1 | {"numbers": []}), "x", 1, KNOWN))
    assert "writing-task1/numbers_supported" not in nonum


def test_rules_file_is_a_draft_with_noisy_evidence() -> None:
    assert RULES.status == "draft"
    p = RULES.params()
    assert p.p_slip >= 0.2 and p.p_guess >= 0.3
