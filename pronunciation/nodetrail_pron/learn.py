"""Step 3.5a: does a small learned detector beat raw GOP? speechocean762, train then test.

    python -m nodetrail_pron.learn <speechocean762> --model <weights> --cache <dir> --out <json>

The recogniser stays frozen. Per phone it computes `features.phone_features` plus the phone's
identity, fits a logistic regression on the train half (class-weighted, L2), and compares it with
GOP on the test half: AUC, and precision and false-alarm share at thresholds chosen on the train
half for a target recall (so the test half is never used to tune). Features are cached per half,
so the slow recogniser pass runs once.
"""

import argparse
import json
import math
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from nodetrail_pron.evaluate import WRONG_BELOW, Utterance, auc, load_half
from nodetrail_pron.features import NAMES, phone_features

TARGET_RECALLS = (0.25, 0.5, 0.75)

Row = tuple[str, list[float], int]  # (phone, features, 1 if the experts scored it wrong)


def extract(utterances: Sequence[Utterance], model: Path) -> list[Row]:  # pragma: no cover - model
    from nodetrail_pron.align import AlignmentError, align
    from nodetrail_pron.model import Recogniser, read_wav

    rec = Recogniser(model)
    rows: list[Row] = []
    for u in utterances:
        if any(p not in rec.vocab for p in u.phones):
            continue
        lp = rec(read_wav(u.wav.read_bytes()))
        try:
            segs = align(lp, [rec.vocab[p] for p in u.phones], rec.blank)
        except AlignmentError:
            continue
        for phone, seg, acc in zip(u.phones, segs, u.phone_accuracy, strict=True):
            rows.append((phone, phone_features(lp, seg, rec.blank), int(acc < WRONG_BELOW)))
    return rows


def cached(path: Path, make: Any) -> list[Row]:  # pragma: no cover - file cache
    if path.exists():
        return [(str(p), [float(v) for v in f], int(t)) for p, f, t in json.loads(path.read_text())]
    rows: list[Row] = make()
    path.write_text(json.dumps(rows))
    return rows


def design(rows: Sequence[Row], phones: Sequence[str]) -> list[list[float]]:
    """Features plus a one-hot of the phone (phones unseen in training get all zeros)."""
    index = {p: i for i, p in enumerate(phones)}
    out = []
    for phone, feats, _ in rows:
        onehot = [0.0] * len(phones)
        if phone in index:
            onehot[index[phone]] = 1.0
        out.append(list(feats) + onehot)
    return out


def fit(x: list[list[float]], y: list[int], l2: float = 1e-3, steps: int = 400) -> Any:
    """Class-weighted L2 logistic regression on standardised features; returns a scorer."""
    import torch

    X = torch.tensor(x, dtype=torch.float64)
    Y = torch.tensor(y, dtype=torch.float64)
    mean, std = X.mean(0), X.std(0).clamp_min(1e-6)
    Z = (X - mean) / std
    w = torch.zeros(Z.shape[1], dtype=torch.float64, requires_grad=True)
    b = torch.zeros(1, dtype=torch.float64, requires_grad=True)
    pos = float(Y.sum())
    weight = torch.where(Y > 0, (len(y) - pos) / max(pos, 1.0), 1.0)
    opt = torch.optim.LBFGS([w, b], max_iter=steps, line_search_fn="strong_wolfe")

    def closure() -> Any:
        opt.zero_grad()
        logits = Z @ w + b
        loss = torch.nn.functional.binary_cross_entropy_with_logits(
            logits, Y, weight=weight
        ) + l2 * (w @ w)
        loss.backward()  # type: ignore[no-untyped-call]
        return loss

    opt.step(closure)  # type: ignore[no-untyped-call]

    def score(rows: list[list[float]]) -> list[float]:
        with torch.no_grad():
            z = (torch.tensor(rows, dtype=torch.float64) - mean) / std
            return [float(v) for v in torch.sigmoid(z @ w + b)]  # P(wrong)

    score.coefficients = {  # type: ignore[attr-defined]
        "mean": mean.tolist(), "std": std.tolist(), "w": w.detach().tolist(), "b": float(b),
    }  # fmt: skip
    return score


def threshold_for_recall(wrongness: Sequence[float], y: Sequence[int], recall: float) -> float:
    """The cut on a 'higher = more likely wrong' score that catches `recall` of the wrong phones."""
    wrong = sorted((s for s, t in zip(wrongness, y, strict=True) if t), reverse=True)
    if not wrong:
        return math.inf
    k = max(1, math.ceil(recall * len(wrong)))
    return wrong[k - 1]


def at(wrongness: Sequence[float], y: Sequence[int], cut: float) -> dict[str, float]:
    flagged = [t for s, t in zip(wrongness, y, strict=True) if s >= cut]
    caught, total = sum(flagged), sum(y)
    return {
        "flagged": len(flagged),
        "recall": round(caught / total, 3) if total else math.nan,
        "precision": round(caught / len(flagged), 3) if flagged else math.nan,
        "false_alarm_share": round(1 - caught / len(flagged), 3) if flagged else math.nan,
    }


def compare(train: Sequence[Row], test: Sequence[Row]) -> dict[str, Any]:
    """GOP against the learned detector, thresholds from the train half, measured on test."""
    phones = sorted({r[0] for r in train})
    y_tr, y_te = [r[2] for r in train], [r[2] for r in test]
    model = fit(design(train, phones), y_tr)
    learned_tr, learned_te = model(design(train, phones)), model(design(test, phones))
    gop_tr, gop_te = [-r[1][0] for r in train], [-r[1][0] for r in test]  # low GOP = wrong

    def side(tr: list[float], te: list[float]) -> dict[str, Any]:
        wrong = [s for s, t in zip(te, y_te, strict=True) if t]
        right = [s for s, t in zip(te, y_te, strict=True) if not t]
        cuts = {str(r): threshold_for_recall(tr, y_tr, r) for r in TARGET_RECALLS}
        return {
            # evaluate.auc expects "low = wrong"; these scores are "high = wrong"
            "auc": round(auc([-s for s in wrong], [-s for s in right]), 3),
            "at_recall": {r: at(te, y_te, cut) for r, cut in cuts.items()},
        }

    return {
        "train_phones": len(train), "train_wrong": sum(y_tr),
        "test_phones": len(test), "test_wrong": sum(y_te),
        "features": [*NAMES, "phone one-hot"],
        "gop": side(gop_tr, gop_te),
        "learned": side(learned_tr, learned_te),
        "coefficients": model.coefficients, "phones": phones,
    }  # fmt: skip


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - needs the model and corpus
    parser = argparse.ArgumentParser(prog="python -m nodetrail_pron.learn")
    parser.add_argument("corpus", type=Path)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument(
        "--cache", type=Path, required=True, help="where per-half features are kept"
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    args.cache.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    halves = {
        h: cached(
            args.cache / f"{h}.json", lambda h=h: extract(load_half(args.corpus, h), args.model)
        )
        for h in ("train", "test")
    }
    report = compare(halves["train"], halves["test"])
    report |= {"corpus": "speechocean762 (OpenSLR SLR101, CC BY 4.0)", "model": args.model.name,
               "seconds": round(time.monotonic() - started)}  # fmt: skip
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("gop", "learned")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
