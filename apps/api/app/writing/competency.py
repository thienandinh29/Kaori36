"""Writing competency observations from code checks (specs/two-layer-map/writing-evidence.md). Pure.

Each analysed essay gives a few pass/fail observations per Writing competency, by the draft rules in
`data/writing/competency-rules.yaml`. They are checks a script can make, not band descriptors.
A rule whose input is missing (no grammar check, no chart, no number in a Task 1 essay) gives no
observation: nothing is guessed.
"""

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field

from app.engine.bkt import BKTParams
from app.writing.analysis import words

TASK_ONLY = {"writing-task1": 1, "writing-task2-response": 2}


class Observation_(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    slip: float = Field(gt=0, lt=1)
    guess: float = Field(gt=0, lt=1)
    transit: float = Field(ge=0, lt=1)
    init: float = Field(gt=0, lt=1)


class Rules(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    status: Literal["draft", "reviewed"]
    observation: Observation_
    rules: dict[str, dict[str, dict[str, Any]]]

    def params(self) -> BKTParams:
        o = self.observation
        return BKTParams(p_init=o.init, p_transit=o.transit, p_slip=o.slip, p_guess=o.guess)


def load_rules(path: Path) -> Rules:
    return Rules.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


@dataclass(frozen=True)
class Observation:
    competency: str
    rule: str
    passed: bool
    value: float | None
    explain_vi: str


def _share(k: int, n: int) -> float | None:
    return None if n == 0 else round(k / n, 3)


def _check(
    rule: str, cfg: Mapping[str, Any], result: Mapping[str, Any], text: str, known: Collection[str]
) -> tuple[bool, float | None, str] | None:
    """(passed, measured value, Vietnamese explanation), or None when the input is missing."""
    if rule == "long_enough":
        return (
            bool(result["long_enough"]),
            float(result["words"]),
            f"Độ dài: {result['words']}/{result['min_words']} từ",
        )
    if rule == "paragraphs":
        n = int(result["paragraphs"])
        return n >= cfg["min"], float(n), f"Số đoạn: {n} (cần ít nhất {cfg['min']})"
    if rule == "linking_variety":
        n = int(result["linking_groups_used"])
        return (
            n >= cfg["min_groups"],
            float(n),
            f"Từ nối thuộc {n} chức năng (cần ít nhất {cfg['min_groups']})",
        )
    if rule == "position_stated":
        used = [g for g in cfg["groups"] if g in result.get("linking", {})]
        return (
            bool(used),
            float(len(used)),
            "Có câu nêu quan điểm hoặc kết luận"
            if used
            else ("Chưa thấy câu nêu quan điểm hoặc kết luận"),
        )
    if rule == "sentence_length":
        avg = float(result["avg_sentence_words"])
        ok = cfg["min_avg"] <= avg <= cfg["max_avg"]
        return (
            ok,
            avg,
            f"Trung bình {avg:g} từ một câu (nên từ {cfg['min_avg']} đến {cfg['max_avg']})",
        )
    if rule == "beyond_b1":
        ws = [w.lower().replace("\u2019", "'").strip("'-") for w in words(text)]
        share = _share(sum(1 for w in ws if w not in known), len(ws))
        if share is None:
            return None
        return (
            share >= cfg["min_share"],
            share,
            f"{share:.0%} số từ ngoài nhóm A1-B1 (cần ít nhất {cfg['min_share']:.0%})",
        )
    if rule == "error_rate":
        grammar = result.get("grammar")
        if not grammar or not result["words"]:
            return None
        errors = sum(int(v) for v in grammar.get("counts", {}).values())
        rate = round(errors * 100 / result["words"], 2)
        return (
            rate <= cfg["max_per_100_words"],
            rate,
            f"{rate:g} lỗi ngữ pháp mỗi 100 từ (tối đa {cfg['max_per_100_words']:g})",
        )
    if rule == "complex_sentences":
        c = result.get("complexity")
        if not c or not c.get("sentences"):
            return None
        share = float(c["complex_sentence_share"])
        return (
            share >= cfg["min_share"],
            share,
            f"{share:.0%} câu có nhiều mệnh đề (cần ít nhất {cfg['min_share']:.0%})",
        )
    t1 = result.get("task1")
    if rule == "overview":
        if not t1:
            return None
        return (
            bool(t1["overview"]),
            None,
            "Có câu tổng quan" if t1["overview"] else ("Chưa có câu tổng quan (Overall, ...)"),
        )
    if rule == "numbers_supported":
        if not t1 or not t1["numbers"]:
            return None
        ok = sum(1 for n in t1["numbers"] if n["supported"])
        share = _share(ok, len(t1["numbers"]))
        assert share is not None
        return share >= cfg["min_share"], share, f"{ok}/{len(t1['numbers'])} số liệu khớp biểu đồ"
    if rule == "features_covered":
        if not t1 or not t1["features"]:
            return None
        ok = sum(1 for f in t1["features"] if f["covered"])
        share = _share(ok, len(t1["features"]))
        assert share is not None
        return (
            share >= cfg["min_share"],
            share,
            f"Nêu {ok}/{len(t1['features'])} đặc điểm chính của biểu đồ",
        )
    raise ValueError(f"unknown rule {rule}")


def observations(
    rules: Rules, result: Mapping[str, Any], text: str, task: int, known: Collection[str]
) -> list[Observation]:
    out = []
    for competency, checks in rules.rules.items():
        if TASK_ONLY.get(competency, task) != task:
            continue
        for rule, cfg in checks.items():
            got = _check(rule, cfg or {}, result, text, known)
            if got is not None:
                out.append(Observation(competency, rule, *got))
    return out
