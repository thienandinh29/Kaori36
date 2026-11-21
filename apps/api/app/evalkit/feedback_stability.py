"""Does the model say the same things about the same essay? (specs/writing/step-2.11.md, 2.11a)

    uv run python -m app.evalkit.feedback_stability \\
        ../../data/private/writing/stability/essays.jsonl --runs 3 --max-cost 0.20 \\
        --out ../../evals/writing/feedback-stability.json

Each essay goes to the app's feedback prompt `runs` times; every reply passes `feedback.verify`, as
in the app. Two points from different runs are the same point when criterion and kind match and
their quotes overlap. Issues and strengths are scored apart, per essay with exact intervals and
across essays with a bootstrap interval. Essay texts stay in `data/private/`; the report holds
metrics, ids, the model and the cost only (a test checks that no essay text reaches it). A sample of
matched pairs, with their quotes, goes to a separate file under `data/private/` for the owner to
check by eye; it is never committed. The 60% bar is a proposal until the owner has seen a result.
"""

import argparse
import asyncio
import json
import random
import re
import sys
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path
from typing import Any

from app.evalkit.stats import clopper_pearson
from app.writing import feedback
from app.writing.analysis import analyse, load_linking_words

REPO = Path(__file__).resolve().parents[4]
KINDS = ("issue", "strength")
MIN_WORD_OVERLAP = 0.5  # share of the shorter quote's words found in the other quote
RECUR_BAR = 0.60  # PROPOSED (owner, 21 Nov): stays a proposal until the owner has seen a result
BAR_STATUS = "proposed"
PAIR_SAMPLE = 10  # matched pairs written to data/private for checking by eye
_WORD = re.compile(r"\w+")


@dataclass(frozen=True)
class Found:
    """A checked feedback point, as compared across runs."""

    criterion: str
    kind: str
    quotes: tuple[str, ...]
    point_vi: str = ""  # shown in the private pair sample only; never used for matching


def _norm(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).lower().split())


def _quotes_overlap(a: str, b: str) -> bool:
    x, y = _norm(a), _norm(b)
    if x in y or y in x:
        return True
    wa, wb = set(_WORD.findall(x)), set(_WORD.findall(y))
    small = min(len(wa), len(wb))
    return small > 0 and len(wa & wb) / small >= MIN_WORD_OVERLAP


def same_point(a: Found, b: Found) -> bool:
    """Same criterion and kind, and some quote of one overlaps some quote of the other."""
    return (
        a.criterion == b.criterion
        and a.kind == b.kind
        and any(_quotes_overlap(q, r) for q in a.quotes for r in b.quotes)
    )


def points_of(fb: feedback.Feedback) -> list[Found]:
    return [Found(c, p.kind, p.quotes, p.point_vi) for c, ps in fb.criteria.items() for p in ps]


def _jaccard(a: Sequence[Found], b: Sequence[Found]) -> float | None:
    if not a and not b:
        return None
    matched_a = sum(any(same_point(p, q) for q in b) for p in a)
    matched_b = sum(any(same_point(q, p) for p in a) for q in b)
    matched = (matched_a + matched_b) / 2  # matching is symmetric up to duplicates
    union = len(a) + len(b) - matched
    return matched / union if union else None


def essay_stability(runs: Sequence[Sequence[Found]], kind: str) -> dict[str, Any]:
    """For one essay and kind: how many points recur in at least two runs, and pairwise overlap."""
    by_run = [[p for p in run if p.kind == kind] for run in runs]
    total = sum(len(r) for r in by_run)
    recurring = sum(
        1
        for i, run in enumerate(by_run)
        for p in run
        if any(any(same_point(p, q) for q in other) for j, other in enumerate(by_run) if j != i)
    )
    pairs = [_jaccard(a, b) for a, b in combinations(by_run, 2)]
    pair_values = [x for x in pairs if x is not None]
    low, high = clopper_pearson(recurring, total) if total else (None, None)
    return {
        "points": total,
        "recurring": recurring,
        "share": round(recurring / total, 3) if total else None,
        "interval": [round(low, 3), round(high, 3)]
        if low is not None and high is not None
        else None,
        "pairwise_jaccard": round(sum(pair_values) / len(pair_values), 3) if pair_values else None,
        "points_per_run": [len(r) for r in by_run],
    }


