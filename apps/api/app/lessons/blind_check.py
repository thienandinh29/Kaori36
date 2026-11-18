"""Blind check of a lesson's checkpoints by another model family (specs/grammar-lessons, step 7).

    uv run python -m app.lessons.blind_check <lesson.yaml> --out <json>

The checker (the gateway's `lesson_check` task: free Ernie, dots as backup, never DeepSeek) sees
only what the lesson teaches (its narration, examples and board) and the text of any cited chunks,
then answers each checkpoint without the key. The options are shown sorted, so the key's place in
the file says nothing. An answer that differs from the key, or no usable answer, makes the lesson
`needs_review`: it is a reason for the owner to look, not a verdict on the lesson.
"""

import argparse
import asyncio
import json
from collections.abc import Awaitable, Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app.lessons.model import (
    BoardTable,
    BoardTimeline,
    BoardWrite,
    Checkpoint,
    Lesson,
    Say,
    ShowExample,
)

SYSTEM = (
    "You check English grammar lessons for learners. Answer only from the lesson text and sources "
    'given; if they do not support any option, answer "none". Answer only with the JSON asked for.'
)


class Answer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    answer: str


Ask = Callable[[str, str], Awaitable[Answer | None]]  # (system, prompt) -> answer, None if unusable


def teaching_text(lesson: Lesson) -> str:
    """What the lesson teaches, in English, scene by scene: never its checkpoints or keys."""
    out = []
    for scene in lesson.scenes:
        lines = []
        for a in scene.actions:
            if isinstance(a, Say):
                lines.append(a.en)
            elif isinstance(a, ShowExample):
                lines.append(f"Example: {a.en}")
            elif isinstance(a, BoardWrite):
                lines.append(f"Board: {a.text}")
            elif isinstance(a, BoardTable):
                lines += ["Table: " + " | ".join(row) for row in a.rows]
            elif isinstance(a, BoardTimeline):
                marks = [f"{p.label} at {p.at:+g}" for p in a.points]
                marks += [f"{s.label} from {s.start:+g} to {s.end:+g}" for s in a.spans]
                lines.append("Timeline (0 is now, negative is the past): " + "; ".join(marks))
        if lines:
            out.append(f"[{scene.kind}]\n" + "\n".join(lines))
    return "\n\n".join(out)


def prompt(lesson: Lesson, checkpoint: Checkpoint, chunks: Mapping[str, str]) -> str:
    options = sorted(o.text for o in checkpoint.options)
    sources = "\n\n".join(f"[{cid}]\n{chunks[cid]}" for cid in sorted(chunks))
    return (
        f"Lesson: {lesson.title_en}\n\n{teaching_text(lesson)}\n\n"
        + (f"Sources cited by the lesson:\n\n{sources}\n\n" if sources else "")
        + f"Question: {checkpoint.en}\nOptions:\n"
        + "\n".join(f"- {o}" for o in options)
        + '\n\nReturn {"answer": "<one option, exactly as written>"} or {"answer": "none"}.'
    )


def judge(checkpoint: Checkpoint, answer: Answer | None) -> dict[str, Any]:
    """One checkpoint's result: agree, disagree (with what it chose) or unusable."""
    if answer is None:
        return {"checkpoint": checkpoint.id, "result": "unusable"}
    given = answer.answer.strip()
    texts = {o.text.casefold(): o.text for o in checkpoint.options}
    chosen = texts.get(given.casefold())
    if chosen == checkpoint.key:
        return {"checkpoint": checkpoint.id, "result": "agree"}
    return {
        "checkpoint": checkpoint.id,
        "result": "disagree",
        "chose": chosen or given[:80],  # "none" or text outside the options is a disagreement too
    }


async def check(
    lesson: Lesson, ask: Ask, chunks: Mapping[str, str] | None = None
) -> dict[str, Any]:
    """All checkpoints, one at a time (free models are rate-limited)."""
    results = []
    for c in lesson.checkpoints:
        results.append(judge(c, await ask(SYSTEM, prompt(lesson, c, chunks or {}))))
    return verdict(lesson, results, cited=bool(chunks))


def verdict(lesson: Lesson, results: Sequence[Mapping[str, Any]], cited: bool) -> dict[str, Any]:
    outcome: Literal["pass", "needs_review"] = (
        "pass" if results and all(r["result"] == "agree" for r in results) else "needs_review"
    )
    return {
        "lesson": f"{lesson.course}/{lesson.node}",
        "status": lesson.status,
        # Without cited chunks only the lesson's own teaching was given: this shows the checkpoints
        # are answerable from the lesson and agree with their keys, not that the rules are sourced.
        "grounding": "cited chunks and the lesson"
        if cited
        else "the lesson only (no cited chunks)",
        "outcome": outcome,
        "checkpoints": list(results),
    }


def gateway_ask(generator_family: str, tier: str = "free") -> Ask:  # pragma: no cover - model
    """The gateway's `lesson_check` route, which refuses a checker of the generator's family."""
    from app.llm.gateway import GatewayError, complete_with_metadata, verification_scope

    async def ask(system: str, text: str) -> Answer | None:
        try:
            with verification_scope(generator_family):
                out = await complete_with_metadata(
                    "lesson_check", tier, system, [{"role": "user", "content": text}], Answer
                )
        except GatewayError:
            return None
        checkers.add(out.route.model)
        return out.value if isinstance(out.value, Answer) else None

    checkers: set[str] = set()
    ask.checkers = checkers  # type: ignore[attr-defined]
    return ask


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - calls a model
    import yaml  # type: ignore[import-untyped]

    parser = argparse.ArgumentParser(prog="python -m app.lessons.blind_check")
    parser.add_argument("lesson", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--generator-family",
        default="deepseek",
        help="who wrote the lesson (deepseek for generated ones); the checker must differ",
    )
    args = parser.parse_args(argv)
    lesson = Lesson.model_validate(yaml.safe_load(args.lesson.read_text(encoding="utf-8")))
    if any(s.cites for s in lesson.scenes):
        raise SystemExit(
            "cited chunks are not loaded yet: this lesson needs the library (phase B2)"
        )
    ask = gateway_ask(args.generator_family)
    report = asyncio.run(check(lesson, ask))
    report["checker"] = sorted(ask.checkers)  # type: ignore[attr-defined]
    report["generator_family"] = args.generator_family
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["outcome"] == "pass" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
