"""Gate: does the recommendation engine pick the right thing? (specs/two-layer-map/spec.md, M2)

Simulated learners on the real competency map and the live foundations, with noisy estimates:
- `weak_foundation`: one competency is weak because one of its live `requires` foundations is
  weak; everything else is known. Right = the first activity learns that foundation.
- `no_weak_foundation`: one competency is weak although all its foundations are known. Right = the
  first activity practises that competency.
- `borderline_foundation` (reported, not gated): the weak foundation is only a little weak
  (0.70-0.85), to show the cost of the engine's 0.8 root-cause line.
Each is reported with an exact interval, with the two cross-errors (practice when a foundation is
weak, and the reverse). The bar is 90% each; CI also compares with the committed baseline.

Usage, from apps/api:
    uv run python -m app.evalkit.recommend_gate run --out ../../evals/baselines/recommend-gate.json
    uv run python -m app.evalkit.recommend_gate check ../../evals/baselines/recommend-gate.json
"""

import argparse
import json
import random
import sys
from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path

from app.competencies.check import load_foundations
from app.competencies.model import load_map
from app.engine.recommend import Estimate, recommend
from app.evalkit.stats import rate

RUNS = 1000
SEED = 20261118
NOISE = 0.04
BAR = 0.90
TOLERANCE = 0.02
TODAY = date(2026, 12, 1)
AT = datetime(2026, 12, 1, 8, 0, tzinfo=UTC)


def _clip(x: float) -> float:
    return min(0.999, max(0.001, x))


def run(runs: int = RUNS, seed: int = SEED) -> dict[str, object]:
    cmap = load_map()
    live = load_foundations().live
    rng = random.Random(seed)
    comps = [c for c in cmap.competencies if any(f in live for f in c.requires)]
    foundations_all = sorted({f for c in cmap.competencies for f in c.requires if f in live})
    skills = frozenset({"reading", "listening", "writing", "speaking"})
    cells = []
    for scenario in ("weak_foundation", "no_weak_foundation", "borderline_foundation"):
        right = practice_instead = foundation_instead = 0
        for _ in range(runs):
            comp = rng.choice(comps)
            weak_f = rng.choice([f for f in comp.requires if f in live])
            f_true = {f: rng.uniform(0.92, 0.99) for f in foundations_all}
            if scenario == "weak_foundation":
                f_true[weak_f] = rng.uniform(0.2, 0.6)
            elif scenario == "borderline_foundation":
                f_true[weak_f] = rng.uniform(0.70, 0.85)
            c_true = {c.slug: rng.uniform(0.92, 0.99) for c in cmap.competencies}
            c_true[comp.slug] = rng.uniform(0.3, 0.7)
            fs = {f: Estimate(_clip(p + rng.gauss(0, NOISE)), 10) for f, p in f_true.items()}
            cs = {c: Estimate(_clip(p + rng.gauss(0, NOISE)), 10) for c, p in c_true.items()}
            first = recommend(cmap, fs, cs, {}, skills, TODAY, 40, AT).activities[0]
            if scenario != "no_weak_foundation":
                right += first.kind == "learn_foundation" and first.target == weak_f
                practice_instead += first.kind == "practise_competency"
            else:
                right += first.kind == "practise_competency" and first.target == comp.slug
                foundation_instead += first.kind == "learn_foundation"
        r = rate(right, runs)
        cells.append({
            "scenario": scenario, "runs": runs, "right": right,
            "share": round(right / runs, 4),
            "low": None if r.low is None else round(r.low, 4),
            "practice_when_foundation_weak": practice_instead,
            "foundation_when_none_weak": foundation_instead,
        })  # fmt: skip
    return {"seed": seed, "noise": NOISE, "bar": BAR, "cells": cells}


def check(baseline: dict[str, object], fresh: dict[str, object]) -> list[str]:
    problems = []
    base = {c["scenario"]: c for c in baseline["cells"]}  # type: ignore[attr-defined]
    for c in fresh["cells"]:  # type: ignore[attr-defined]
        if c["scenario"] == "borderline_foundation":
            continue  # reported, not gated
        if c["share"] < BAR:
            problems.append(f"{c['scenario']}: {c['share']} is below the bar {BAR}")
        b = base.get(c["scenario"])
        if b is not None and c["share"] < b["share"] - TOLERANCE:
            problems.append(f"{c['scenario']}: {c['share']} dropped from {b['share']}")
    return problems


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run").add_argument("--out", type=Path)
    sub.add_parser("check").add_argument("baseline", type=Path)
    args = parser.parse_args(argv)
    fresh = run()
    if args.command == "run":
        text = json.dumps(fresh, indent=1) + "\n"
        if args.out:
            args.out.write_text(text, encoding="utf-8")
        print(text)
        return 0
    problems = check(json.loads(args.baseline.read_text(encoding="utf-8")), fresh)
    for c in fresh["cells"]:  # type: ignore[attr-defined]
        print(c)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    print("recommendation gate: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
