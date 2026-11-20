"""Errors a learner repeats across essays (specs/writing/step-2.8.md). Pure: stored results only."""

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

MIN_ESSAYS = 2
TOP = 5
RECENT = 3


@dataclass(frozen=True)
class Pattern:
    key: str  # grammar node, else ERRANT type
    node: str | None
    name_vi: str | None
    essays: int
    errors: int
    in_latest: bool  # in the most recent analysed essay
    recent: int  # how many of the latest RECENT essays had it
    example: str  # the last sentence it was found in
    suggestion: str | None

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def patterns(results: Sequence[Mapping[str, Any]]) -> list[Pattern]:
    """`results`: analysed essays' results, newest first."""
    seen: dict[str, dict[str, Any]] = {}
    for rank, result in enumerate(results):
        issues = ((result.get("grammar") or {}).get("issues")) or []
        here: set[str] = set()
        for i in issues:
            if i.get("source", "languagetool") != "languagetool":
                continue  # AI suggestions are never a pattern
            key = i.get("node") or i.get("errant_type")
            if not key:
                continue
            g = seen.setdefault(key, {"essays": set(), "errors": 0, "first": None, "item": i})
            g["errors"] += 1
            here.add(key)
            if g["first"] is None:
                g["first"], g["item"] = rank, i  # the newest example
        for key in here:
            seen[key]["essays"].add(rank)
    out = [
        Pattern(
            key=key,
            node=g["item"].get("node"),
            name_vi=g["item"].get("node_vi"),
            essays=len(g["essays"]),
            errors=g["errors"],
            in_latest=0 in g["essays"],
            recent=sum(1 for r in g["essays"] if r < RECENT),
            example=g["item"].get("sentence", ""),
            suggestion=g["item"].get("suggestion"),
        )
        for key, g in seen.items()
        if len(g["essays"]) >= MIN_ESSAYS
    ]
    return sorted(out, key=lambda p: (-p.essays, -p.errors, p.key))[:TOP]
