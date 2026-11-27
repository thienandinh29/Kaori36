"""The summary across pasted Reading tests: per type and pacing (step 4.3d part 2)."""

from app.reading.own_summary import Answer, by_kind, late_numbers, pacing, summary


def a(
    fp: str,
    n: int,
    *,
    correct: bool = True,
    kind: str = "tfng",
    blank: bool = False,
    trap: str | None = None,
    mark: str | None = None,
    position: int | None = 1,
) -> Answer:
    return Answer(fp, n, kind, correct, blank, trap, mark, position)  # type: ignore[arg-type]


def test_late_numbers_are_the_last_third_of_a_passage() -> None:
    assert late_numbers(list(range(1, 14))) == frozenset({10, 11, 12, 13})
    assert late_numbers([27, 28, 29, 30, 31, 32]) == frozenset({31, 32})
    assert late_numbers([1, 2]) == frozenset()


def test_by_kind_counts_score_and_top_trap_but_not_a_guess_trap() -> None:
    rows = [a("t", i) for i in range(1, 5)] + [
        a("t", 5, correct=False, trap="false_for_not_given"),
        a("t", 6, correct=False, trap="false_for_not_given"),
        a("t", 7, correct=False, trap="not_given_for_false", mark="guessed"),
        a("t", 8, correct=False, trap="true_for_false"),
        a("t", 9, kind="mcq"),
    ]
    tf, mcq = by_kind(rows)
    assert (tf["answers"], tf["wrong"], tf["enough"]) == (8, 4, True)
    assert tf["right"]["k"] == 4 and tf["right"]["low"] < 0.5 < tf["right"]["high"]
    assert tf["top_trap"] == {"trap": "false_for_not_given", "count": 2, "of": 3}  # guess left out
    assert mcq["enough"] is False and mcq["top_trap"] is None


def _test(fp: str, late_wrong: int, *, marked: int, position: int = 1) -> list[Answer]:
    """12 questions; `late_wrong` of the last 4 wrong (the first `marked` of them marked)."""
    rows = [a(fp, n, position=position) for n in range(1, 9)]
    for i, n in enumerate(range(9, 13)):
        wrong = i < late_wrong
        rows.append(a(fp, n, correct=not wrong, position=position,
                      mark="no_time" if wrong and i < marked else None))  # fmt: skip
    return rows


def test_pacing_needs_three_tests_and_a_passage_three() -> None:
    two = _test("a", 4, marked=4) + _test("b", 4, marked=4, position=3)
    assert pacing(two)["status"] == "not_enough"
    no_third = _test("a", 4, marked=4) + _test("b", 4, marked=4) + _test("c", 4, marked=4)
    assert pacing(no_third)["status"] == "not_enough"


def test_pacing_says_maybe_time_only_when_late_errors_are_high_and_marked() -> None:
    rows = _test("a", 3, marked=2) + _test("b", 3, marked=2) + _test("c", 3, marked=2, position=3)
    p = pacing(rows)
    # Passage 3 counts as late as a whole: its first 8 are right, so the gap is diluted but clear.
    assert p["late"] == {"wrong": 9, "n": 20} and p["rest"] == {"wrong": 0, "n": 16}
    assert p["late_wrong_marked"] == 6 and p["status"] == "maybe_time"
    unmarked = _test("a", 3, marked=0) + _test("b", 3, marked=0) + _test("c", 3, marked=0,
                                                                         position=3)  # fmt: skip
    assert pacing(unmarked)["status"] == "counts_only"  # late errors, but nothing says time
    even = _test("a", 0, marked=0) + _test("b", 0, marked=0) + _test("c", 0, marked=0, position=3)
    assert pacing(even)["status"] == "counts_only"


def test_a_blank_late_answer_counts_as_a_sign_of_time() -> None:
    rows = []
    for fp, pos in (("a", 1), ("b", 2), ("c", 3)):
        rows += [a(fp, n, position=pos) for n in range(1, 9)]
        rows += [a(fp, n, correct=False, blank=True, position=pos) for n in range(9, 13)]
    assert pacing(rows)["status"] == "maybe_time"


def test_summary_shape() -> None:
    s = summary([a("x", 1), a("y", 1, correct=False)])
    assert (s["tests"], s["answers"]) == (2, 2)
    assert s["pacing"]["status"] == "not_enough" and s["thresholds"]["gap"] == 0.2
    assert summary([])["by_kind"] == []
