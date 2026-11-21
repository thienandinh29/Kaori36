"""Feedback stability: matching points across runs and the scores (specs/writing/step-2.11.md)."""

from typing import Any

from app.evalkit import feedback_stability as fs
from app.writing.feedback import CriterionOut, FeedbackOut, PointOut

ESSAY = (
    "Many people think that cities should ban cars. In my opinion this is a good idea. "
    "She go to school by bus every day, and the air is cleaner."
)


def found(c: str, kind: str, *quotes: str) -> fs.Found:
    return fs.Found(c, kind, quotes)


def test_the_same_point_is_matched_by_criterion_kind_and_quote() -> None:
    a = found("gra", "issue", "She go to school")
    assert fs.same_point(a, found("gra", "issue", "She go to school by bus every day"))
    assert fs.same_point(a, found("gra", "issue", "she go to school"))  # case and spacing
    assert not fs.same_point(a, found("lr", "issue", "She go to school"))  # another criterion
    assert not fs.same_point(a, found("gra", "strength", "She go to school"))
    assert not fs.same_point(a, found("gra", "issue", "the air is cleaner"))


def test_per_essay_shares_are_split_by_kind_with_intervals() -> None:
    issue = found("gra", "issue", "She go to school")
    other = found("tr", "issue", "this is a good idea")
    strength = found("cc", "strength", "In my opinion")
    runs = [[issue, strength], [issue, other, strength], [strength]]
    s = fs.essay_stability(runs, "issue")
    # issue is in runs 1 and 2 (2 recurring); other only once: 2 of 3 issue points recur
    assert (s["points"], s["recurring"], s["share"]) == (3, 2, 0.667)
    assert s["interval"][0] < 0.667 < s["interval"][1]
    assert s["points_per_run"] == [1, 2, 0]
    st = fs.essay_stability(runs, "strength")
    assert (st["points"], st["recurring"], st["share"], st["pairwise_jaccard"]) == (3, 3, 1.0, 1.0)


def test_an_essay_with_no_points_of_a_kind_has_no_share() -> None:
    s = fs.essay_stability([[], [], []], "issue")
    assert s["share"] is None and s["interval"] is None and s["pairwise_jaccard"] is None


def test_the_summary_keeps_kinds_apart_and_states_the_decision() -> None:
    per_essay: list[dict[str, Any]] = [
        {"issue": {"share": 0.4}, "strength": {"share": 0.9}},
        {"issue": {"share": 0.5}, "strength": {"share": 1.0}},
        {"issue": {"share": 0.6}, "strength": {"share": None}},
    ]
    s = fs.summarise(per_essay)
    assert s["issue"]["mean_share"] == 0.5 and s["issue"]["essays"] == 3
    assert s["strength"]["essays"] == 2
    lo, hi = s["issue"]["interval"]
    assert lo <= 0.5 <= hi
    assert s["decision"] == "keep only issues recurring in 2 of 3 runs"


def reply(quote: str) -> FeedbackOut:
    point = PointOut(kind="issue", point_vi="Động từ chưa chia theo chủ ngữ.", quotes=[quote])
    keep = CriterionOut(band=6.0, points=[point])
    return FeedbackOut(tr=keep, cc=keep, lr=keep, gra=keep)


def test_measure_uses_the_apps_prompt_and_verify_and_stops_at_the_cap() -> None:
    essays = [fs.Essay("e1", "Should cities ban cars?", ESSAY, "web"),
              fs.Essay("e2", "Should cities ban cars?", ESSAY, "web")]  # fmt: skip
    sent: list[str] = []
    replies = iter([reply("She go to school"), reply("words not in the essay"),
                    reply("She go to school")])  # fmt: skip

    def ask(system: str, user: str) -> FeedbackOut | None:
        sent.append(user)
        return next(replies, None)

    budget = iter([True, True, True, False, False, False, False])
    out = fs.measure(essays, ask, {}, 3, lambda: next(budget))
    assert "<<<" in sent[0] and "Should cities ban cars?" in sent[0]
    first = out[0]
    assert first["runs"] == 3
    # run 2's quote is not in the essay, so verify drops its points (as in the app)
    assert first["issue"]["points_per_run"] == [3, 0, 3]
    assert out[1]["skipped"] == "0 usable runs"
    assert len(out) == 2
