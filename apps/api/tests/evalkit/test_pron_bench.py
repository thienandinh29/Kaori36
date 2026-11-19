"""Step 3.6b: the synthetic pronunciation benchmark's pure parts (app/evalkit/pron_bench.py)."""
# ruff: noqa: RUF001  (IPA symbols are the data here)

import math
from itertools import pairwise

import pytest

from app.evalkit.pron_bench import (
    CARRIER_BEFORE,
    load_cases,
    read_wav,
    resample,
    rms,
    summarise,
    variants,
    with_noise,
    write_wav,
)


def test_cases_say_the_word_right_swapped_and_dropped_inside_a_carrier() -> None:
    vs = variants({"sound": "th-voiceless", "word": "month", "phones": ["m", "ʌ", "n", "θ"],
                   "target": 3, "subs": ["t"], "drop": True})  # fmt: skip
    assert [v.kind for v in vs] == ["right", "substituted", "dropped"]
    right, swapped, dropped = vs
    assert right.canonical == ["s", "eɪ", "m", "ʌ", "n", "θ", "ə", "ɡ", "ɛ", "n"]
    assert right.canonical[right.target] == "θ" and right.target == len(CARRIER_BEFORE) + 3
    assert right.spoken == ["s", "ˈeɪ", " ", "m", "ˈʌ", "n", "θ", " ", "ə", "ɡ", "ˈɛ", "n"]
    assert "t" in swapped.spoken and "θ" not in swapped.spoken and swapped.said == "t"
    assert "θ" not in dropped.spoken and dropped.canonical == right.canonical
    every = load_cases()
    assert {v.kind for v in every} == {"right", "substituted", "dropped"}
    assert all(v.canonical[v.target] == v.canonical[v.target].strip() for v in every)
    assert len(every) == 63  # 28 words: 28 right, 22 swapped, 13 dropped


def test_resampling_keeps_a_tone_and_the_duration() -> None:
    src = 22_050
    tone = [0.5 * math.sin(2 * math.pi * 440 * i / src) for i in range(src // 4)]
    out = resample(tone, src)
    assert len(out) == pytest.approx(16_000 / 4, abs=2)
    assert rms(out[100:-100]) == pytest.approx(0.5 / math.sqrt(2), rel=0.03)
    # Zero crossings: still about 440 Hz.
    crossings = sum(1 for a, b in pairwise(out) if a < 0 <= b)
    assert crossings == pytest.approx(440 / 4, abs=2)
    x, rate = read_wav(write_wav(out))
    assert rate == 16_000 and len(x) == len(out)


def test_noise_is_seeded_and_at_the_asked_level() -> None:
    speech = [0.3 * math.sin(i / 7) for i in range(16_000)]
    a, b = with_noise(speech, 10, seed=1), with_noise(speech, 10, seed=1)
    assert a == b
    noise = [x - s for x, s in zip(a, speech, strict=True)]
    assert 20 * math.log10(rms(speech) / rms(noise)) == pytest.approx(10, abs=0.5)


def test_the_summary_counts_each_rule_per_kind() -> None:
    def row(kind: str, gop: float, comp: str | None, peak: float, other: float,
            said: str | None = None) -> dict[str, object]:  # fmt: skip
        score = {"gop": gop, "competitor": comp, "peak": peak, "other_peak": other}
        return {"sound": "s", "word": "w", "kind": kind, "said": said, "score": score}

    out = summarise([
        row("right", 3.0, None, 0.9, 0.01),
        row("substituted", -4.0, "t", 0.01, 0.9, said="t"),
        row("dropped", -5.0, "ə", 0.0, 0.05),
    ])  # fmt: skip
    assert out["kinds"]["substituted"]["competitor_is_the_swap"] == 1
    assert out["kinds"]["dropped"]["gop_negative_with_competitor"] == 1
    tenth = next(s for s in out["dropped_rule_sweep"] if s["tau"] == 0.1)
    assert tenth == {"tau": 0.1, "dropped_rule_on_right": 0, "dropped_rule_on_substituted": 0,
                     "dropped_rule_on_dropped": 1}  # fmt: skip
