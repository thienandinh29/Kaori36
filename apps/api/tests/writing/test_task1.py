"""Task 1 checks against the chart's own data (specs/writing/step-2.5.md)."""

from pathlib import Path

import pytest

from app.writing.prompts import load_prompts
from app.writing.task1 import (
    check,
    check_features,
    check_numbers,
    describe,
    has_overview,
    numbers_in,
)

BANK = load_prompts(Path(__file__).resolve().parents[4] / "data" / "writing" / "prompts.yaml")


def chart(prompt_id: str):  # type: ignore[no-untyped-def]
    p = BANK.get(prompt_id)
    assert p is not None and p.figure is not None
    return p.figure


LINE = chart("t1-internet-access")
PIE = chart("t1-family-spending")

GOOD = (
    "The graph shows internet access in three countries from 2000 to 2020. Overall, all rose. "
    "Country A grew from 5% in 2000 to 85% in 2020, the highest figure in 2020, while Country B "
    "was lowest at 2% in 2000. Country C started at 12% and reached 80%, a rise of 68 points."
)


def test_every_number_the_chart_supports_passes() -> None:
    got = {n.text: n.supported for n in check_numbers(GOOD, LINE)}
    assert all(got.values()), got
    assert {"2000", "2020", "5%", "85%", "2%", "12%", "80%", "68"} <= set(got)  # 68 = 80 - 12


def test_a_number_nothing_supports_is_flagged_and_rounding_is_allowed() -> None:
    essay = "Country A reached 90% in 2020, and 2 in 3 homes of Country B had it. About 85.0% too."
    got = {n.text: n.supported for n in check_numbers(essay, LINE)}
    assert got["90%"] is False
    assert got["85.0%"] is True  # 85 written with a decimal place is the same number
    assert check_numbers("Nearly 85.2%.", LINE)[0].supported is False  # an invented decimal
    assert "2" not in got and "3" not in got  # bare small numbers are counts, not data


def test_years_and_thousands_separators() -> None:
    assert numbers_in("In 2005, 1,200 homes and 3.5% of them") == [
        ("2005", 2005.0, False),
        ("1,200", 1200.0, False),
        ("3.5%", 3.5, True),
    ]
    assert not check_numbers("In 2007 it rose.", LINE)[0].supported  # not one of the categories


def test_pie_shares_are_supported_and_a_wrong_share_is_not() -> None:
    got = {n.text: n.supported for n in check_numbers("Housing is 32% and food 24%, not 45%.", PIE)}
    assert got == {"32%": True, "24%": True, "45%": False}
    assert check_numbers("Housing takes 32% of 100%.", PIE)[1].supported  # the total


def test_key_features_must_be_in_the_same_sentence_as_their_series() -> None:
    covered = {(f.kind, f.series): f.covered for f in check_features(GOOD, LINE)}
    assert covered[("max", "Country A")]  # "Country A ... 85%"
    assert covered[("min", "Country B")]  # "Country B was lowest at 2%"
    assert covered[("overall_change", "Country C")]  # "Country C started at 12% and reached 80%"
    # Country B's peak (70%) is never given with Country B: the year 2020 elsewhere is not enough
    assert not covered[
        ("max", "Country B")
    ]  # "highest" there belongs to Country A, before B's name
    short = "Country A rose a lot over the years."
    got = {(f.kind, f.series): f.covered for f in check_features(short, LINE)}
    assert got[("overall_change", "Country A")]  # a change word with the series name
    assert not got[("max", "Country A")] and not got[("max", "Country C")]


def test_a_pie_needs_only_its_largest_slice() -> None:
    feats = check_features("Housing is the biggest share of spending.", PIE)
    assert len(feats) == 1 and feats[0].covered and feats[0].category == "Housing"
    assert not check_features("People spend money on things.", PIE)[0].covered


@pytest.mark.parametrize(
    ("text", "expected"),
    [("Overall, sales rose.", True), ("It is clear that sales rose.", True),
     ("Sales rose then fell.", False)],
)  # fmt: skip
def test_overview_marker(text: str, expected: bool) -> None:
    assert has_overview(text) is expected


def test_the_result_is_plain_data_and_the_model_sees_the_facts() -> None:
    r = check(GOOD, LINE).to_json()
    assert r["overview"] is True and {"numbers", "features"} <= set(r)
    d = describe(LINE)
    assert "Country A: 5, 18, 40, 68, 85" in d and "peaks at 85%" in d


def test_a_prompt_needs_a_figure_exactly_when_it_is_task_1() -> None:
    from pydantic import ValidationError

    from app.writing.prompts import Prompt

    task2 = BANK.get("t2-plastic-ban")
    assert task2 is not None and task2.figure is None
    with pytest.raises(ValidationError):
        Prompt(id="x", task=2, type="chart", level="B2", status="draft", prompt="y" * 30,
               figure=LINE)  # fmt: skip
    with pytest.raises(ValidationError):
        Prompt(id="x", task=1, type="chart", level="B2", status="draft", prompt="y" * 30)
