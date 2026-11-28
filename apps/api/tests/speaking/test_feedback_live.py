"""One real feedback call to DeepSeek on a synthetic transcript (specs/speaking/step-5.3b.md); costs
a tenth of a cent. Skipped unless WRITING_LIVE_LLM=1 and the DeepSeek key and model are set."""

import asyncio
import os

import pytest

from app.llm.providers import default_gateway
from app.speaking import feedback

LIVE = os.environ.get("WRITING_LIVE_LLM") == "1" and all(
    os.environ.get(k) for k in ("DEEPSEEK_API_KEY", "DEEPSEEK_FREE_MODEL")
)
pytestmark = pytest.mark.skipif(not LIVE, reason="set WRITING_LIVE_LLM=1 with a DeepSeek key")

QUESTION = "Do you prefer to live in a city or in the countryside?"
# Synthetic, written for this test: a plausible spoken answer with a few real mistakes.
TRANSCRIPT = (
    "Um, I prefer living in the city because it have many things to do. For example, "
    "I can go to the cinema with my friends on weekends and there is a lot of restaurants. "
    "But the city is very crowded and the air is not good for health, so sometimes I want "
    "to go to the countryside to relax."
)


def test_the_real_model_answers_in_the_schema_and_code_keeps_only_quoted_points() -> None:
    out = asyncio.run(
        default_gateway().complete(
            "speaking_feedback",
            "free",
            feedback.SYSTEM,
            [{"role": "user", "content": feedback.prompt(QUESTION, 1, TRANSCRIPT)}],
            feedback.FeedbackOut,
        )
    )
    assert isinstance(out, feedback.FeedbackOut)
    checked = feedback.check(out, TRANSCRIPT)
    print(f"\npoints kept {len(checked.points)}, dropped {checked.dropped} of {len(out.points)}")
    for p in checked.points:
        print(f"- [{p['kind']}/{p['area']}] {p['point_vi']}\n  “{p['quote']}” -> {p['better']}")
    assert checked.points  # at least one point whose quote is really in the transcript
    for p in checked.points:
        assert p["quote"] in " ".join(TRANSCRIPT.split())
