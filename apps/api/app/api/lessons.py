"""Lesson routes (specs/grammar-lessons): the list, one lesson without its keys, checkpoint answers.

Sample and draft lessons are served only to the learners in DRAFT_ITEM_LEARNERS, labelled; a
checkpoint answer is graded by key and returned, and is not mastery evidence (aided; phase D).
"""

from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.lessons.model import Lesson
from app.lessons.store import LessonStore
from app.services.backend import learner_uuid

SLUG = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class LessonSummary(BaseModel):
    node: str
    level: str
    status: str
    title_en: str
    title_vi: str


class SourceOut(BaseModel):
    candidate: str
    chapter: str
    licence: str


class LessonOut(BaseModel):
    node: str
    course: str
    level: str
    status: str  # sample | draft | reviewed: the page labels the first two
    title_en: str
    title_vi: str
    noncommercial: bool
    sources: list[SourceOut]
    scenes: list[dict[str, Any]]
    checkpoints: list[dict[str, Any]]  # question and option texts only, never the key


class CheckpointIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    learner_id: str = Field(min_length=1, max_length=200)
    course: str = Field(default="english-ielts", min_length=1, max_length=40, pattern=SLUG)
    checkpoint: str = Field(min_length=1, max_length=80, pattern=SLUG)
    answer: str = Field(max_length=100)


class CheckpointOut(BaseModel):
    correct: bool
    key: str
    explain_vi: str
    misconception_vi: str | None
    evidence: bool = False  # aided: not counted towards mastery


def lesson_out(lesson: Lesson) -> LessonOut:
    return LessonOut(
        node=lesson.node,
        course=lesson.course,
        level=lesson.level,
        status=lesson.status,
        title_en=lesson.title_en,
        title_vi=lesson.title_vi,
        noncommercial=lesson.noncommercial,
        sources=[SourceOut(**s.model_dump()) for s in lesson.sources],
        scenes=[
            {
                "id": s.id,
                "kind": s.kind,
                "misconceptions": list(s.misconceptions),
                "actions": [a.model_dump() for a in s.actions],
            }
            for s in lesson.scenes
        ],
        checkpoints=[
            {"id": c.id, "en": c.en, "vi": c.vi, "options": [o.text for o in c.options]}
            for c in lesson.checkpoints
        ],
    )


def create_router(
    stores: Mapping[str, LessonStore],
    draft_learners: str,
    misconceptions: Mapping[str, str],
) -> APIRouter:
    router = APIRouter(prefix="/lessons", tags=["lessons"])
    drafts = {learner_uuid(x.strip()) for x in draft_learners.split(",") if x.strip()}

    def store(course: str) -> LessonStore:
        if course not in stores:
            raise HTTPException(404, "Không tìm thấy khóa học.")
        return stores[course]

    def lesson(course: str, node: str, learner_id: str) -> Lesson:
        found = store(course).visible(node, include_drafts=learner_uuid(learner_id) in drafts)
        if found is None:
            raise HTTPException(404, "Phần này chưa có bài học.")
        return found

    @router.get("", response_model=list[LessonSummary])
    def list_lessons(
        learner_id: str = Query(min_length=1, max_length=200),
        course: str = Query(default="english-ielts", max_length=40, pattern=SLUG),
    ) -> list[LessonSummary]:
        include = learner_uuid(learner_id) in drafts
        out = []
        for node in store(course).lessons:
            ls = store(course).visible(node, include_drafts=include)
            if ls is not None:
                out.append(LessonSummary(node=ls.node, level=ls.level, status=ls.status,
                                         title_en=ls.title_en, title_vi=ls.title_vi))  # fmt: skip
        return out

    @router.get("/{node}", response_model=LessonOut)
    def get_lesson(
        node: str,
        learner_id: str = Query(min_length=1, max_length=200),
        course: str = Query(default="english-ielts", max_length=40, pattern=SLUG),
    ) -> LessonOut:
        return lesson_out(lesson(course, node, learner_id))

    @router.post("/{node}/checkpoints", response_model=CheckpointOut)
    def answer_checkpoint(node: str, body: CheckpointIn) -> CheckpointOut:
        found = lesson(body.course, node, body.learner_id)
        c = found.checkpoint(body.checkpoint)
        if c is None:
            raise HTTPException(404, "Không tìm thấy câu hỏi.")
        chosen = next((o for o in c.options if o.text == body.answer), None)
        if chosen is None:
            raise HTTPException(422, "Câu trả lời không nằm trong các lựa chọn.")
        return CheckpointOut(
            correct=chosen.correct,
            key=c.key,
            explain_vi=c.explain_vi,
            misconception_vi=misconceptions.get(chosen.misconception or ""),
        )

    return router
