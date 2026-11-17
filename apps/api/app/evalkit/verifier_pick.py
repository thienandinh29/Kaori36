"""Choose the lesson checker by measurement (specs/grammar-lessons, option 2).

    python -m app.evalkit.verifier_pick qwen/qwen3.7-flash z-ai/glm-5.3-flash ...

Each candidate (through OpenRouter, never DeepSeek: the checker is another family) sees the planted
set in `evals/verifier/planted-grammar.yaml` one entry at a time:
- a grammar claim: it says whether the rule and example are correct;
- a checkpoint: it answers blind (no key); a different answer from the key is a flag.
Scored per model: errors caught, false alarms (with exact 95% intervals), unusable replies, cost
from OpenRouter's own prices, time. The set ranks candidates; it does not certify one.
"""

import argparse
import asyncio
import json
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict

from app.config import REPO_ROOT
from app.evalkit.stats import rate
from app.llm.gateway import GenerationLimits, Message, ProviderError, Route, _limits
from app.llm.providers import OpenRouterAdapter

PLANTED = REPO_ROOT / "evals" / "verifier" / "planted-grammar.yaml"
REPORT = REPO_ROOT / "evals" / "baselines" / "verifier-pick.json"
SYSTEM = (
    "You check English grammar teaching material for learners. Be strict about standard English "
    "grammar; ignore style. Answer only with the JSON asked for."
)


class ClaimVerdict(BaseModel):
    model_config = ConfigDict(extra="ignore")
    verdict: Literal["correct", "incorrect"]


class Answer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    answer: str


@dataclass
class Score:
    model: str
    wrong: int = 0
    caught: int = 0
    right: int = 0
    false_alarms: int = 0
    unusable: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    seconds: float = 0.0
    misses: list[str] = field(default_factory=list)
    alarms: list[str] = field(default_factory=list)


def prices() -> dict[str, tuple[float, float]]:
    """US$ per token (input, output) from OpenRouter's public model list."""
    request = urllib.request.Request("https://openrouter.ai/api/v1/models")
    with urllib.request.urlopen(request, timeout=30) as r:
        data = json.loads(r.read())["data"]
    return {
        m["id"]: (float(m["pricing"]["prompt"]), float(m["pricing"]["completion"])) for m in data
    }


# The maker of each candidate: the checker must never be the generator's family (DeepSeek).
FAMILIES = {
    "qwen/": "qwen",
    "z-ai/": "glm",
    "openai/": "openai",
    "anthropic/": "claude",
    "meta-llama/": "llama",
    "mistralai/": "mistral",
    "google/": "gemini",
    "nvidia/": "nvidia",
    "inclusionai/": "inclusionai",
    "baidu/": "baidu",
    "dots-studio/": "dots",
}
FREE_GAP_SECONDS = 3.2  # free models allow 20 requests a minute


def family(model: str) -> str:
    for prefix, name in FAMILIES.items():
        if model.startswith(prefix):
            return name
    raise SystemExit(f"unknown maker for {model}")


