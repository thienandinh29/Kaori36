"""Lessons (specs/grammar-lessons, phase B1): the format, every check, the store and the routes."""

import unicodedata
from pathlib import Path
from typing import Any

import pytest
import yaml  # type: ignore[import-untyped]
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api import lessons as lesson_routes
from app.curriculum.course import load_course
from app.curriculum.items import load_items
from app.lessons.checks import check_lesson, seconds
from app.lessons.graded import build_index, off_level, too_long
from app.lessons.model import Lesson
from app.lessons.store import LessonStore, Paths, word_index
from app.services.grammar import load_misconceptions

ROOT = Path(__file__).resolve().parents[4]
PATHS = Paths(
    lessons=ROOT / "data" / "lessons",
    courses=ROOT / "data" / "courses",
    items=ROOT / "data" / "items",
    forms=ROOT / "data-sa" / "vocabulary" / "forms.yaml",
    vocabulary=ROOT / "data" / "vocabulary" / "core-seed.yaml",
    candidates=ROOT / "data" / "sources" / "english-candidates.yaml",
)
COURSE = load_course(PATHS.courses / "english-ielts.yaml")
BANK = load_items(PATHS.items / "english-ielts.yaml", COURSE)
MISCONCEPTIONS = load_misconceptions(PATHS.items / "misconceptions.vi.yaml")
WORDS = word_index(PATHS)
OWNER = "00000000-0000-4000-8000-0000000000aa"
OTHER = "00000000-0000-4000-8000-0000000000bb"


def lesson(**over: Any) -> dict[str, Any]:
    """A small valid lesson (about 100 s) to break one rule at a time."""
    say = [
        {
            "do": "say",
            "en": "We use this form for things that are still true now.",
            "vi": "Dùng dạng này cho điều vẫn còn đúng.",
        }
    ] * 9
    base: dict[str, Any] = {
        "course": "english-ielts",
        "node": "present-perfect-vs-past",
        "level": "B1",
        "status": "sample",
        "title_en": "T",
        "title_vi": "T",
        "names": ["Mai"],
        "scenes": [
            {
                "id": "a",
                "kind": "engage",
                "actions": [
                    *say,
                    {
                        "do": "show_example",
                        "id": "e1",
                        "en": "Mai has studied here for a year.",
                        "vi": "Mai học ở đây được một năm.",
                        "target": "has studied",
                    },
                    {"do": "spotlight", "example": "e1"},
                ],
            },
            {"id": "b", "kind": "activate", "actions": [{"do": "ask", "checkpoint": "c1"}, *say]},
        ],
        "checkpoints": [
            {
                "id": "c1",
                "en": "Is it still true now?",
                "vi": "Bây giờ còn đúng không?",
                "options": [
                    {"text": "Yes", "correct": True},
                    {"text": "No", "misconception": "past-simple-with-since"},
                ],
                "explain_vi": "Có.",
            }
        ],
    }
    base.update(over)
    return base


def problems(data: dict[str, Any], verified: tuple[str, ...] = ()) -> list[str]:
    return check_lesson(Lesson.model_validate(data), COURSE, BANK, MISCONCEPTIONS, WORDS, verified)


# --- graded narration -------------------------------------------------------------------------


def test_inflected_forms_reach_their_headword_and_levels_are_respected() -> None:
    assert off_level("She went home and the children studied.", "A1", WORDS) == []
    assert off_level("I don't know, it's here, you're right, we can't stay.", "A1", WORDS) == []
    assert "phenomenon" in off_level("This phenomenon is common.", "A2", WORDS)
    assert off_level("Sena likes IELTS and Hanoi.", "A1", WORDS) == []  # names always allowed
    assert off_level("The examiner asks.", "B1", WORDS, ["examiner"]) == []  # the lesson's terms
    assert off_level("Two tenses.", "A1", WORDS, ["tense"]) == []  # a term's plural


