"""Check the competency map against the foundations that exist (specs/two-layer-map/spec.md).

    uv run python -m app.competencies.check

Errors: a link to a foundation that exists nowhere, a link to another competency (so no cycles), a
competency with no `requires` link. A link to a node of the proposed grammar path is accepted as
"not live yet": the engine ignores it until the node is in the live course.
"""

import json
from collections.abc import Collection
from dataclasses import dataclass, field
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from app.competencies.model import VOCAB_BANDS, CompetencyMap, load_map
from app.config import REPO_ROOT

COURSES = REPO_ROOT / "data" / "courses"
PROPOSED_PATH = REPO_ROOT / "specs" / "grammar-lessons" / "english-ielts-path.yaml"


@dataclass(frozen=True)
class Foundations:
    live: frozenset[str]  # grammar and pronunciation nodes in live courses, and vocabulary bands
    proposed: frozenset[str] = field(default_factory=frozenset)  # only in the proposed path


@dataclass(frozen=True)
class Report:
    errors: list[str]
    not_live: dict[str, list[str]]  # competency -> foundations not live yet


def check(m: CompetencyMap, f: Foundations) -> Report:
    errors: list[str] = []
    not_live: dict[str, list[str]] = {}
    slugs = {c.slug for c in m.competencies}
    for c in m.competencies:
        if not c.requires:
            errors.append(f"{c.slug}: no `requires` foundation")
        for link in c.links:
            if link.node in slugs:
                errors.append(f"{c.slug}: links to the competency {link.node} (only foundations)")
            elif link.node in f.live:
                continue
            elif link.node in f.proposed:
                not_live.setdefault(c.slug, []).append(link.node)
            else:
                errors.append(f"{c.slug}: unknown foundation {link.node}")
    return Report(errors, not_live)


def _slugs(path: Path) -> set[str]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {str(x["slug"]) for x in raw.get("concepts", [])}


def load_foundations(
    courses: Collection[str] = ("english-ielts", "english-pronunciation"),
) -> Foundations:
    live = set(VOCAB_BANDS)
    for slug in courses:
        live |= _slugs(COURSES / f"{slug}.yaml")
    proposed = _slugs(PROPOSED_PATH) - live if PROPOSED_PATH.is_file() else set()
    return Foundations(frozenset(live), frozenset(proposed))


def main() -> int:  # pragma: no cover - files
    r = check(load_map(), load_foundations())
    print(json.dumps({"errors": r.errors, "not_live_yet": r.not_live}, indent=2))
    return 1 if r.errors else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
