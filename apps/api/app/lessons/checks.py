"""Every rule a lesson must pass before it is served (specs/grammar-lessons, "Checks by code").

Pure: the course, the item bank, the misconceptions, the word index and the verified sources come in
as arguments, so the checks run in CI and in the generation pipeline alike.
"""

import re
import unicodedata
from collections.abc import Collection, Mapping

from app.curriculum.course import CourseSpec
from app.curriculum.items import ItemBank
from app.lessons.graded import WordIndex, off_level, too_long
from app.lessons.model import WAITS, Ask, Lesson, Say, ShowExample, Spotlight
from app.vocabulary.wordlist import occurrences

WORDS_PER_SECOND = 2.2  # unhurried speech for learners
SECONDS = {"show_example": 3.0, "pause": 4.0, "ask": 12.0}
MIN_SECONDS, MAX_SECONDS = 90, 240
CITED_KINDS = frozenset({"notice", "form", "contrast"})


def _plain(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9' ]+", " ", text.lower()).split())


def seconds(lesson: Lesson) -> float:
    """Estimated playing time: speech at a learner's pace plus time for cards, pauses and checks."""
    total = 0.0
    for scene in lesson.scenes:
        for a in scene.actions:
            if isinstance(a, Say):
                total += len(a.en.split()) / WORDS_PER_SECOND
            elif isinstance(a, Ask):
                c = lesson.checkpoint(a.checkpoint)
                total += SECONDS["ask"] + (len(c.en.split()) / WORDS_PER_SECOND if c else 0)
            else:
                total += SECONDS.get(a.do, 0.0)
                if isinstance(a, ShowExample):
                    total += len(a.en.split()) / WORDS_PER_SECOND
    return total


def check_lesson(
    lesson: Lesson,
    course: CourseSpec,
    bank: ItemBank | None,
    misconceptions: Mapping[str, str],
    words: WordIndex,
    verified_sources: Collection[str],
) -> list[str]:
    p: list[str] = []
    concept = next((c for c in course.concepts if c.slug == lesson.node), None)
    if lesson.course != course.slug:
        p.append(f"course {lesson.course} is not {course.slug}")
    if concept is None:
        return [*p, f"unknown node {lesson.node}"]
    if concept.level != lesson.level:
        p.append(f"level {lesson.level} is not the node's level {concept.level}")

    # examples, spotlights, checkpoints: in playing order
    shown: dict[str, ShowExample] = {}
    asked: set[str] = set()
    for scene in lesson.scenes:
        for a in scene.actions:
            if isinstance(a, ShowExample):
                shown[a.id] = a
                if not occurrences(a.target, a.en):
                    p.append(f"example {a.id}: the target {a.target!r} is not in {a.en!r}")
            elif isinstance(a, Spotlight) and a.example not in shown:
                p.append(
                    f"scene {scene.id}: spotlight on {a.example}, which is not shown before it"
                )
            elif isinstance(a, Ask):
                if lesson.checkpoint(a.checkpoint) is None:
                    p.append(f"scene {scene.id}: unknown checkpoint {a.checkpoint}")
                asked.add(a.checkpoint)
        if not any(a.do in WAITS for a in scene.actions):
            p.append(f"scene {scene.id}: nothing to listen to or answer")
    for c in lesson.checkpoints:
        if c.id not in asked:
            p.append(f"checkpoint {c.id} is never asked")

    # misconceptions named anywhere must be explained for the learner
    named = {m for s in lesson.scenes for m in s.misconceptions} | {
        o.misconception for c in lesson.checkpoints for o in c.options if o.misconception
    }
    p += [f"unknown misconception {m}" for m in sorted(named - set(misconceptions))]

    # graded narration (what Sena says and asks)
    spoken = [a.en for s in lesson.scenes for a in s.actions if isinstance(a, Say)]
    spoken += [c.en for c in lesson.checkpoints]
    off: list[str] = []
    for text in spoken:
        allowed = (*lesson.terms, *lesson.names)
        off += [w for w in off_level(text, lesson.level, words, allowed) if w not in off]
        p += [f"sentence too long for {lesson.level}: {s!r}" for s in too_long(text, lesson.level)]
    if off:
        p.append(f"words above {lesson.level} or not in the word list: {', '.join(off)}")

    # Vietnamese text is stored composed (NFC)
    vi = [a.vi for s in lesson.scenes for a in s.actions if isinstance(a, Say | ShowExample)]
    vi += [t for c in lesson.checkpoints for t in (c.vi, c.explain_vi)] + [lesson.title_vi]
    if any(unicodedata.normalize("NFC", t) != t for t in vi):
        p.append("Vietnamese text must be NFC")

    # the lesson never gives away a test question
    if bank is not None:
        lesson_texts = [_plain(e.en) for e in shown.values()] + [
            _plain(c.en) for c in lesson.checkpoints
        ]
        for item in bank.items:
            filled = _plain(item.prompt.replace("___", item.key))
            stem = _plain(item.prompt.replace("___", " "))
            for t in lesson_texts:
                if filled in t or t == stem:
                    p.append(f"lesson text repeats test item {item.id}")
                    break

    duration = seconds(lesson)
    if not MIN_SECONDS <= duration <= MAX_SECONDS:
        p.append(f"estimated length {duration:.0f} s is outside {MIN_SECONDS}-{MAX_SECONDS} s")

    # citations: a sample may have none; every real lesson cites verified sources
    if lesson.status != "sample":
        if not lesson.sources:
            p.append("a lesson needs its sources")
        p += [f"source {s.candidate} is not verified" for s in lesson.sources
              if s.candidate not in verified_sources]  # fmt: skip
        p += [f"scene {s.id} ({s.kind}) cites no chunk" for s in lesson.scenes
              if s.kind in CITED_KINDS and not s.cites]  # fmt: skip
    return p
