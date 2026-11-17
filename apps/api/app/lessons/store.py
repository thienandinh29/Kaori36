"""Lessons on disk, checked on load: a broken lesson fails at start-up and in CI, not on a page."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from app.curriculum.course import CourseSpec, load_course
from app.curriculum.items import ItemBank, load_items
from app.lessons.checks import check_lesson
from app.lessons.graded import WordIndex, build_index
from app.lessons.model import Lesson
from app.services.grammar import load_misconceptions
from app.sources.candidates import load_candidates
from app.vocabulary.wordlist import load_wordlist


@dataclass(frozen=True)
class Paths:
    lessons: Path  # data/lessons
    courses: Path  # data/courses
    items: Path  # data/items
    forms: Path  # data-sa/vocabulary/forms.yaml
    vocabulary: Path  # data/vocabulary/core-seed.yaml (authored words count as known)
    candidates: Path  # data/sources/english-candidates.yaml


def load_lesson(path: Path) -> Lesson:
    return Lesson.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def word_index(paths: Paths) -> WordIndex:
    authored = load_wordlist(paths.vocabulary)
    return build_index(paths.forms, [(w.lemma, w.level) for w in authored.words])


class LessonStore:
    """Every lesson of a course, checked; empty when the course has no lessons folder."""

    def __init__(self, paths: Paths, course_slug: str) -> None:
        self.course: CourseSpec = load_course(paths.courses / f"{course_slug}.yaml")
        folder = paths.lessons / course_slug
        files = sorted(folder.glob("*.yaml")) if folder.is_dir() else []
        self.lessons: dict[str, Lesson] = {}
        if not files:
            return
        items = paths.items / f"{course_slug}.yaml"
        bank: ItemBank | None = load_items(items, self.course) if items.is_file() else None
        misconceptions: Mapping[str, str] = load_misconceptions(
            paths.items / "misconceptions.vi.yaml"
        )
        words = word_index(paths)
        verified = {c.slug for c in load_candidates(paths.candidates).usable()}
        problems: list[str] = []
        for f in files:
            lesson = load_lesson(f)
            if f.stem != lesson.node:
                problems.append(f"{f.name}: file name must be the node, {lesson.node}")
            problems += [f"{f.name}: {x}" for x in check_lesson(
                lesson, self.course, bank, misconceptions, words, verified)]  # fmt: skip
            self.lessons[lesson.node] = lesson
        if problems:
            raise ValueError("; ".join(problems))

    def visible(self, node: str, *, include_drafts: bool) -> Lesson | None:
        lesson = self.lessons.get(node)
        if lesson is None or (lesson.status != "reviewed" and not include_drafts):
            return None
        return lesson
