# ruff: noqa: RUF001  (IPA symbols are the data here)
"""Synthetic pronunciation benchmark (specs/pronunciation/step-3.6b.md).

    uv run python -m app.evalkit.pron_bench --tts URL --pronunciation URL \
        --out ../../evals/baselines/pronunciation-synthetic.json

Each case is a word said by the self-hosted voice inside "say ... again", from exact phonemes:
as written, with the target sound swapped, or with it left out. Every recording is scored against
the word's canonical phones, as a learner's would be. The report shows, per kind, the target
sound's GOP and its peaks, how often each rule fires, and a sweep of the dropped-sound rule. Noisy
copies of the clean recordings check that the quality gate refuses them.

Pure except `main`. Synthetic audio from one native British voice shows whether the pipeline
reacts to a controlled error; it says nothing about Vietnamese accents (the real benchmark,
3.6b with L2-ARCTIC, and the Gold gate, 3.3b, do).
"""

import argparse
import base64
import io
import json
import math
import random
import statistics
import wave
from array import array
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml  # type: ignore[import-untyped]

REPO = Path(__file__).resolve().parents[4]
CASES = REPO / "evals" / "pronunciation" / "synthetic.yaml"
RATE = 16_000
CARRIER_BEFORE, CARRIER_AFTER = ["s", "eɪ"], ["ə", "ɡ", "ɛ", "n"]  # "say ... again"
VOWELS = set("aeiouɪʊəɛæʌɒɔɜɑ")
PAD_SECONDS = 0.3  # silence either side, as a recording has
Kind = Literal["right", "substituted", "dropped"]
SWEEP = (0.02, 0.05, 0.1, 0.2, 0.3, 0.5)


@dataclass(frozen=True)
class Variant:
    sound: str
    word: str
    kind: Kind
    canonical: list[str]  # what the recording is scored against (carrier included)
    target: int  # index of the target sound in `canonical`
    spoken: list[str]  # what the voice is asked to say
    said: str | None  # the phone said instead (substituted); None otherwise


def _stressed(word: list[str]) -> list[str]:
    """The word's phonemes with a primary stress mark before its first vowel."""
    out, done = [], False
    for p in word:
        if not done and any(c in VOWELS for c in p):
            out.append("ˈ" + p)
            done = True
        else:
            out.append(p)
    return out


def variants(case: dict[str, Any]) -> list[Variant]:
    phones: list[str] = list(case["phones"])
    t: int = case["target"]
    canonical = CARRIER_BEFORE + phones + CARRIER_AFTER
    index = len(CARRIER_BEFORE) + t

    def spoken(word: list[str]) -> list[str]:
        return ["s", "ˈeɪ", " ", *_stressed(word), " ", "ə", "ɡ", "ˈɛ", "n"]

    out = [Variant(case["sound"], case["word"], "right", canonical, index, spoken(phones), None)]
    for sub in case.get("subs", []):
        swapped = [*phones[:t], sub, *phones[t + 1 :]]
        out.append(
            Variant(case["sound"], case["word"], "substituted", canonical, index, spoken(swapped),
                    sub)
        )  # fmt: skip
    if case.get("drop"):
        out.append(
            Variant(case["sound"], case["word"], "dropped", canonical, index,
                    spoken(phones[:t] + phones[t + 1 :]), None)
        )  # fmt: skip
    return out


def load_cases(path: Path = CASES) -> list[Variant]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [v for case in raw["cases"] for v in variants(case)]


# --- audio (pure Python: no new dependency for a benchmark) ---


def read_wav(data: bytes) -> tuple[list[float], int]:
    with wave.open(io.BytesIO(data), "rb") as w:
        if w.getnchannels() != 1 or w.getsampwidth() != 2:
            raise ValueError("expected mono 16-bit WAV")
        rate = w.getframerate()
        pcm = array("h")
        pcm.frombytes(w.readframes(w.getnframes()))
    return [s / 32768 for s in pcm], rate


def write_wav(samples: Sequence[float], rate: int = RATE) -> bytes:
    pcm = array("h", (max(-32768, min(32767, round(s * 32767))) for s in samples))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def resample(x: Sequence[float], src: int, dst: int = RATE, taps: int = 16) -> list[float]:
    """Windowed-sinc resampling (Hann window), low-passed below the lower Nyquist rate."""
    if src == dst:
        return list(x)
    ratio = dst / src
    cutoff = min(1.0, ratio) * 0.95
    n_out = int(len(x) * ratio)
    out = []
    for i in range(n_out):
        centre = i / ratio
        lo, hi = math.floor(centre) - taps + 1, math.floor(centre) + taps
        acc = 0.0
        for j in range(max(0, lo), min(len(x), hi + 1)):
            d = centre - j
            w = 0.5 + 0.5 * math.cos(math.pi * d / taps) if abs(d) < taps else 0.0
            arg = math.pi * d * cutoff
            sinc = cutoff if d == 0 else math.sin(arg) / (math.pi * d)
            acc += x[j] * sinc * w
        out.append(acc)
    return out


