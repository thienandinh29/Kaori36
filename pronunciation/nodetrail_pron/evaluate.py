# ruff: noqa: RUF001
"""How well do the scores agree with experts? speechocean762, test half (step 3.2b).

    python -m nodetrail_pron.evaluate <speechocean762 folder> --out report.json [--limit N]

The corpus (OpenSLR SLR101, CC BY 4.0 on its OpenSLR page; Zhang et al., Interspeech 2021):
5,000 English sentences by Mandarin-speaking children and adults, scored by five experts. Its
canonical phones are ARPAbet; they are mapped to the recogniser's IPA phones below. Two measures:
- sentence level: Pearson correlation of a sentence's mean GOP with the experts' accuracy (0-10);
- phone level: how well a low GOP finds the phones the experts scored as mispronounced (phone
  accuracy below 1 on the 0-2 scale): AUC, and precision and recall at a few thresholds.
This tests the machinery on Mandarin speakers, not Vietnamese learners: the owner's recordings
are the evidence for the product (the gate).
"""

import argparse
import json
import math
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ARPAbet (stress removed) to the recogniser's IPA tokens; AH is /ə/ unstressed and /ʌ/ stressed.
ARPABET = {
    "AA": "ɑː",
    "AE": "æ",
    "AO": "ɔː",
    "AW": "aʊ",
    "AY": "aɪ",
    "EH": "ɛ",
    "ER": "ɚ",
    "EY": "eɪ",
    "IH": "ɪ",
    "IY": "iː",
    "OW": "oʊ",
    "OY": "ɔɪ",
    "UH": "ʊ",
    "UW": "uː",
    "B": "b",
    "CH": "tʃ",
    "D": "d",
    "DH": "ð",
    "F": "f",
    "G": "ɡ",
    "HH": "h",
    "JH": "dʒ",
    "K": "k",
    "L": "l",
    "M": "m",
    "N": "n",
    "NG": "ŋ",
    "P": "p",
    "R": "ɹ",
    "S": "s",
    "SH": "ʃ",
    "T": "t",
    "TH": "θ",
    "V": "v",
    "W": "w",
    "Y": "j",
    "Z": "z",
    "ZH": "ʒ",
}
WRONG_BELOW = 1.0  # expert phone accuracy (0-2) below this: mispronounced


def to_ipa(phone: str) -> str:
    base = phone.rstrip("012")
    if base == "AH":
        return "ʌ" if phone.endswith("1") else "ə"
    return ARPABET[base]


def pearson(x: Sequence[float], y: Sequence[float]) -> float:
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    return sxy / math.sqrt(sxx * syy)


def pearson_interval(r: float, n: int) -> tuple[float, float]:
    """95% interval by Fisher's z (needs more than 3 pairs)."""
    if n <= 3 or abs(r) >= 1:
        return (math.nan, math.nan)
    z, se = math.atanh(r), 1 / math.sqrt(n - 3)
    return math.tanh(z - 1.96 * se), math.tanh(z + 1.96 * se)


def auc(scores_wrong: Sequence[float], scores_right: Sequence[float]) -> float:
    """P(a wrong phone scores lower than a right one): the Mann-Whitney U, ties counted half."""
    ranked = sorted([(s, 1) for s in scores_wrong] + [(s, 0) for s in scores_right])
    rank_sum, i = 0.0, 0
    while i < len(ranked):
        j = i
        while j < len(ranked) and ranked[j][0] == ranked[i][0]:
            j += 1
        mean_rank = (i + 1 + j) / 2
        rank_sum += mean_rank * sum(1 for k in range(i, j) if ranked[k][1] == 1)
        i = j
    n_w, n_r = len(scores_wrong), len(scores_right)
    u = rank_sum - n_w * (n_w + 1) / 2  # wrong phones ranked above right ones
    return 1 - u / (n_w * n_r)


