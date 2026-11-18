"""Two maps, M2: the recommendation engine's rules (specs/two-layer-map/spec.md)."""

from datetime import UTC, date, datetime

from app.competencies.model import CompetencyMap
from app.engine.recommend import Estimate, recommend, size

AT = datetime(2026, 12, 1, 8, 0, tzinfo=UTC)
TODAY = date(2026, 12, 1)
ALL = frozenset({"reading", "listening", "writing", "speaking"})


def cmap(exam: str = "2027-07-01") -> CompetencyMap:
    def c(slug: str, skill: str, *req: str) -> dict[str, object]:
        return {
            "slug": slug,
            "skill": skill,
            "name_vi": slug,
            "name_en": slug,
            "links": [{"node": r, "kind": "requires"} for r in req],
        }

    return CompetencyMap.model_validate(
        {
            "status": "proposed",
            "target": {"overall": 7.0, "exam_date": exam},
            "balance": {"review_share_max": 0.34, "foundations_in_a_row_max": 2},
            "competencies": [
                c("w-gra", "writing", "conditionals", "articles"),
                c("w-lex", "writing", "vocab-b2"),
                c("r-detail", "reading", "vocab-b2"),
            ],
        }
    )


def e(p: float, n: int = 10) -> Estimate:
    return Estimate(p, n)


KNOWN_F = {"conditionals": e(0.95), "articles": e(0.95), "vocab-b2": e(0.95)}
KNOWN_C = {"w-gra": e(0.95), "w-lex": e(0.95), "r-detail": e(0.95)}


def kinds(today: object) -> list[tuple[str, str]]:
    return [(a.kind, a.target) for a in today.activities]  # type: ignore[attr-defined]


def test_size_from_minutes() -> None:
    assert [size(m) for m in (10, 30, 40, 50, 120)] == [3, 3, 4, 5, 5]


def test_reviews_first_but_capped() -> None:
    t = recommend(
        cmap(),
        KNOWN_F,
        KNOWN_C | {"w-gra": e(0.5)},
        {"vocab": 30, "phrases": 4},
        ALL,
        TODAY,
        30,
        AT,
    )
    got = kinds(t)
    assert got[0] == ("review", "vocab") and ("review", "phrases") not in got  # cap: 1 of 3
    assert t.activities[0].trace.rule == "recommend.review_due"


def test_root_cause_to_the_weakest_clear_foundation() -> None:
    f = KNOWN_F | {"conditionals": e(0.52), "articles": e(0.70)}
    t = recommend(
        cmap(),
        f,
        KNOWN_C | {"w-gra": e(0.5)},
        {},
        ALL,
        TODAY,
        30,
        AT,
        {"conditionals": "Câu điều kiện loại 1-2", "w-gra": "Viết: ngữ pháp"},
    )
    first = t.activities[0]
    assert (first.kind, first.target, first.via) == ("learn_foundation", "conditionals", "w-gra")
    assert "Câu điều kiện loại 1-2 chưa chắc (0,52)" in first.trace.rule_vi
    assert [a.concept_slug for a in first.trace.alternatives] == ["articles"]


def test_a_borderline_foundation_is_not_the_cause() -> None:
    f = KNOWN_F | {"conditionals": e(0.86)}
    t = recommend(cmap(), f, KNOWN_C | {"w-gra": e(0.5)}, {}, ALL, TODAY, 30, AT)
    assert kinds(t)[0] == ("practise_competency", "w-gra")


def test_unmeasured_competency_gets_a_diagnostic_never_a_guess() -> None:
    cs = {"w-gra": e(0.5), "w-lex": e(0.95, 2)}  # w-lex has too little evidence; r-detail none
    t = recommend(cmap(), KNOWN_F, cs, {}, frozenset({"writing"}), TODAY, 30, AT)
    assert kinds(t)[0] == ("diagnostic", "w-lex")  # reading is not available: no diagnostic
    assert ("diagnostic", "r-detail") not in kinds(t)


def test_nothing_measured_falls_back_to_shared_foundations() -> None:
    f = {"vocab-b2": e(0.4), "conditionals": e(0.3), "articles": e(0.95)}
    t = recommend(cmap(), f, {}, {}, frozenset(), TODAY, 50, AT)
    # vocab-b2 is required by two competencies, conditionals by one: shared first.
    assert kinds(t)[:2] == [("learn_foundation", "vocab-b2"), ("learn_foundation", "conditionals")]
    assert t.notes == ["nothing measured: shared foundations first"]


def test_at_most_two_foundations_in_a_row_and_exam_style_kept() -> None:
    f = {"conditionals": e(0.3), "articles": e(0.95), "vocab-b2": e(0.4)}
    cs = {"w-gra": e(0.40), "w-lex": e(0.45), "r-detail": e(0.5)}
    t = recommend(cmap(), f, cs, {}, ALL, TODAY, 50, AT)
    got = kinds(t)
    run = best = 0
    for k, _ in got:
        run = run + 1 if k == "learn_foundation" else 0
        best = max(best, run)
    assert best <= 2
    assert len(set(got)) == len(got)  # no activity twice


def test_two_exam_style_activities_in_the_final_weeks() -> None:
    f = {"conditionals": e(0.3), "articles": e(0.95), "vocab-b2": e(0.95)}
    cs = {"w-gra": e(0.4), "w-lex": e(0.5), "r-detail": e(0.6)}
    late = recommend(cmap("2027-01-15"), f, cs, {}, ALL, TODAY, 30, AT)
    exam_style = [k for k, _ in kinds(late) if k in ("practise_competency", "diagnostic")]
    assert len(exam_style) >= 2
