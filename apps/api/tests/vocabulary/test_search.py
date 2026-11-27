"""Dictionary search (specs/vocabulary/step-dictionary.md): matching rules, ranking, route."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import vocab as vocab_routes
from app.services.vocabulary import VocabPractice
from app.vocabulary.search import fold, has_diacritics, normalise, search
from app.vocabulary.wordlist import Word

LISTS = Path(__file__).resolve().parents[4] / "data" / "vocabulary"


def word(lemma: str, vi: str, level: str = "B1", pos: str = "noun") -> Word:
    return Word.model_validate(
        {
            "lemma": lemma,
            "pos": pos,
            "level": level,
            "definition": "something used in a test here",
            "vi": vi,
            "examples": [{"text": f"This is the {lemma} we need.", "answer": lemma}],
        }
    )


WORDS = [
    word("table", "cái bàn", "A1"),
    word("tablet", "máy tính bảng", "B1"),
    word("stable", "ổn định", "B2", "adjective"),
    word("sell", "bán", "A2", "verb"),
    word("friend", "bạn bè", "A1"),
    word("discuss", "thảo luận, bàn bạc", "B1", "verb"),
]


def lemmas(query: str, limit: int = 20) -> list[str]:
    return [w.lemma for w in search(WORDS, query, limit).words]


def test_exact_then_prefix_then_contains() -> None:
    assert lemmas("table") == ["table", "tablet", "stable"]
    assert lemmas("TAB") == ["table", "tablet", "stable"]  # case-insensitive


def test_contains_needs_three_letters() -> None:
    assert lemmas("ab") == []  # "ab" is inside table, but too short to search inside words
    assert lemmas("ta") == ["table", "tablet"]  # a prefix still works


def test_vietnamese_with_diacritics_is_exact_about_them() -> None:
    assert lemmas("bàn") == ["table", "discuss"]
    assert lemmas("bán") == ["sell"]
    assert lemmas("bạn") == ["friend"]


def test_vietnamese_without_diacritics_finds_every_accent_last() -> None:
    assert lemmas("ban") == ["friend", "table", "sell", "discuss"]  # not "bảng": whole syllables
    assert lemmas("on dinh") == ["stable"]


def test_ranking_puts_headwords_before_meanings_and_easier_levels_first() -> None:
    words = [*WORDS, word("bank", "ngân hàng", "B2")]
    found = search(words, "ban", 20)
    assert found.words[0].lemma == "bank"  # a headword prefix beats a meaning


def test_limit_and_total() -> None:
    found = search(WORDS, "ban", 2)
    assert len(found.words) == 2 and found.total == 4
    assert search(WORDS, "   ", 5).total == 0


def test_helpers() -> None:
    assert fold("Đường bàn") == "Duong ban"
    assert has_diacritics("bàn") and not has_diacritics("ban")
    assert normalise("  Cái   BÀN ") == "cái bàn"


def test_route_searches_the_real_list() -> None:
    app = FastAPI()
    app.include_router(vocab_routes.create_router(VocabPractice(lambda: None, LISTS)))  # type: ignore[arg-type,return-value]
    client = TestClient(app)
    out = client.get("/vocab/search", params={"q": "important"}).json()
    assert out["status"] == "draft" and out["total"] >= 1
    assert out["results"][0]["lemma"] == "important"
    assert out["results"][0]["vi"] == "quan trọng"
    assert client.get("/vocab/search", params={"q": "quan trọng"}).json()["total"] >= 1
    assert client.get("/vocab/search", params={"q": ""}).status_code == 422
    assert client.get("/vocab/search", params={"q": "x" * 41}).status_code == 422
    assert client.get("/vocab/search", params={"q": "e", "limit": 51}).status_code == 422
    assert len(client.get("/vocab/search", params={"q": "e", "limit": 3}).json()["results"]) == 3
