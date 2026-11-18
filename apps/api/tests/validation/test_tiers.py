"""Step V1: tier rules (specs/validation/step-v1.md)."""

import pytest

from app.validation.tiers import Label, effective, model_family, own_tier, source_of


def lab(role: str, value: str, name: str = "x", reviewer: str | None = None) -> Label:
    _, key = source_of(role, name=name, reviewer_id=reviewer)
    return Label(role, value, key)


def test_own_tier_comes_from_the_role() -> None:
    assert own_tier("expert_teacher") == "gold"
    assert own_tier("dataset") == "gold"
    assert own_tier("model") == own_tier("owner_developer") == own_tier("code_check") == "bronze"
    assert own_tier("owner_learner") == "feedback"
    with pytest.raises(ValueError):
        own_tier("friend")


def test_model_family() -> None:
    assert model_family("baidu/ernie-5.5-flash-preview:free") == "baidu"
    assert model_family("deepseek-flash") == "deepseek"
    assert model_family("DeepSeek/deepseek-chat") == "deepseek"


def test_no_labels_has_no_tier() -> None:
    assert effective([]).tier is None
    only_unsure = effective([lab("expert_teacher", "unsure", reviewer="r1")])
    assert only_unsure.tier is None and not only_unsure.disputed


def test_gold_wins_and_expert_disagreement_is_disputed() -> None:
    got = effective([lab("expert_teacher", "right", reviewer="r1"), lab("model", "wrong", "a/m")])
    assert (got.tier, got.value) == ("gold", "right")
    split = effective(
        [
            lab("expert_teacher", "right", reviewer="r1"),
            lab("expert_teacher", "wrong", reviewer="r2"),
        ]
    )
    assert split.tier is None and split.disputed


def test_two_independent_checks_make_silver() -> None:
    got = effective([lab("code_check", "right", "reading"), lab("model", "right", "baidu/ernie")])
    assert (got.tier, got.value) == ("silver", "right")


def test_one_family_counts_once() -> None:
    got = effective(
        [lab("model", "right", "baidu/ernie-a"), lab("model", "right", "baidu/ernie-b")]
    )
    assert got.tier == "bronze"


def test_the_owner_never_promotes() -> None:
    got = effective([lab("owner_developer", "right"), lab("model", "right", "baidu/ernie")])
    assert (got.tier, got.value) == ("bronze", "right")
    assert effective([lab("owner_developer", "right")]).tier == "bronze"


def test_the_owner_can_raise_a_doubt() -> None:
    got = effective(
        [
            lab("code_check", "right", "reading"),
            lab("model", "right", "baidu/e"),
            lab("owner_developer", "wrong"),
        ]
    )
    assert got.tier == "bronze" and got.disputed and got.value is None


def test_learner_feedback_is_never_correctness() -> None:
    got = effective([lab("owner_learner", "too_hard")])
    assert got.tier is None
    silver = effective(
        [
            lab("code_check", "right", "r"),
            lab("model", "right", "b/e"),
            lab("owner_learner", "wrong"),
        ]
    )
    assert silver.tier == "silver"


def test_expert_label_needs_a_reviewer() -> None:
    with pytest.raises(ValueError):
        source_of("ielts_rater")
    with pytest.raises(ValueError):
        source_of("model")
