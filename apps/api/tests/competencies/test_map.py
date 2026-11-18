"""Two maps, M1: the competency map, its checker, vocabulary bands (specs/two-layer-map)."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.competencies.bands import STABLE_DAYS, band_of, bands
from app.competencies.check import Foundations, check, load_foundations
from app.competencies.model import CompetencyMap, load_map


def make(competencies: list[dict[str, object]]) -> CompetencyMap:
    return CompetencyMap.model_validate({
        "status": "proposed",
        "target": {"overall": 7.0, "exam_date": "2027-07-01"},
        "balance": {"review_share_max": 0.34, "foundations_in_a_row_max": 2},
        "competencies": competencies,
    })  # fmt: skip


def comp(slug: str, *links: tuple[str, str]) -> dict[str, object]:
    return {"slug": slug, "skill": "writing", "name_vi": "x", "name_en": "x",
            "links": [{"node": n, "kind": k} for n, k in links]}  # fmt: skip


def test_the_real_map_checks_clean() -> None:
    m = load_map()
    assert m.target.overall == 7.0 and m.target.exam_date == date(2027, 7, 1)
    report = check(m, load_foundations())
    assert report.errors == []
    assert {c.skill for c in m.competencies} == {"reading", "listening", "writing", "speaking"}


def test_checker_errors_and_not_live() -> None:
    f = Foundations(frozenset({"articles-basic", "vocab-b1"}), frozenset({"linking-ideas"}))
    m = make([
        comp("a", ("articles-basic", "requires"), ("linking-ideas", "helps")),
        comp("b", ("vocab-b1", "helps")),
        comp("c", ("nowhere", "requires")),
        comp("d", ("a", "requires")),
    ])  # fmt: skip
    r = check(m, f)
    assert r.not_live == {"a": ["linking-ideas"]}
    assert r.errors == [
        "b: no `requires` foundation",
        "c: unknown foundation nowhere",
        "d: links to the competency a (only foundations)",
    ]


def test_model_rejects_duplicates_and_bad_targets() -> None:
    with pytest.raises(ValidationError):
        make([comp("a", ("x", "requires")), comp("a", ("y", "requires"))])
    with pytest.raises(ValidationError):
        make([comp("a", ("x", "requires"), ("x", "helps"))])
    with pytest.raises(ValidationError):
        CompetencyMap.model_validate({
            "status": "proposed", "target": {"overall": 7.2, "exam_date": "2027-07-01"},
            "balance": {"review_share_max": 0.34, "foundations_in_a_row_max": 2},
            "competencies": [comp("a", ("x", "requires"))],
        })  # fmt: skip


def test_vocabulary_bands_from_card_stability() -> None:
    assert band_of("B2", "ngsl") == "vocab-b2" and band_of("B2", "nawl") == "vocab-nawl"
    words = [("a:noun", "B1", "ngsl"), ("b:verb", "B1", "authored"), ("c:noun", "B1", "ngsl"),
             ("d:adj", "B1", "ngsl"), ("e:noun", "C1", "nawl")]  # fmt: skip
    got = bands(words, {"a:noun": STABLE_DAYS, "b:verb": 3.0, "e:noun": 40.0})
    b1 = got["vocab-b1"]
    assert (b1.words, b1.reviewed, b1.stable, b1.p) == (4, 2, 1, 0.25)
    assert got["vocab-nawl"].p == 1.0 and "vocab-c1" not in got