def test_word_levels_use_the_lowest_level_of_a_form(tmp_path: Path) -> None:
    forms = tmp_path / "forms.yaml"
    forms.write_text("leave: [A1, leaves, left]\nleft: [B1]\n", encoding="utf-8")
    index = build_index(forms, [("glimmer", "C1")])
    assert off_level("He left early.", "A1", index) == ["he", "early"]  # left is A1 through leave
    assert off_level("A glimmer.", "B2", index) == ["a", "glimmer"]


def test_sentence_length_depends_on_the_level() -> None:
    sixteen = " ".join(["word"] * 16) + "."
    assert too_long(sixteen, "A2") and not too_long(sixteen, "B1")
    assert too_long("Short one. " + sixteen, "A1") == [sixteen]


# --- the format -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("change", "why"),
    [
        ({"scenes": [{"id": "a", "kind": "engage", "actions": [{"do": "dance"}]}] * 2}, "dance"),
        (
            {
                "scenes": [
                    {"id": "a", "kind": "form", "actions": [{"do": "board_table", "rows": [["x"]]}]}
                ]
                * 2
            },
            "2 to 4 cells",
        ),
        (
            {
                "scenes": [
                    {
                        "id": "a",
                        "kind": "form",
                        "actions": [
                            {
                                "do": "board_timeline",
                                "spans": [{"label": "x", "start": 0, "end": -1}],
                            }
                        ],
                    }
                ]
                * 2
            },
            "end after",
        ),
        (
            {
                "checkpoints": [
                    {
                        "id": "c1",
                        "en": "q",
                        "vi": "q",
                        "explain_vi": "x",
                        "options": [{"text": "a", "correct": True}, {"text": "b", "correct": True}],
                    }
                ]
            },
            "exactly one",
        ),
        ({"scenes": [{"id": "a", "kind": "engage", "actions": [{"do": "pause"}]}] * 2}, "unique"),
        ({"level": "D1"}, "level"),
    ],
)
def test_the_format_refuses_what_the_player_cannot_play(change: dict[str, Any], why: str) -> None:
    with pytest.raises(ValidationError, match=why):
        Lesson.model_validate(lesson(**change))


# --- the checks -------------------------------------------------------------------------------


def test_a_good_sample_passes_and_lasts_long_enough() -> None:
    assert problems(lesson()) == []
    assert 90 <= seconds(Lesson.model_validate(lesson())) <= 240


def test_each_rule_reports_its_problem() -> None:
    data = lesson()
    data["scenes"][0]["actions"][-1] = {"do": "spotlight", "example": "missing"}
    assert any("not shown before" in p for p in problems(data))
    data = lesson()
    data["scenes"][0]["actions"][-2]["target"] = "have studied"
    assert any("target" in p for p in problems(data))
    data = lesson(level="A2")
    assert any("level A2 is not" in p for p in problems(data))
    data = lesson()
    data["scenes"][1]["misconceptions"] = ["no-such-mistake"]
    assert any("unknown misconception no-such-mistake" in p for p in problems(data))
    data = lesson()
    data["scenes"][1]["actions"] = data["scenes"][1]["actions"][1:]
    assert any("never asked" in p for p in problems(data))
    data = lesson(title_vi=unicodedata.normalize("NFD", "Hiện tại"))
    assert any("NFC" in p for p in problems(data))
    data = lesson()
    data["scenes"][0]["actions"][0] = {
        "do": "say",
        "en": "This phenomenon is ubiquitous.",
        "vi": "x",
    }
    assert any("ubiquitous" in p for p in problems(data))
    data = lesson()
    data["scenes"] = [{**s, "actions": s["actions"][-3:]} for s in data["scenes"]]
    assert any("outside 90-240" in p for p in problems(data))


def test_the_lesson_never_repeats_a_test_question() -> None:
    data = lesson()
    item = next(i for i in BANK.items if i.node == "present-perfect-vs-past")
    data["scenes"][0]["actions"][-2] = {
        "do": "show_example",
        "id": "e1",
        "target": item.key,
        "en": item.prompt.replace("___", item.key),
        "vi": "x",
    }
    assert any(f"repeats test item {item.id}" in p for p in problems(data))


