"""The owner's hand-rating tools: export and score (specs/writing/step-2.4.md)."""

from pathlib import Path

import pytest

from app.evalkit.writing_review import main, score_corrections, score_feedback, verdict
from app.writing.export_review import correction_rows, feedback_rows
from app.writing.export_review import main as export_main

RESULT = {
    "feedback": {
        "criteria": {
            "tr": [{"kind": "strength", "point_vi": "Rõ ý.", "quotes": ["I agree with", "a ban"]}],
            "gra": [
                {"kind": "issue", "point_vi": "Chia động từ.", "quotes": ["bags pollutes rivers"]}
            ],
        }
    },
    "grammar": {
        "issues": [
            {"id": 0, "sentence": "A dies.", "text": "dies", "suggestion": "die",
             "errant_type": "R:VERB:SVA", "node": "present-simple", "source": "llm"},
            {"id": 1, "sentence": "B go.", "text": "go", "suggestion": "goes",
             "errant_type": "R:VERB:SVA", "node": None, "source": "languagetool"},
        ]
    },
}  # fmt: skip


def test_the_export_lists_every_point_and_only_ai_corrections() -> None:
    rows = feedback_rows([("e1", RESULT), ("e2", {"feedback": None})])
    assert [(r["criterion"], r["kind"], r["supported"]) for r in rows] == [
        ("tr", "strength", ""),
        ("gra", "issue", ""),
    ]
    assert rows[0]["quotes"] == "I agree with | a ban"
    fixes = correction_rows([("e1", RESULT)])
    assert [(r["issue_id"], r["suggestion"], r["correct"]) for r in fixes] == [("0", "die", "")]


def test_verdicts_are_read_leniently_and_garbage_is_refused() -> None:
    assert [verdict(x) for x in ("y", " YES ", "1", "đúng", "n", "No", "0", "sai", "")] == [
        True, True, True, True, False, False, False, False, None,
    ]  # fmt: skip
    with pytest.raises(ValueError, match="use y or n"):
        verdict("maybe")


def feedback_sheet(supported: list[str]) -> list[dict[str, str]]:
    return [
        {"essay_id": f"e{i // 3}", "criterion": ("tr", "cc", "gra")[i % 3],
         "kind": "issue" if i % 2 else "strength", "supported": v}
        for i, v in enumerate(supported)
    ]  # fmt: skip


def test_feedback_faithfulness_with_intervals_per_criterion_and_kind() -> None:
    r = score_feedback(feedback_sheet(["y"] * 15 + ["n"] * 3 + [""] * 2))
    assert r["overall"]["yes"] == 15 and r["overall"]["rated"] == 18
    assert r["overall"]["share"] == round(15 / 18, 4) and len(r["overall"]["interval"]) == 2
    assert r["unrated_points"] == 2 and r["essays_rated"] == 6
    assert set(r["per_criterion"]) == {"tr", "cc", "gra"} and set(r["per_kind"]) == {
        "issue",
        "strength",
    }
    assert "usable interval" in r["note"] and "18 points" in r["note"]
    assert score_feedback([])["overall"]["share"] is None


def correction_sheet(good: int, bad: int) -> list[dict[str, str]]:
    return [{"errant_type": "R:VERB:SVA", "correct": "y"} for _ in range(good)] + [
        {"errant_type": "M:DET", "correct": "n"} for _ in range(bad)
    ]


def test_correction_precision_and_the_owners_decision_threshold() -> None:
    few = score_corrections(correction_sheet(20, 2))
    assert few["overall"]["rated"] == 22 and "at least 50" in few["note"]
    high = score_corrections(correction_sheet(58, 2))  # lower bound well above 0.80
    assert "may decide to let AI corrections count" in high["note"]
    low = score_corrections(correction_sheet(40, 20))
    assert "keep AI corrections as hints" in low["note"]
    assert set(high["per_type"]) == {"SVA", "DET"} and high["per_type"]["DET"]["yes"] == 0


def test_the_command_line_reads_a_sheet_and_refuses_the_wrong_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sheet = tmp_path / "feedback.csv"
    sheet.write_text("essay_id,criterion,kind,supported\ne1,tr,issue,y\ne1,cc,issue,n\n", "utf-8")
    assert main(["feedback", str(sheet)]) == 0
    assert '"rated": 2' in capsys.readouterr().out
    assert main(["corrections", str(sheet)]) == 2  # no `correct` column: the wrong sheet
    assert "no 'correct' column" in capsys.readouterr().out
    sheet.write_text("essay_id,criterion,kind,supported\ne1,tr,issue,perhaps\n", "utf-8")
    assert main(["feedback", str(sheet)]) == 2


def test_the_export_refuses_to_write_outside_the_private_folder(tmp_path: Path) -> None:
    assert export_main(["feedback", "--learner", "x", "--out", str(tmp_path / "f.csv")]) == 2