def at_threshold(wrong: Sequence[float], right: Sequence[float], t: float) -> dict[str, float]:
    flagged_wrong = sum(1 for s in wrong if s < t)
    flagged_right = sum(1 for s in right if s < t)
    flagged = flagged_wrong + flagged_right
    return {
        "threshold": t,
        "flagged": flagged,
        "precision": round(flagged_wrong / flagged, 3) if flagged else math.nan,
        "recall": round(flagged_wrong / len(wrong), 3),
        "false_alarm_share": round(flagged_right / flagged, 3) if flagged else math.nan,
    }


@dataclass(frozen=True)
class Utterance:
    id: str
    wav: Path
    accuracy: float
    phones: list[str]  # IPA
    phone_accuracy: list[float]


def load_test(folder: Path) -> list[Utterance]:
    """The test half: `test/wav.scp` lists the audio, `resource/scores.json` the experts' scores."""
    return load_half(folder, "test")


def load_half(folder: Path, half: str) -> list[Utterance]:
    """One half of the corpus (`train` or `test`), with the experts' scores."""
    scores = json.loads((folder / "resource" / "scores.json").read_text(encoding="utf-8"))
    out = []
    for line in (folder / half / "wav.scp").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        utt, rel = line.split(maxsplit=1)
        s = scores[utt]
        phones, accuracy = [], []
        for w in s["words"]:
            phones += [to_ipa(p) for p in w["phones"]]
            accuracy += [float(a) for a in w["phones-accuracy"]]
        out.append(Utterance(utt, folder / rel, float(s["accuracy"]), phones, accuracy))
    return out


Scorer = Callable[[Path, list[str]], list[float] | None]


def evaluate(utterances: Sequence[Utterance], score: Scorer) -> dict[str, Any]:
    sentence_tool: list[float] = []
    sentence_expert: list[float] = []
    wrong: list[float] = []
    right: list[float] = []
    skipped = 0
    for u in utterances:
        gops = score(u.wav, u.phones)
        if gops is None or len(gops) != len(u.phones):
            skipped += 1
            continue
        sentence_tool.append(sum(gops) / len(gops))
        sentence_expert.append(u.accuracy)
        for g, a in zip(gops, u.phone_accuracy, strict=True):
            (wrong if a < WRONG_BELOW else right).append(g)
    r = pearson(sentence_tool, sentence_expert)
    low, high = pearson_interval(r, len(sentence_tool))
    return {
        "sentences": len(sentence_tool),
        "skipped": skipped,
        "sentence_pcc": round(r, 3),
        "sentence_pcc_95": [round(low, 3), round(high, 3)],
        "phones_wrong": len(wrong),
        "phones_right": len(right),
        "phone_auc": round(auc(wrong, right), 3) if wrong and right else None,
        "thresholds": [at_threshold(wrong, right, t) for t in (-4.0, -2.0, -1.0, 0.0)],
    }


def main(argv: list[str] | None = None) -> int:
    from nodetrail_pron.align import AlignmentError, align, gop
    from nodetrail_pron.model import Recogniser, read_wav

    parser = argparse.ArgumentParser(prog="python -m nodetrail_pron.evaluate")
    parser.add_argument("corpus", type=Path)
    parser.add_argument("--model", type=Path, required=True, help="folder with the pinned files")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args(argv)
    rec = Recogniser(args.model)
    utterances = load_test(args.corpus)
    if args.limit:
        utterances = utterances[: args.limit]

    def score(wav: Path, phones: list[str]) -> list[float] | None:
        if any(p not in rec.vocab for p in phones):
            return None
        lp = rec(read_wav(wav.read_bytes()))
        try:
            segs = align(lp, [rec.vocab[p] for p in phones], rec.blank)
        except AlignmentError:
            return None
        return [s.gop for s in gop(lp, segs, rec.blank)]

    started = time.monotonic()
    report = evaluate(utterances, score)
    report |= {
        "corpus": "speechocean762 test (OpenSLR SLR101, CC BY 4.0)",
        "model": str(args.model.name),
        "seconds": round(time.monotonic() - started),
    }
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