def pad(x: Sequence[float], seconds: float = PAD_SECONDS, rate: int = RATE) -> list[float]:
    silence = [0.0] * int(seconds * rate)
    return [*silence, *x, *silence]


def rms(x: Sequence[float]) -> float:
    return math.sqrt(sum(s * s for s in x) / len(x)) if x else 0.0


def with_noise(x: Sequence[float], snr_db: float, seed: int = 0) -> list[float]:
    """White noise at `snr_db` below the speech's RMS (over the voiced part), seeded."""
    voiced = [s for s in x if abs(s) > 1e-4]
    level = rms(voiced) / (10 ** (snr_db / 20))
    rnd = random.Random(seed)
    return [s + rnd.gauss(0, level) for s in x]


# --- outcomes and the report ---


def dropped(score: dict[str, Any], tau: float) -> bool:
    """Neither the canonical phone nor any other phone peaks in the target's frames."""
    return float(score["peak"]) < tau and float(score["other_peak"]) < tau


def caught(score: dict[str, Any]) -> bool:
    """The current mark rule's raw signal: another phone beat the canonical one."""
    return float(score["gop"]) < 0 and score.get("competitor") is not None


def _stats(values: Iterable[float]) -> dict[str, float | None]:
    v = sorted(values)
    if not v:
        return {"n": 0, "median": None, "min": None, "max": None}
    return {"n": len(v), "median": round(statistics.median(v), 3), "min": round(v[0], 3),
            "max": round(v[-1], 3)}  # fmt: skip


def summarise(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """rows: {sound, word, kind, said, score} with `score` the target phone's service output."""
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_kind.setdefault(r["kind"], []).append(r)
    kinds: dict[str, Any] = {}
    for kind, rs in sorted(by_kind.items()):
        s = [r["score"] for r in rs]
        kinds[kind] = {
            "n": len(rs),
            "gop": _stats(x["gop"] for x in s),
            "peak": _stats(x["peak"] for x in s),
            "other_peak": _stats(x["other_peak"] for x in s),
            "gop_negative_with_competitor": sum(caught(x) for x in s),
            "competitor_is_the_swap": sum(
                1 for r in rs if r["said"] and r["score"].get("competitor") == r["said"]
            ),
        }
    sweep = []
    for tau in SWEEP:
        sweep.append({
            "tau": tau,
            **{f"dropped_rule_on_{k}": sum(dropped(r["score"], tau) for r in by_kind.get(k, []))
               for k in ("right", "substituted", "dropped")},
        })  # fmt: skip
    return {"kinds": kinds, "dropped_rule_sweep": sweep}


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - needs both services
    import httpx

    from app.pronunciation.quality import check

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tts", required=True)
    parser.add_argument("--pronunciation", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--repeats", type=int, default=5,
        help="each case said this many times: the voice varies between syntheses",
    )  # fmt: skip
    args = parser.parse_args(argv)
    rows, quality = [], []
    with httpx.Client(timeout=120) as client:
        runs = [v for v in load_cases() for _ in range(args.repeats)]
        for i, v in enumerate(runs):
            r = client.post(f"{args.tts}/speak-phonemes", json={"phonemes": v.spoken})
            r.raise_for_status()
            x, rate = read_wav(r.content)
            clean = pad(resample(x, rate))
            s = client.post(
                f"{args.pronunciation}/score",
                json={"audio": base64.b64encode(write_wav(clean)).decode(), "phones": v.canonical},
            )
            s.raise_for_status()
            out = s.json()
            score = out["phones"][v.target]
            rows.append({"sound": v.sound, "word": v.word, "kind": v.kind, "said": v.said,
                         "heard": "".join(out["recognised"]), "score": score})  # fmt: skip
            if v.kind == "right":
                for snr in (30.0, 5.0):
                    q = check(write_wav(with_noise(clean, snr, seed=i)))
                    quality.append({"word": v.word, "snr_db": snr, "ok": q.ok,
                                    "problems": list(q.problems)})  # fmt: skip
            print(f"{v.kind:11s} {v.sound:13s} {v.word:7s} gop={score['gop']:7.2f} "
                  f"peak={score['peak']:.3f} other={score['other_peak']:.3f} "
                  f"comp={score.get('competitor')}")  # fmt: skip
    report = {
        "what": "synthetic: one native voice (Piper en_GB-cori-high) from exact phonemes, each "
        "case said --repeats times (the voice varies between syntheses); sensitivity to "
        "controlled errors only, nothing about Vietnamese accents",
        "basis": {"truth": "construction", "n": len(rows), "repeats": args.repeats},
        **summarise(rows),
        "noise": {
            "refused_at_5_db": sum(1 for q in quality if q["snr_db"] == 5.0 and not q["ok"]),
            "accepted_at_30_db": sum(1 for q in quality if q["snr_db"] == 30.0 and q["ok"]),
            "n_each": sum(1 for q in quality if q["snr_db"] == 5.0),
        },
        "rows": rows,
    }
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("kinds", "dropped_rule_sweep", "noise")}, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
