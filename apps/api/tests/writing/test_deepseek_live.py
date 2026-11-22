"""One real feedback call to DeepSeek (specs/writing/step-2.4.md); costs a few tenths of a cent.

Skipped unless WRITING_LIVE_LLM=1 and DEEPSEEK_API_KEY and DEEPSEEK_FREE_MODEL are set, so CI and
ordinary test runs never call a paid model.
"""

import asyncio
import os

import pytest

from app.llm.providers import default_gateway
from app.writing import feedback

LIVE = os.environ.get("WRITING_LIVE_LLM") == "1" and all(
    os.environ.get(k) for k in ("DEEPSEEK_API_KEY", "DEEPSEEK_FREE_MODEL")
)
pytestmark = pytest.mark.skipif(not LIVE, reason="set WRITING_LIVE_LLM=1 with a DeepSeek key")

ESSAY = (
    "Some people think that plastic bags should be banned. I agree with this idea because "
    "plastic bags pollutes rivers and seas. Many animals dies after eating plastic. However, "
    "shops can give paper bags instead. In conclusion, a ban is a sensible step for the planet."
)


def test_feedback_comes_back_in_the_schema_and_its_quotes_are_checked() -> None:
    out = asyncio.run(
        default_gateway().complete(
            "writing_feedback", "free", feedback.SYSTEM,
            [{"role": "user", "content": feedback.prompt(
                "Some countries ban plastic bags. Do you agree?", ESSAY, {"words": 52})}],
            feedback.FeedbackOut,
        )
    )  # fmt: skip
    assert isinstance(out, feedback.FeedbackOut)
    fb = feedback.verify(ESSAY, out)
    kept = sum(len(p) for p in fb.criteria.values())
    print(
        f"\npoints kept {kept}, dropped {fb.dropped}; quotes {fb.quotes_kept}/{fb.quotes_checked}"
    )
    assert kept >= 1


# Step 2.11b: a complete essay, and one that skips the solutions and flips its position.
STRUCTURE_QUESTION = (
    "Traffic congestion is a growing problem in many large cities. What are the causes of this "
    "problem, and what measures could be taken to solve it? Give your own opinion."
)
COMPLETE = [
    "Traffic jams are now part of daily life in Hanoi. In my opinion, the main cause is the "
    "number of private vehicles, and better public transport is the best solution.",
    "The first cause is that millions of people ride motorbikes. Because buses are slow and "
    "crowded, most workers prefer their own vehicle, so the roads fill up every morning.",
    "To solve this, the city should build more metro lines. For example, the Cat Linh line "
    "already carries thousands of passengers a day who would otherwise drive.",
    "In conclusion, private vehicles cause most congestion, and I believe that investing in "
    "public transport is the best way to reduce it.",
]
SKIPPED = [
    "Traffic jams are now part of daily life in Hanoi. I believe that private vehicles are not "
    "the real problem.",
    "The first cause is that millions of people ride motorbikes. Because buses are slow and "
    "crowded, most workers prefer their own vehicle, so the roads fill up every morning.",
    "Another cause is that many offices are in the city centre.",
    "In conclusion, private vehicles are clearly the real problem in our cities.",
]


@pytest.mark.parametrize("paragraphs", [COMPLETE, SKIPPED], ids=["complete", "skipped"])
def test_structure_comes_back_in_the_schema_and_its_quotes_are_checked(
    paragraphs: list[str],
) -> None:
    from app.writing import structure
    from app.writing.own_prompt import propose_parts

    parts = propose_parts(STRUCTURE_QUESTION)
    out = asyncio.run(
        default_gateway().complete(
            "writing_structure", "free", structure.SYSTEM,
            [{"role": "user",
              "content": structure.prompt(STRUCTURE_QUESTION, parts, paragraphs)}],
            structure.StructureOut,
        )
    )  # fmt: skip
    assert isinstance(out, structure.StructureOut)
    s = structure.verify(paragraphs, parts, out)
    print(
        f"\nparts {[p.text for p in parts]} answered {s.answered}; dropped {s.dropped}; "
        f"stances {s.introduction.stance}/{s.conclusion.stance}; "
        f"development {[b.development for b in s.body]}; findings {[f.kind for f in s.findings]}"
    )
    assert s.dropped <= 1