def test_real_lessons_need_verified_sources_and_cited_study_scenes() -> None:
    data = lesson(status="draft")
    data["scenes"][0]["kind"] = "notice"
    found = problems(data)
    assert "a lesson needs its sources" in found and any("cites no chunk" in p for p in found)
    data["sources"] = [
        {"candidate": "esl-grammar-bissonnette", "chapter": "3.07", "licence": "CC BY-NC 4.0"}
    ]
    data["scenes"][0]["cites"] = ["chunk:bissonnette-3-07-001"]
    assert problems(data) == ["source esl-grammar-bissonnette is not verified"]
    assert problems(data, verified=("esl-grammar-bissonnette",)) == []
    assert Lesson.model_validate(data).noncommercial  # NC source -> NC lesson


# --- the store and the committed files --------------------------------------------------------


def test_every_committed_lesson_loads_and_passes() -> None:
    store = LessonStore(PATHS, "english-ielts")
    assert "present-perfect-vs-past" in store.lessons
    sample = store.lessons["present-perfect-vs-past"]
    assert sample.status == "sample"  # labelled, never shown as a real lesson
    assert store.visible("present-perfect-vs-past", include_drafts=False) is None


def test_a_file_must_be_named_after_its_node(tmp_path: Path) -> None:
    folder = tmp_path / "lessons" / "english-ielts"
    folder.mkdir(parents=True)
    (folder / "wrong-name.yaml").write_text(yaml.safe_dump(lesson()), encoding="utf-8")
    paths = Paths(**{**PATHS.__dict__, "lessons": tmp_path / "lessons"})
    with pytest.raises(ValueError, match="file name must be the node"):
        LessonStore(paths, "english-ielts")


def test_forms_file_maps_irregular_forms() -> None:
    raw = yaml.safe_load(PATHS.forms.read_text(encoding="utf-8"))
    assert raw["go"][0] == "A1" and "went" in raw["go"] and "children" in raw["child"]
    assert "the" in raw and "monday" in raw  # function words and the supplementary list


# --- routes -----------------------------------------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    store = LessonStore(PATHS, "english-ielts")
    app.include_router(lesson_routes.create_router({"english-ielts": store}, OWNER, MISCONCEPTIONS))
    return TestClient(app)


def test_samples_reach_the_owner_only_and_keys_never_leave(client: TestClient) -> None:
    assert client.get("/lessons", params={"learner_id": OTHER}).json() == []
    assert (
        client.get("/lessons/present-perfect-vs-past", params={"learner_id": OTHER}).status_code
        == 404
    )
    listed = client.get("/lessons", params={"learner_id": OWNER}).json()
    assert [x["node"] for x in listed] == ["present-perfect-vs-past"]
    r = client.get("/lessons/present-perfect-vs-past", params={"learner_id": OWNER})
    body = r.json()
    assert r.status_code == 200 and body["status"] == "sample"
    assert (
        "correct" not in r.text and 'misconception"' not in r.text
    )  # no key, no wrong-option tags
    assert body["checkpoints"][0]["options"] == ["Yes", "No"]


def test_a_checkpoint_is_graded_by_key_and_is_not_evidence(client: TestClient) -> None:
    url = "/lessons/present-perfect-vs-past/checkpoints"
    right = client.post(
        url, json={"learner_id": OWNER, "checkpoint": "still-true", "answer": "Yes"}
    )
    assert right.json()["correct"] is True and right.json()["evidence"] is False
    wrong = client.post(
        url, json={"learner_id": OWNER, "checkpoint": "time-word", "answer": "two months ago"}
    ).json()
    assert wrong["correct"] is False and wrong["key"] == "since January"
    assert wrong["misconception_vi"] == MISCONCEPTIONS["present-perfect-with-ago"]
    assert (
        client.post(
            url, json={"learner_id": OWNER, "checkpoint": "time-word", "answer": "never"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            url, json={"learner_id": OTHER, "checkpoint": "still-true", "answer": "Yes"}
        ).status_code
        == 404
    )
