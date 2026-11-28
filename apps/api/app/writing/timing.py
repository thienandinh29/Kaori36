"""Seconds spent in each stage of an essay's analysis (step 2.1's worker job).

The numbers go into the stored result under `_timings` (a key that starts with an underscore is
never sent to the browser) and into one log line per essay. They answer one question: where does
the time between "submitted" and "done" go, so that the web page's polling limit and any
parallelism are decided from measurements. Wall-clock seconds on the worker, not a quality measure.
"""

import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

KEY = "_timings"


@contextmanager
def timed(result: dict[str, Any], stage: str) -> Iterator[None]:
    """Add the seconds this block takes to `result["_timings"][stage]`, even if it raises."""
    start = time.perf_counter()
    try:
        yield
    finally:
        stages: dict[str, float] = result.setdefault(KEY, {})
        stages[stage] = round(stages.get(stage, 0.0) + time.perf_counter() - start, 3)
