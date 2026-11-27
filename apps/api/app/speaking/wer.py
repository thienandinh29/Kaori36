"""Word error rate of the Speaking transcripts against the owner's typed references (step 5.1).

    uv run python -m app.speaking.wer --refs ../../data/private/speaking/references.jsonl \\
        --out ../../evals/speaking/wer.json

Each reference line: {"answer_id": "...", "reference": "what was said, word for word"}.
The references stay in git-ignored data/private; only the metrics are written out. Pooled WER
is total edits over total reference words, with a 95% bootstrap interval over answers (one
learner: an N-of-1 measure of this recogniser on this voice, not a general claim). It is
reported with fillers kept and removed.
"""

import argparse
import json
import random
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FILLERS = frozenset({"um", "umm", "uh", "uhm", "er", "erm", "hmm", "mm"})
_NOT_WORD = re.compile(r"[^\w']+")


def words(text: str, drop_fillers: bool = False) -> list[str]:
    """Lower-case words without punctuation; numbers are left as typed."""
    flat = _NOT_WORD.sub(" ", unicodedata.normalize("NFC", text).lower().replace("_", " "))
    out = [w.strip("'") for w in flat.split()]
    return [w for w in out if w and not (drop_fillers and w in FILLERS)]


def edits(ref: Sequence[str], hyp: Sequence[str]) -> int:
    """Word-level Levenshtein distance (substitutions, deletions, insertions)."""
    previous = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        current = [i]
        for j, h in enumerate(hyp, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (r != h)))
        previous = current
    return previous[-1]


@dataclass(frozen=True)
class Pair:
    answer_id: str
    reference: str
    hypothesis: str


def _pooled(rows: Sequence[tuple[int, int]]) -> float | None:
    n = sum(r for _, r in rows)
    return None if n == 0 else sum(e for e, _ in rows) / n


def measure(
    pairs: Sequence[Pair], drop_fillers: bool, resamples: int = 1000, seed: int = 0
) -> dict[str, Any]:
    rows = []
    per = []
    for p in pairs:
        ref, hyp = words(p.reference, drop_fillers), words(p.hypothesis, drop_fillers)
        e = edits(ref, hyp)
        rows.append((e, len(ref)))
        per.append(
            {
                "answer_id": p.answer_id,
                "reference_words": len(ref),
                "edits": e,
                "wer": None if not ref else round(e / len(ref), 3),
            }
        )
    pooled = _pooled(rows)
    low = high = None
    if len(rows) >= 2 and pooled is not None:
        rng = random.Random(seed)
        draws = sorted(
            x
            for x in (_pooled([rng.choice(rows) for _ in rows]) for _ in range(resamples))
            if x is not None
        )
        low, high = draws[int(0.025 * len(draws))], draws[int(0.975 * len(draws)) - 1]
    return {
        "answers": len(rows),
        "reference_words": sum(r for _, r in rows),
        "wer": None if pooled is None else round(pooled, 3),
        "low": None if low is None else round(low, 3),
        "high": None if high is None else round(high, 3),
        "per_answer": per,
    }


def report(pairs: Sequence[Pair], missing: Sequence[str] = ()) -> dict[str, Any]:
    return {
        "fillers_kept": measure(pairs, drop_fillers=False),
        "fillers_removed": measure(pairs, drop_fillers=True),
        "missing_transcripts": list(missing),
        "note": (
            "N-of-1: the owner's own answers and typed references (the owner is not the judge "
            "of correct English, but is the only witness of what was said). Interval: 95% "
            "bootstrap over answers."
        ),
    }


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - database
    import psycopg

    from app.config import get_settings

    parser = argparse.ArgumentParser(prog="python -m app.speaking.wer")
    parser.add_argument("--refs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    lines = args.refs.read_text("utf-8").splitlines()
    refs = [json.loads(line) for line in lines if line.strip()]
    pairs, missing = [], []
    with psycopg.connect(get_settings().database_url) as conn:
        for r in refs:
            row = conn.execute(
                "select transcript->>'text' from speaking_answers where id::text=%s "
                "and transcript_status='done'",
                (r["answer_id"],),
            ).fetchone()
            if row is None:
                missing.append(r["answer_id"])
            else:
                pairs.append(Pair(r["answer_id"], r["reference"], row[0] or ""))
    out = report(pairs, missing)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2) + "\n", "utf-8")
    print(json.dumps({k: v for k, v in out["fillers_kept"].items() if k != "per_answer"}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
