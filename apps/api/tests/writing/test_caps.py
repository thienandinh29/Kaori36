"""Descriptor caps (specs/writing/step-2.12.md, 2.12a): code findings may lower a band once
measured; the model's structure findings never do, they stay notes."""

from pathlib import Path
from typing import Any

import pytest
import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError

from app.writing.caps import (
    DEFAULT_PATH,
    CapRule,
    CapsFile,
    apply_caps,
    cap_effect,
    code_findings,
    fire,
    load_caps,
    model_findings,
    notes,
)
from app.writing.prompts import Part
from app.writing.structure import StructureOut, verify

ONE_BLOCK = " ".join(["Students learn better when they study with a teacher in a classroom."] * 12)
PARAGRAPHED = "\n\n".join([ONE_BLOCK[:300], ONE_BLOCK[300:600], ONE_BLOCK[600:]])


def rule(**over: Any) -> CapRule:
    base: dict[str, Any] = {
        "id": "no_paragraphing", "criterion": "cc", "cap": 5, "source": "code", "applied": False,
        "status": "proposed", "finding": "one block", "reading": "r",
        "descriptor": ["Band 5: Paragraphing may be inadequate or missing."],
    }  # fmt: skip
    return CapRule.model_validate(base | over)


def test_the_committed_caps_file_loads_and_applies_nothing_yet() -> None:
    caps = load_caps()
    assert {r.id for r in caps.rules} == {
        "no_paragraphing", "part_missing", "position_missing", "position_changed"
    }  # fmt: skip
    assert not any(r.applied for r in caps.rules)  # nothing is applied before it is measured
    assert caps.source.url.startswith("https://ielts.org/")
    assert DEFAULT_PATH.name == "caps.yaml"


def test_a_model_finding_can_never_be_applied() -> None:
    with pytest.raises(ValidationError, match="never changes a band"):
        rule(
            id="part_missing",
            criterion="tr",
            source="model",
            applied=True,
            status="measured",
            descriptor=["Band 5: The main parts of the prompt are incompletely addressed."],
        )


def test_a_rule_must_be_measured_before_it_is_applied_and_quote_its_band() -> None:
    with pytest.raises(ValidationError, match="only after it is measured"):
        rule(applied=True)
    with pytest.raises(ValidationError, match="quote the band 6 line"):
        rule(cap=6)
    with pytest.raises(ValidationError, match="found by code"):
        rule(source="model")


def test_rule_ids_are_unique(tmp_path: Path) -> None:
    raw = yaml.safe_load(DEFAULT_PATH.read_text(encoding="utf-8"))
    raw["rules"].append(raw["rules"][0])
    with pytest.raises(ValidationError, match="unique"):
        CapsFile.model_validate(raw)


def test_one_long_block_is_unparagraphed_but_a_short_one_is_not() -> None:
    assert code_findings(ONE_BLOCK) == {"no_paragraphing": ("1 paragraph, 144 words",)}
    assert code_findings(PARAGRAPHED) == {}
    assert code_findings("Too short to judge. " * 10) == {}


def test_only_measured_code_caps_lower_a_band() -> None:
    proposed = fire([rule()], ONE_BLOCK, None)
    assert apply_caps({"cc": 6.0, "tr": 7.0}, proposed) == {"cc": 6.0, "tr": 7.0}
    assert notes(proposed) == proposed
    measured = fire([rule(applied=True, status="measured")], ONE_BLOCK, None)
    assert apply_caps({"cc": 6.0, "tr": 7.0}, measured) == {"cc": 5.0, "tr": 7.0}
    assert apply_caps({"cc": 4.0}, measured) == {"cc": 4.0}  # a cap never raises a band
    assert notes(measured) == ()


PARAS = [
    "Some people think online study is enough. I believe classrooms are still better.",
    "Online study saves time because students do not travel.",
    "However, classrooms give students direct contact with teachers.",
    "In conclusion, online study is clearly the better choice for most students.",
]
PARTS = (
    Part(text="online study"),
    Part(text="classrooms"),
    Part(text="your opinion", position=True),
)


def test_structure_issues_become_notes_with_their_quotes_and_hints_do_not() -> None:
    s = verify(PARAS, PARTS, StructureOut.model_validate({
        "introduction": {"stance": "second", "quote": "I believe classrooms are still better"},
        "conclusion": {"stance": "first", "quote": "online study is clearly the better choice"},
        "body": [
            {"paragraph": 2, "main_idea": "Online study saves time", "answers": [1],
             "development": "explanation", "development_quote": "because students do not travel"},
            {"paragraph": 3, "main_idea": "classrooms give students direct contact", "answers": [1],
             "development": "none", "development_quote": None},
        ],
    }))  # fmt: skip
    found = model_findings(s)
    assert set(found) == {"part_missing", "position_changed"}  # "undeveloped" is a hint, not a cap
    assert found["position_changed"] == (
        "I believe classrooms are still better", "online study is clearly the better choice"
    )  # fmt: skip
    fired = fire(load_caps().rules, "\n\n".join(PARAS), s)
    assert {f.rule.id for f in fired} == {"part_missing", "position_changed"}
    assert apply_caps({"tr": 8.0}, fired) == {"tr": 8.0}  # model findings never touch the band
    assert len(notes(fired)) == 2
    assert model_findings(None) == {}


def test_cap_effect_compares_error_with_and_without_the_cap_where_it_fired() -> None:
    e = cap_effect([5, 6, 7], [6.5, 6.0, 7.0], [True, True, False], cap=5)
    assert e.fired == 2 and e.mae_without == 0.75 and e.mae_with == 0.5 and e.helps is True
    worse = cap_effect([7.0], [7.0], [True], cap=5)
    assert worse.helps is False
    assert cap_effect([7.0], [7.0], [False], cap=5).helps is None
    with pytest.raises(ValueError, match="same length"):
        cap_effect([7.0], [7.0, 6.0], [True], cap=5)
