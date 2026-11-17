import math

import pytest

from nodetrail_pron.align import AlignmentError, align, gop, greedy

B, A, C, D = 0, 1, 2, 3  # blank and three phones


def rows(*best: int, p: float = 0.9) -> list[list[float]]:
    """Frames where `best` is likely and the rest share what is left (log-probabilities)."""
    out = []
    for b in best:
        rest = (1 - p) / 3
        out.append([math.log(p if k == b else rest) for k in range(4)])
    return out


def test_alignment_follows_the_frames() -> None:
    lp = rows(B, A, A, B, C, C, C, B)
    segs = align(lp, [A, C])
    assert [(s.token, s.start, s.end) for s in segs] == [(A, 1, 3), (C, 4, 7)]


def test_a_repeated_phone_needs_a_blank_between() -> None:
    lp = rows(A, B, A)
    segs = align(lp, [A, A])
    assert [(s.start, s.end) for s in segs] == [(0, 1), (2, 3)]
    with pytest.raises(AlignmentError):
        align(rows(A, A), [A, A, A])  # three phones, two frames


def test_gop_is_zero_when_the_canonical_phone_wins_and_negative_with_a_competitor() -> None:
    lp = rows(B, A, A, B, D, D, B)  # the learner said D where C was expected
    segs = align(lp, [A, C])
    scores = gop(lp, segs)
    assert scores[0].gop == pytest.approx(math.log(0.9 / (0.1 / 3)), abs=1e-3)
    assert scores[0].competitor is None
    assert scores[1].gop < 0 and scores[1].competitor == D


def test_greedy_merges_repeats_and_drops_blanks() -> None:
    assert greedy(rows(B, A, A, B, A, C, C)) == [A, A, C]