def screen(planted: dict[str, Any], n: int) -> dict[str, Any]:
    """A balanced first round: n items, half planted mistakes, half claims and half checkpoints."""

    def pick(items: list[dict[str, Any]], k: int) -> list[dict[str, Any]]:
        wrong = [i for i in items if i["truth"] == "wrong"][: (k + 1) // 2]
        right = [i for i in items if i["truth"] == "right"][: k // 2]
        return wrong + right

    return {
        "claims": pick(planted["claims"], n // 2),
        "checkpoints": pick(planted["checkpoints"], n - n // 2),
    }


class Pace:
    """Spaces requests to free models so the per-minute limit is never hit."""

    def __init__(self, free: bool) -> None:
        self.gap = FREE_GAP_SECONDS if free else 0.0
        self.last = 0.0
        self.lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self.lock:
            delay = self.last + self.gap - time.monotonic()
            if delay > 0:
                await asyncio.sleep(delay)
            self.last = time.monotonic()


async def ask(
    adapter: OpenRouterAdapter,
    model: str,
    prompt: str,
    schema: type[BaseModel],
    score: Score,
    price: tuple[float, float],
    pace: Pace,
) -> BaseModel | None:
    # The gateway's Route only names families allowed in the app; this test may try others.
    route = Route.model_construct(provider="openrouter", model=model, family=family(model))  # type: ignore[arg-type]
    await pace.wait()
    token = _limits.set(GenerationLimits(1024, 0))
    try:
        reply = await adapter.generate(
            route, SYSTEM, [Message(role="user", content=prompt)], schema
        )
    except ProviderError:
        score.unusable += 1
        return None
    finally:
        _limits.reset(token)
    score.input_tokens += reply.input_tokens
    score.output_tokens += reply.output_tokens + reply.thoughts_tokens
    score.cost_usd += (
        reply.input_tokens * price[0] + (reply.output_tokens + reply.thoughts_tokens) * price[1]
    )
    text = reply.text.strip().removeprefix("```json").removesuffix("```").strip()
    try:
        return schema.model_validate_json(text)
    except ValueError:
        score.unusable += 1
        return None


async def run_model(model: str, planted: dict[str, Any], price: tuple[float, float]) -> Score:
    adapter = OpenRouterAdapter()
    score = Score(model)
    started = time.monotonic()
    sem = asyncio.Semaphore(1 if model.endswith(":free") else 4)
    pace = Pace(model.endswith(":free"))

    async def claim(c: dict[str, Any]) -> None:
        async with sem:
            prompt = (
                "Is this grammar rule and its example correct?\n\n"
                + c["text"]
                + '\n\nReturn {"verdict": "correct"} or {"verdict": "incorrect"}.'
            )
            v = await ask(adapter, model, prompt, ClaimVerdict, score, price, pace)
        flagged = v is not None and isinstance(v, ClaimVerdict) and v.verdict == "incorrect"
        record(score, c["id"], c["truth"], flagged, v is None)

    async def checkpoint(q: dict[str, Any]) -> None:
        async with sem:
            options = "\n".join(f"- {o}" for o in q["options"])
            prompt = (
                f"Fill the gap with the one correct option.\n\n{q['question']}\n\nOptions:\n"
                f'{options}\n\nReturn {{"answer": "<the option, exactly as written>"}}.'
            )
            a = await ask(adapter, model, prompt, Answer, score, price, pace)
        flagged = a is not None and isinstance(a, Answer) and a.answer.strip() != q["key"]
        record(score, q["id"], q["truth"], flagged, a is None)

    await asyncio.gather(
        *[claim(c) for c in planted["claims"]], *[checkpoint(q) for q in planted["checkpoints"]]
    )
    score.seconds = round(time.monotonic() - started, 1)
    score.cost_usd = round(score.cost_usd, 6)
    return score


def record(score: Score, item: str, truth: str, flagged: bool, unusable: bool) -> None:
    """An unusable reply counts as not caught / no alarm: the honest reading for a gate."""
    if truth == "wrong":
        score.wrong += 1
        score.caught += flagged
        if not flagged:
            score.misses.append(item + (" (unusable)" if unusable else ""))
    else:
        score.right += 1
        score.false_alarms += flagged
        if flagged:
            score.alarms.append(item)


def summary(s: Score) -> dict[str, Any]:
    caught, alarms = rate(s.caught, s.wrong), rate(s.false_alarms, s.right)
    return {
        **asdict(s),
        "caught": str(caught),
        "false_alarms": str(alarms),
        "cost_per_1000_checks_usd": round(s.cost_usd / max(1, s.wrong + s.right) * 1000, 4),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.evalkit.verifier_pick")
    parser.add_argument("models", nargs="+")
    parser.add_argument("--out", type=Path, default=REPORT)
    parser.add_argument(
        "--screen",
        type=int,
        default=0,
        help="first round: only this many items, balanced (e.g. 12)",
    )
    args = parser.parse_args(argv)
    if any(m.startswith("deepseek") for m in args.models):
        raise SystemExit("the checker must not be DeepSeek, the generator's family")
    planted = yaml.safe_load(PLANTED.read_text(encoding="utf-8"))
    if args.screen:
        planted = screen(planted, args.screen)
    table = prices()
    missing = [m for m in args.models if m not in table]
    if missing:
        raise SystemExit(f"not on OpenRouter: {', '.join(missing)}")
    results = [summary(asyncio.run(run_model(m, planted, table[m]))) for m in args.models]
    report = {
        "set": str(PLANTED.relative_to(REPO_ROOT)),
        "items": len(planted["claims"]) + len(planted["checkpoints"]),
        "date": time.strftime("%Y-%m-%d"),
        "results": results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for r in results:
        print(
            f"{r['model']:40} caught {r['caught']:28} false alarms {r['false_alarms']:28} "
            f"unusable {r['unusable']:2}  ${r['cost_per_1000_checks_usd']}/1000 checks  "
            f"{r['seconds']}s",
            file=sys.stdout,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
