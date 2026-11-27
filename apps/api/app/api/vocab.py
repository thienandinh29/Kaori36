"""Vocabulary routes (specs/vocabulary): a session of due and new words, and answers."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field

from app.schemas import DecisionTrace
from app.services.vocabulary import (
    DEFAULT_LIMIT,
    DEFAULT_NEW_PER_DAY,
    MAX_ANSWER_CHARS,
    VocabPractice,
)
from app.vocabulary.items import LearnerItem, WordCard, card
from app.vocabulary.search import MAX_QUERY, search

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class VocabEntry(BaseModel):
    item: LearnerItem
    is_new: bool
    card: WordCard | None  # new words only: the word is taught before it is asked
    due_at: datetime | None


class VocabSession(BaseModel):
    entries: list[VocabEntry]
    due: int
    new_today: int
    new_left_today: int
    new_available: int  # new words not started yet at the chosen level(s)


class VocabSearch(BaseModel):
    """Dictionary search (specs/vocabulary/step-dictionary.md): cards from the word list."""

    status: Literal["draft", "reviewed"]
    total: int
    results: list[WordCard]


class VocabLevel(BaseModel):
    level: Literal["A1", "A2", "B1", "B2", "C1"]
    words: int
    started: int
    due: int


class VocabCheckInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_id: str = Field(min_length=1, max_length=200)
    answer: str = Field(max_length=MAX_ANSWER_CHARS)


class VocabCheckResult(BaseModel):
    """A retry's verdict: graded like an answer, never scheduled."""

    correct: bool
    accepted: str
    card: WordCard


class VocabTopic(BaseModel):
    slug: str
    name_vi: str
    words: int
    started: int


class VocabLevels(BaseModel):
    levels: list[VocabLevel]
    suggested: Literal["A1", "A2", "B1", "B2", "C1"]
    topics: list[VocabTopic]


class VocabAnswerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    learner_id: str = Field(min_length=1, max_length=200)
    item_id: str = Field(min_length=1, max_length=200)
    answer: str = Field(max_length=MAX_ANSWER_CHARS)


class VocabAnswerResult(BaseModel):
    correct: bool
    accepted: str
    card: WordCard
    due_at: datetime
    trace: DecisionTrace


def create_router(practice: VocabPractice) -> APIRouter:
    router = APIRouter(prefix="/vocab", tags=["vocabulary"])

    @router.get("/session")
    def session(
        learner_id: str = Query(min_length=1, max_length=200),
        list_slug: str = Query(
            default="core-seed", alias="list", min_length=1, max_length=40, pattern=SLUG_PATTERN
        ),
        limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=50),
        new_limit: int = Query(default=DEFAULT_NEW_PER_DAY, ge=0, le=50),
        max_level: Literal["A1", "A2", "B1", "B2", "C1"] | None = None,
        level: Literal["A1", "A2", "B1", "B2", "C1"] | None = None,
        topic: str | None = Query(default=None, max_length=40, pattern=SLUG_PATTERN),
    ) -> VocabSession:
        result = practice.session(
            learner_id,
            list_slug,
            limit=limit,
            new_limit=new_limit,
            max_level=max_level,
            level=level,
            topic=topic,
        )
        return VocabSession(
            entries=[
                VocabEntry(item=e.item, is_new=e.is_new, card=e.card, due_at=e.due_at)
                for e in result.entries
            ],
            due=result.due,
            new_today=result.new_today,
            new_left_today=result.new_left_today,
            new_available=result.new_available,
        )

    @router.get("/search")
    def find(
        q: str = Query(min_length=1, max_length=MAX_QUERY),
        list_slug: str = Query(
            default="core-seed", alias="list", min_length=1, max_length=40, pattern=SLUG_PATTERN
        ),
        limit: int = Query(default=20, ge=1, le=50),
    ) -> VocabSearch:
        wordlist = practice.wordlist(list_slug)
        found = search(wordlist.words, q, limit)
        return VocabSearch(
            status=wordlist.status, total=found.total, results=[card(w) for w in found.words]
        )

    @router.get("/levels")
    def levels(
        learner_id: str = Query(min_length=1, max_length=200),
        list_slug: str = Query(
            default="core-seed", alias="list", min_length=1, max_length=40, pattern=SLUG_PATTERN
        ),
        topic: str | None = Query(default=None, max_length=40, pattern=SLUG_PATTERN),
    ) -> VocabLevels:
        result = practice.levels(learner_id, list_slug, topic=topic)
        return VocabLevels(
            levels=[
                VocabLevel(level=c.level, words=c.words, started=c.started, due=c.due)
                for c in result.levels
            ],
            suggested=result.suggested,
            topics=[
                VocabTopic(slug=t.slug, name_vi=t.name_vi, words=t.words, started=t.started)
                for t in result.topics
            ],
        )

    @router.post("/checks")
    def check(body: VocabCheckInput) -> VocabCheckResult:
        correct, accepted, card = practice.check(body.item_id, body.answer)
        return VocabCheckResult(correct=correct, accepted=accepted, card=card)

    @router.post("/answers")
    def answer(body: VocabAnswerInput) -> VocabAnswerResult:
        result = practice.answer(body.learner_id, body.item_id, body.answer)
        trace = DecisionTrace.model_validate(result.trace.model_dump())
        return VocabAnswerResult(
            correct=result.correct,
            accepted=result.accepted,
            card=result.card,
            due_at=result.due_at,
            trace=trace,
        )

    return router
