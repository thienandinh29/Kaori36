"""The Learning Recommendation Engine (specs/two-layer-map/spec.md, M2). Pure and traced.

Given both maps' estimates, due reviews, the owner's target and today's time, it returns 3-5
activities, each with a DecisionTrace for "Vì sao?". The rules, in order:
1. due reviews first, capped at `balance.review_share_max` of the list;
2. an unmeasured competency of a skill NodeTrail can practise gets one short diagnostic first: the
   engine never guesses a weakness from nothing;
3. then the measured competency with the largest gap to "known" (0.9), the target until bands are
   calibrated;
4. root cause through the links: its weakest `requires` foundation clearly below known (under
   ROOT_CAUSE_BELOW, 0.8) is learned first; with none, the competency itself is practised. A
   foundation between 0.8 and 0.9 is too close to call with noisy estimates (the simulation gate
   showed a hard 0.9 sends 17% of learners back to foundations they know);
5. balance: at most `balance.foundations_in_a_row_max` foundation activities in a row, and at least
   one exam-style activity a day once one is possible (two in the last 12 weeks before the exam).
With nothing measured yet, it falls back to the weakest foundations that the most competencies
require, so the list is useful from the first day. Links to foundations that are not live are
ignored. Speed and streaks never enter.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal

from app.competencies.model import CompetencyMap
from app.engine.trace import Alternative, DecisionTrace, fmt_p

KNOWN = 0.9
ROOT_CAUSE_BELOW = 0.8  # a foundation must be clearly not known to be named the cause
MIN_EVIDENCE = 3  # answers before a competency counts as measured
FINAL_WEEKS = 12
Kind = Literal["review", "diagnostic", "learn_foundation", "practise_competency"]
EXAM_STYLE: frozenset[str] = frozenset({"diagnostic", "practise_competency"})


@dataclass(frozen=True)
class Estimate:
    p: float
    evidence: int  # how many observations the estimate rests on


@dataclass(frozen=True)
class Activity:
    kind: Kind
    target: str  # review source, competency or foundation slug
    trace: DecisionTrace
    via: str | None = None  # the competency a foundation activity serves


@dataclass(frozen=True)
class Today:
    activities: list[Activity]
    notes: list[str] = field(default_factory=list)


def size(minutes: int) -> int:
    """3 activities for 30 minutes or less, up to 5 for 50 or more (about 10 minutes each)."""
    return max(3, min(5, minutes // 10))


def _trace(
    slug: str,
    at: datetime,
    rule: str,
    rule_vi: str,
    p: float | None = None,
    alternatives: Sequence[Alternative] = (),
) -> DecisionTrace:
    return DecisionTrace(
        kind="next_item",
        concept_slug=slug,
        at=at,
        prior=p,
        posterior=p,
        rule=rule,
        rule_vi=rule_vi,
        alternatives=list(alternatives),
    )


def recommend(
    cmap: CompetencyMap,
    foundations: Mapping[str, Estimate],
    competencies: Mapping[str, Estimate],
    due: Mapping[str, int],
    available_skills: frozenset[str],
    today: date,
    minutes: int,
    at: datetime,
    names_vi: Mapping[str, str] | None = None,
) -> Today:
    """foundations: live foundation nodes only; competencies: estimates with any evidence."""
    name = (names_vi or {}).get
    n = size(minutes)
    out: list[Activity] = []
    notes: list[str] = []

    # 1. Due reviews, capped.
    cap = max(1, int(n * cmap.balance.review_share_max))
    for source, count in sorted(due.items(), key=lambda x: -x[1]):
        if count > 0 and len(out) < cap:
            out.append(
                Activity(
                    "review",
                    source,
                    _trace(
                        source,
                        at,
                        "recommend.review_due",
                        f"Có {count} mục đến hạn ôn ({name(source) or source}): "
                        "ôn trước để không quên.",
                    ),
                )
            )

    measured = {
        c.slug: competencies[c.slug]
        for c in cmap.competencies
        if c.slug in competencies and competencies[c.slug].evidence >= MIN_EVIDENCE
    }

    # 2. One diagnostic for an unmeasured competency NodeTrail can practise.
    unmeasured = [
        c for c in cmap.competencies if c.slug not in measured and c.skill in available_skills
    ]
    if unmeasured and len(out) < n:
        c = unmeasured[0]
        out.append(
            Activity(
                "diagnostic",
                c.slug,
                _trace(
                    c.slug,
                    at,
                    "recommend.diagnostic_first",
                    f"Chưa đo {name(c.slug) or c.name_vi}: làm một bài ngắn để biết mức hiện tại "
                    "trước khi chọn bài học.",
                ),
            )
        )

    # 3-4. Candidates by gap, each traced back to its weakest live `requires` foundation.
    candidates: list[Activity] = []
    by_gap = sorted(measured.items(), key=lambda kv: (kv[1].p, kv[0]))
    for slug, est in by_gap:
        if est.p >= KNOWN:
            continue
        comp = next(c for c in cmap.competencies if c.slug == slug)
        weak = sorted(
            (
                (f, foundations[f].p)
                for f in comp.requires
                if f in foundations and foundations[f].p < ROOT_CAUSE_BELOW
            ),
            key=lambda x: (x[1], x[0]),
        )
        if weak:
            f, p = weak[0]
            alts = [
                Alternative(concept_slug=g, p_known=q, why_not_vi="cao hơn") for g, q in weak[1:]
            ]
            candidates.append(
                Activity(
                    "learn_foundation",
                    f,
                    _trace(
                        f,
                        at,
                        "recommend.root_cause_foundation",
                        f"{name(slug) or comp.name_vi} còn yếu ({fmt_p(est.p)}) → {name(f) or f} "
                        f"chưa chắc ({fmt_p(p)}) → học {name(f) or f} trước.",
                        p,
                        alts,
                    ),
                    via=slug,
                )
            )
        else:
            candidates.append(
                Activity(
                    "practise_competency",
                    slug,
                    _trace(
                        slug,
                        at,
                        "recommend.practise_competency",
                        f"Nền tảng của {name(slug) or comp.name_vi} đã chắc: luyện dạng bài thi "
                        f"({fmt_p(est.p)}).",
                        est.p,
                    ),
                )
            )

    # Fallback with nothing measured: the weakest foundations the most competencies require.
    if not candidates:
        need: dict[str, int] = {}
        for c in cmap.competencies:
            for f in c.requires:
                if f in foundations and foundations[f].p < KNOWN:
                    need[f] = need.get(f, 0) + 1
        ranked = sorted(need, key=lambda f: (-need[f], foundations[f].p, f))
        for f in ranked:
            candidates.append(
                Activity(
                    "learn_foundation",
                    f,
                    _trace(
                        f,
                        at,
                        "recommend.fallback_shared_foundation",
                        f"Chưa đo được kỹ năng thi nào: học {name(f) or f} "
                        f"({fmt_p(foundations[f].p)}), "
                        f"nền tảng mà {need[f]} kỹ năng thi cần.",
                        foundations[f].p,
                    ),
                )
            )
        if ranked:
            notes.append("nothing measured: shared foundations first")

    # 5. Balance while filling the list.
    weeks_left = (cmap.target.exam_date - today).days / 7
    exam_min = 2 if weeks_left <= FINAL_WEEKS else 1
    seen = {(a.kind, a.target) for a in out}
    in_a_row = 0
    for a in candidates:
        if len(out) >= n:
            break
        if (a.kind, a.target) in seen:
            continue
        exam_so_far = sum(x.kind in EXAM_STYLE for x in out)
        slots_left = n - len(out)
        exam_possible = any(
            c.kind in EXAM_STYLE for c in candidates if (c.kind, c.target) not in seen
        )
        if a.kind == "learn_foundation":
            if in_a_row >= cmap.balance.foundations_in_a_row_max:
                continue
            if exam_possible and exam_so_far < exam_min and slots_left <= exam_min - exam_so_far:
                continue  # keep room for the exam-style activities still owed today
            in_a_row += 1
        else:
            in_a_row = 0
        out.append(a)
        seen.add((a.kind, a.target))
    return Today(out, notes)
