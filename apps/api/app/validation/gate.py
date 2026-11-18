"""What a gate report rests on (specs/validation/step-v3.md). Pure.

A gate is `measured` only when its truth comes from experts (gold) or is known by construction
(simulations, planted faults), and there are at least as many labelled cases as the gate needs.
Anything else keeps its numbers but is a development number, never a gate result.
"""

from typing import Any, Literal

from app.evalkit.stats import rate

Truth = Literal["gold", "silver", "bronze", "feedback", "construction"]
TRUTHS: tuple[str, ...] = ("gold", "silver", "bronze", "feedback", "construction")
GATE_TRUTHS: frozenset[str] = frozenset({"gold", "construction"})

_WHY = {
    "gold": ("", ""),
    "construction": ("", ""),
    "silver": (
        "Hai kiểm tra độc lập đồng ý vẫn chưa phải nhãn của chuyên gia.",
        "two independent checks agreeing are not expert labels",
    ),
    "bronze": (
        "Chỉ một nguồn (ví dụ chủ dự án): chưa phải nhãn của chuyên gia.",
        "one source only (for example the owner): not expert labels",
    ),
    "feedback": (
        "Cảm nhận của người học, không phải nhãn đúng/sai.",
        "learner feedback, not a correctness label",
    ),
}


def basis(truth: Truth, n: int, required: int, *, declared: bool = False) -> dict[str, Any]:
    if truth not in TRUTHS:
        raise ValueError(f"unknown truth: {truth}")
    if n < 0 or required < 1:
        raise ValueError("n must be >= 0 and required >= 1")
    out: dict[str, Any] = {"truth": truth, "n": n, "required": required, "declared": declared}
    if truth not in GATE_TRUTHS:
        vi, en = _WHY[truth]
    elif n < required:
        vi = f"Mới có {n}/{required} nhãn: chưa đủ để đo."
        en = f"only {n} of {required} labelled cases: not enough to measure"
    else:
        out["gate"] = "measured"
        return out
    out |= {"gate": "not_measured", "why_vi": vi, "why_en": en}
    return out


RATED_BY = ("owner", "teacher", "rater")


def rated_by(who: str) -> tuple[Truth, bool]:
    """(truth, declared) for a hand-filled sheet: the owner is Bronze; a teacher or a trained rater
    is Gold, but declared by whoever ran the command, not checked against the `labels` table."""
    if who == "owner":
        return "bronze", False
    if who in ("teacher", "rater"):
        return "gold", True
    raise ValueError(f"rated by one of {RATED_BY}")


def measured(b: dict[str, Any]) -> bool:
    return bool(b.get("gate") == "measured")


def process_supports(escapes: int, n: int, max_rate: float = 0.05) -> dict[str, Any]:
    """Whether a Gold sample supports trusting a process: the upper 95% bound of its escape rate.

    E.g. checker-verified Reading items: `escapes` = the expert found the item wrong.
    """
    r = rate(escapes, n)
    ok = r.high is not None and r.high <= max_rate
    return {
        "escapes": escapes,
        "n": n,
        "upper_95": None if r.high is None else round(r.high, 3),
        "bar": max_rate,
        "supports": ok,
    }
