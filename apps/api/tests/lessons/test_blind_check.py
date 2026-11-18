"""Blind check of lesson checkpoints (specs/grammar-lessons, step 7): no key reaches the checker."""

import asyncio
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from app.lessons.blind_check import Answer, check, judge, prompt, teaching_text
from app.lessons.model import Lesson

SAMPLE = (
    Path(__file__).resolve().parents[4]
    / "data"
    / "lessons"
    / "english-ielts"
    / "present-perfect-vs-past.yaml"
)


def lesson() -> Lesson:
    return Lesson.model_validate(yaml.safe_load(SAMPLE.read_text(encoding="utf-8")))


def test_the_checker_sees_the_teaching_but_never_a_key_or_explanation() -> None:
    les = lesson()
    text = teaching_text(les)
    assert "Example:" in text and "[wrap]" in text
    for c in les.checkpoints:
        p = prompt(les, c, {})
        assert c.explain_vi not in p and "correct" not in p.split("Question:")[1].lower()
        listed = [line[2:] for line in p.splitlines() if line.startswith("- ")]
        assert listed == sorted(o.text for o in c.options)  # sorted: the key's place says nothing


def test_agree_disagree_and_unusable() -> None:
    c = lesson().checkpoints[1]  # time-word: key "since January"
    assert judge(c, Answer(answer="SINCE JANUARY "))["result"] == "agree"
    out = judge(c, Answer(answer="last January"))
    assert out == {"checkpoint": c.id, "result": "disagree", "chose": "last January"}
    assert judge(c, Answer(answer="none"))["result"] == "disagree"
    assert judge(c, None)["result"] == "unusable"


def test_one_disagreement_sends_the_lesson_to_review() -> None:
    les = lesson()
    keys = {c.en: c.key for c in les.checkpoints}

    def asker(wrong: bool):  # type: ignore[no-untyped-def]
        async def ask(system: str, text: str) -> Answer | None:
            question = text.split("Question: ")[1].split("\n")[0]
            return Answer(
                answer="none" if wrong and question.startswith("Which") else keys[question]
            )

        return ask

    good = asyncio.run(check(les, asker(False)))
    assert good["outcome"] == "pass" and good["grounding"].startswith("the lesson only")
    bad = asyncio.run(check(les, asker(True)))
    assert bad["outcome"] == "needs_review"
    assert [r["result"] for r in bad["checkpoints"]] == ["agree", "disagree"]
