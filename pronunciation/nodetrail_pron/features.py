"""Per-phone features for a learned mispronunciation detector (step 3.5a).

Pure: computed from the recogniser's per-frame log-probabilities and one aligned segment. GOP alone
is one number; these add how sure the model was of the expected phone and how long it lasted.
"""

import math
from collections.abc import Sequence

from nodetrail_pron.align import Segment

NAMES = ("gop", "lpp", "min_diff", "best_share", "log_frames")


def phone_features(log_probs: Sequence[Sequence[float]], seg: Segment, blank: int) -> list[float]:
    """[GOP, mean log P(expected), worst frame's margin, share of frames it wins, log duration]."""
    diffs, lps, wins = [], [], 0
    for f in range(seg.start, seg.end):
        row = log_probs[f]
        best = max(p for k, p in enumerate(row) if k not in (blank, seg.token))
        diffs.append(row[seg.token] - best)
        lps.append(row[seg.token])
        wins += row[seg.token] >= best
    n = len(diffs)
    return [sum(diffs) / n, sum(lps) / n, min(diffs), wins / n, math.log(n)]
