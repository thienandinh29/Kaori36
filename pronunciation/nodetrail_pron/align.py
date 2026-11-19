"""CTC forced alignment and goodness of pronunciation, as plain code (step 3.2).

Input is the recogniser's per-frame log-probabilities (rows: 20 ms frames, columns: phone tokens,
column `blank` the CTC blank). No model here: tested on small hand-made matrices.

Alignment finds the most likely path through "blank, phone 1, blank, phone 2, ..., blank" (the
standard CTC trellis, Viterbi). Each canonical phone gets the frames where the path emits it.

GOP for a phone is the mean, over its frames, of log P(canonical) minus the log-probability of the
best non-blank competitor; 0 means the canonical phone was the most likely, below 0 that another
phone was more likely. The competitor is the phone most often best in those frames.

For dropped sounds (step 3.6b) each score also has `peak`, the highest probability of the
canonical phone in its frames, and `other_peak`, the highest probability of any other phone there
(blank and the neighbouring canonical phones left out). Alignment gives every canonical phone at
least one frame even when it was never said; then neither peaks: the frames are blank or belong
to a neighbour. GOP alone misses this, because it compares only phones and ignores blank.
"""

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

Matrix = Sequence[Sequence[float]]
NEG = -math.inf


class AlignmentError(ValueError):
    """The audio is too short for the phones (fewer usable frames than the path needs)."""


@dataclass(frozen=True)
class Segment:
    token: int
    start: int  # first frame (inclusive)
    end: int  # last frame (exclusive)


@dataclass(frozen=True)
class PhoneScore:
    token: int
    start: int
    end: int
    gop: float
    competitor: int | None  # the best other phone in these frames; None when the canonical one wins
    peak: float = 1.0  # highest P(canonical phone) in these frames
    other_peak: float = 0.0  # highest P(another phone), blank and neighbours left out


def align(log_probs: Matrix, tokens: Sequence[int], blank: int = 0) -> list[Segment]:
    """The Viterbi CTC alignment of `tokens` to the frames: one segment per token, in order."""
    frames, n = len(log_probs), len(tokens)
    if n == 0:
        return []
    states = [blank]
    for t in tokens:
        states += [t, blank]
    s_count = len(states)
    # a repeated token needs a blank between its two copies
    need = n + sum(1 for a, b in pairwise(tokens) if a == b)
    if frames < need:
        raise AlignmentError(f"{frames} frames for {n} phones")
    score = [[NEG] * s_count for _ in range(frames)]
    back = [[0] * s_count for _ in range(frames)]
    score[0][0] = log_probs[0][states[0]]
    score[0][1] = log_probs[0][states[1]]
    for f in range(1, frames):
        row, prev = log_probs[f], score[f - 1]
        for s in range(s_count):
            best, arg = prev[s], s
            if s >= 1 and prev[s - 1] > best:
                best, arg = prev[s - 1], s - 1
            # skip a blank between two different phones
            if s >= 2 and states[s] != blank and states[s] != states[s - 2] and prev[s - 2] > best:
                best, arg = prev[s - 2], s - 2
            if best > NEG:
                score[f][s] = best + row[states[s]]
                back[f][s] = arg
    last = frames - 1
    s = s_count - 1 if score[last][s_count - 1] >= score[last][s_count - 2] else s_count - 2
    if score[last][s] == NEG:
        raise AlignmentError("no path through the phones")
    path = [0] * frames
    for f in range(last, -1, -1):
        path[f] = s
        s = back[f][s]
    segments: list[Segment] = []
    for i in range(n):
        state = 2 * i + 1
        fr = [f for f, st in enumerate(path) if st == state]
        segments.append(Segment(tokens[i], fr[0], fr[-1] + 1))
    return segments


def gop(log_probs: Matrix, segments: Sequence[Segment], blank: int = 0) -> list[PhoneScore]:
    out = []
    for i, seg in enumerate(segments):
        neighbours = {s.token for s in segments[max(0, i - 1) : i + 2]} - {seg.token}
        peak = other_peak = NEG
        diffs, winners = [], Counter[int]()
        for f in range(seg.start, seg.end):
            row = log_probs[f]
            best = max((p, k) for k, p in enumerate(row) if k not in (blank, seg.token))
            diffs.append(row[seg.token] - best[0])
            if best[0] > row[seg.token]:
                winners[best[1]] += 1
            peak = max(peak, row[seg.token])
            others = [p for k, p in enumerate(row) if k not in (blank, seg.token, *neighbours)]
            other_peak = max([other_peak, *others])
        mean = sum(diffs) / len(diffs)
        competitor = winners.most_common(1)[0][0] if winners and mean < 0 else None
        out.append(
            PhoneScore(
                seg.token,
                seg.start,
                seg.end,
                round(mean, 3),
                competitor,
                round(math.exp(peak), 3),
                round(math.exp(other_peak), 3),
            )
        )
    return out


def greedy(log_probs: Matrix, blank: int = 0) -> list[int]:
    """The recognised tokens: best token per frame, repeats merged, blanks removed."""
    out: list[int] = []
    previous = blank
    for row in log_probs:
        k = max(range(len(row)), key=row.__getitem__)
        if k != blank and k != previous:
            out.append(k)
        previous = k
    return out