@dataclass(frozen=True)
class Essay:
    id: str
    question: str
    text: str
    source: str


def load_essays(path: Path) -> list[Essay]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            out.append(
                Essay(str(d["id"]), str(d["question"]), str(d["text"]), str(d.get("source", "")))
            )
    ids = [e.id for e in out]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate essay id")
    return out


def _bootstrap_mean(values: Sequence[float], seed: int = 0, resamples: int = 2000) -> list[float]:
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(values) for _ in values) / len(values) for _ in range(resamples))
    return [round(means[int(0.025 * resamples)], 3), round(means[int(0.975 * resamples) - 1], 3)]


def summarise(per_essay: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Across essays, per kind: the mean of per-essay shares with a bootstrap interval."""
    out: dict[str, Any] = {}
    for kind in KINDS:
        shares = [e[kind]["share"] for e in per_essay if e[kind]["share"] is not None]
        out[kind] = {
            "essays": len(shares),
            "mean_share": round(sum(shares) / len(shares), 3) if shares else None,
            "interval": _bootstrap_mean(shares) if len(shares) >= 2 else None,
            "min_share": min(shares, default=None),
            "max_share": max(shares, default=None),
        }
    issue = out["issue"]["mean_share"]
    out["proposed_decision"] = (
        None
        if issue is None
        else "keep only issues recurring in 2 of 3 runs"
        if issue < RECUR_BAR
        else "one call is stable enough"
    )
    out["bar"] = {"issue_share": RECUR_BAR, "status": BAR_STATUS}
    return out


def matched_pairs(essay_id: str, runs: Sequence[Sequence[Found]]) -> list[dict[str, Any]]:
    """Every matched pair across runs of one essay, with quotes: for the private sample only."""
    out = []
    for (i, a_run), (j, b_run) in combinations(enumerate(runs), 2):
        for a in a_run:
            for b in b_run:
                if same_point(a, b):
                    out.append({"essay": essay_id, "criterion": a.criterion, "kind": a.kind,
                                "runs": [i + 1, j + 1], "a": {"point_vi": a.point_vi,
                                "quotes": list(a.quotes)}, "b": {"point_vi": b.point_vi,
                                "quotes": list(b.quotes)}})  # fmt: skip
    return out


def pair_sample(pairs: Sequence[dict[str, Any]], n: int = PAIR_SAMPLE, seed: int = 0) -> list[Any]:
    """A seeded sample of matched pairs, issues first when there are enough of them."""
    rng = random.Random(seed)
    issues = [p for p in pairs if p["kind"] == "issue"]
    strengths = [p for p in pairs if p["kind"] != "issue"]
    take_i = min(len(issues), max(n - len(strengths), (n + 1) // 2 + 2))
    picked = rng.sample(issues, take_i) + rng.sample(strengths, min(len(strengths), n - take_i))
    return picked[:n]


def build_report(
    essays: Sequence[Essay],
    per_essay: Sequence[dict[str, Any]],
    runs: int,
    models: Sequence[str],
    cost: str,
    measured_on: str,
) -> dict[str, Any]:
    """The committed report: ids and numbers only (no quotes, points, sources or essay text)."""
    return {
        "what": "feedback stability, specs/writing/step-2.11.md (2.11a)",
        "measured_on": measured_on,
        "model": sorted(set(models)),
        "runs_per_essay": runs,
        "essays": len(essays),
        "summary": summarise([e for e in per_essay if "issue" in e]),
        "per_essay": [{k: v for k, v in e.items() if k != "pairs"} for e in per_essay],
        "cost": cost,
        "limits": [
            "web sample essays, mostly strong ones: learner essays may behave differently",
            "a point is matched by its quotes, so two problems in one quoted sentence count as one",
            "the app also sends LanguageTool's errors to the model; this measurement does not",
            f"the {RECUR_BAR:.0%} bar is {BAR_STATUS}: the owner decides after seeing this result",
        ],
        "pairs_for_review": "a sample of matched pairs is in data/private (never committed)",
    }


Ask = Callable[[str, str], feedback.FeedbackOut | None]


def measure(
    essays: Sequence[Essay], ask: Ask, linking: Any, runs: int, can_spend: Callable[[], bool]
) -> list[dict[str, Any]]:
    """Every essay `runs` times through the app's prompt and `verify`; stops at the cost cap."""
    results = []
    for e in essays:
        a = analyse(e.text, 2, linking)
        measures = {"words": a.words, "sentences": a.sentences, "paragraphs": a.paragraphs,
                    "linking_groups_used": a.linking_groups_used}  # fmt: skip
        found_runs: list[list[Found]] = []
        failed = 0
        for _ in range(runs):
            if not can_spend():
                break
            out = ask(feedback.SYSTEM, feedback.prompt(e.question, e.text, measures))
            if out is None:
                failed += 1
                continue
            found_runs.append(points_of(feedback.verify(e.text, out)))
        if len(found_runs) < 2:
            results.append(
                {"id": e.id, "skipped": f"{len(found_runs)} usable runs", "failed": failed}
            )
            if not can_spend():
                break
            continue
        results.append({"id": e.id, "runs": len(found_runs), "failed": failed, "words": a.words,
                        "pairs": matched_pairs(e.id, found_runs)}
                       | {k: essay_stability(found_runs, k) for k in KINDS})  # fmt: skip
    return results


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - models and database
    import psycopg

    from app.config import get_settings
    from app.llm.gateway import Gateway, GatewayError
    from app.llm.providers import default_gateway
    from app.reading.calls import CallLog
    from app.writing.model_calls import Prices

    parser = argparse.ArgumentParser(prog="python -m app.evalkit.feedback_stability")
    parser.add_argument("essays", type=Path)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--max-cost", type=float, default=0.20, help="US$ for this run")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--pairs-out", type=Path, default=REPO / "data" / "private" / "writing" / "stability"
        / "matched-pairs.json", help="private: the matched pairs to check by eye",
    )  # fmt: skip
    args = parser.parse_args(argv)
    if REPO / "data" / "private" not in args.pairs_out.resolve().parents:
        print(
            "--pairs-out must be under data/private/: the pairs quote the essays", file=sys.stderr
        )
        return 2
    essays = load_essays(args.essays)
    settings = get_settings()
    log = CallLog(Prices(settings.llm_price_input_per_mtok, settings.llm_price_output_per_mtok))
    base = default_gateway()
    gateway = Gateway(base.routing, base.adapters, observe_attempt=log.observe)
    model: list[str] = []
    linking = load_linking_words(REPO / "data" / "writing" / "linking-words.yaml")

    def ask(system: str, user: str) -> feedback.FeedbackOut | None:
        try:
            done = asyncio.run(
                gateway.complete_with_metadata(
                    "writing_feedback", "free", system,
                    [{"role": "user", "content": user}], feedback.FeedbackOut,
                )
            )  # fmt: skip
        except GatewayError as exc:
            print(f"call failed: {exc}", file=sys.stderr)
            return None
        model.append(done.route.model)
        return done.value if isinstance(done.value, feedback.FeedbackOut) else None

    now = datetime.now(UTC)
    with psycopg.connect(settings.database_url) as conn:

        def can_spend() -> bool:
            log.flush(conn, now)
            conn.commit()
            return bool(log.cost_usd < args.max_cost)

        try:
            per_essay = measure(essays, ask, linking, args.runs, can_spend)
        finally:
            log.flush(conn, now)
            conn.commit()
    report = build_report(
        essays, per_essay, args.runs, model, log.summary(), now.date().isoformat()
    )
    pairs = [p for e in per_essay for p in e.get("pairs", [])]
    args.pairs_out.parent.mkdir(parents=True, exist_ok=True)
    args.pairs_out.write_text(
        json.dumps({"matched_pairs": len(pairs), "sample": pair_sample(pairs)}, ensure_ascii=False,
                   indent=2) + "\n", encoding="utf-8",
    )  # fmt: skip
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(log.summary())
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
