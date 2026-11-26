# ruff: noqa: RUF001
"""Wiktionary coverage (specs/vocabulary-import/step-wiktionary.md): what is counted, and how."""

import gzip
import json
from pathlib import Path
from typing import Any

from app.vocabulary.wiktionary import (
    accent,
    audio,
    coverage,
    english_entries,
    ipa_agrees,
    ipas,
    read_cache,
    scan,
    summary,
    usage_examples,
    vietnamese,
)
from app.vocabulary.wordlist import Word


def word(lemma: str, pos: str = "noun", ipa: str | None = None, origin: str = "ngsl") -> Word:
    return Word.model_validate(
        {
            "lemma": lemma,
            "pos": pos,
            "level": "B1",
            "origin": origin,
            "ipa": ipa,
            "definition": "something used in a test",
            "examples": [{"text": f"This sentence uses {lemma} once.", "answer": lemma}],
        }
    )


HABIT: dict[str, Any] = {
    "word": "habit",
    "lang_code": "en",
    "pos": "noun",
    "sounds": [
        {"ipa": "/ˈhæb.ɪt/", "tags": ["Received-Pronunciation"]},
        {"ipa": "/ˈhæb.ɪt/", "tags": ["General-American"]},
        {"audio": "En-uk-habit.ogg", "ogg_url": "https://upload.wikimedia.org/En-uk-habit.ogg"},
    ],
    "translations": [{"code": "vi", "word": "thói quen"}, {"code": "fr", "word": "habitude"}],
    "senses": [
        {
            "glosses": ["An action done on a regular basis."],
            "examples": [
                {"text": "Smoking is a bad habit.", "type": "example"},
                {"text": "An old line from a book.", "type": "quotation"},
            ],
        }
    ],
}


def test_accents_are_classified_with_british_first() -> None:
    assert accent(["Received-Pronunciation"]) == "uk"
    assert accent(["UK", "US"]) == "uk"
    assert accent(["General-American"]) == "other"
    assert accent([]) == "untagged"


def test_what_one_entry_offers() -> None:
    assert ipas(HABIT, "uk") == ["/ˈhæb.ɪt/"]
    assert audio(HABIT, "uk") == ["https://upload.wikimedia.org/En-uk-habit.ogg"]
    assert vietnamese(HABIT) == ["thói quen"]
    assert usage_examples(HABIT) == ["Smoking is a bad habit."]


def test_vietnamese_inside_senses_is_found_once() -> None:
    entry = {"senses": [{"translations": [{"code": "vi", "word": "tai nạn"}]}], "translations": []}
    assert vietnamese(entry) == ["tai nạn"]


def test_optional_rhotic_sounds_are_left_out_before_comparing() -> None:
    assert ipa_agrees("/ˈwɔːtə/", "/ˈwɔː.tə(ɹ)/")
    assert not ipa_agrees("/ɪkˈspɔːt/", "/ˈɪk.spɔːt/")  # another stressed syllable


def test_wiktionary_notation_is_folded_but_substance_is_not() -> None:
    assert ipa_agrees("/tʃɜːtʃ/", "/t͡ʃɜːt͡ʃ/")  # tie bars
    assert ipa_agrees("/ˌbaɪəʊdaɪˈvɜːsəti/", "/ˌbaɪə(ʊ)daɪˈvɜːsəti/")  # the optional sound said
    assert ipa_agrees("/hɪə/", "/hɪə̯/")  # non-syllabic mark
    assert not ipa_agrees("/fɪʃ/", "[fɪʃ]")  # a narrow transcription is not compared
    assert not ipa_agrees("/ˈbrekfəst/", "/ˈbreɪkˌfɑːst/")  # another pronunciation


def test_only_top_level_english_entries_of_listed_words_are_kept() -> None:
    lines = [
        json.dumps(HABIT),
        json.dumps({**HABIT, "lang_code": "fr"}),  # a French homograph
        json.dumps({"word": "zebra", "lang_code": "en", "pos": "noun"}),  # not on the list
        json.dumps({"word": "habit", "lang_code": "de", "descendants": [{"lang_code": "en"}]}),
    ]
    kept = list(english_entries(lines, {"habit"}))
    assert [e["lang_code"] for e in kept] == ["en"]


def test_scan_writes_the_matches_and_reads_them_back(tmp_path: Path) -> None:
    dump = tmp_path / "dump.jsonl.gz"
    with gzip.open(dump, "wt", encoding="utf-8") as f:
        f.write(json.dumps(HABIT) + "\n" + json.dumps({**HABIT, "word": "other"}) + "\n")
    cache = tmp_path / "out" / "en.jsonl"
    assert scan(dump, cache, {"habit"}) == 1
    assert read_cache(cache) == [HABIT]


def test_coverage_counts_against_the_list() -> None:
    verb_habit = {
        "word": "habit",
        "lang_code": "en",
        "pos": "verb",
        "sounds": [{"ipa": "/x/", "tags": ["UK"]}],
    }
    words = [
        word("habit", ipa="/ˈhæbɪt/"),  # agrees
        word("accident"),  # no entry at all
    ]
    c = coverage(words, [HABIT, verb_habit])
    assert (c.words, c.found, c.found_same_pos, c.uk_ipa, c.vi, c.uk_audio) == (2, 1, 1, 1, 1, 1)
    assert (c.ours_with_ipa_and_uk, c.ipa_agree) == (1, 1)  # the verb's /x/ is not compared
    assert c.missing == ["accident:noun"]
    assert summary(c)["British IPA"] == "1/2 (50.0%)"


def test_a_disagreement_is_sampled_and_a_word_without_ipa_counts_as_a_gain() -> None:
    c = coverage(
        [word("habit", ipa="/ˈhɑːbɪt/"), word("habits")], [HABIT, {**HABIT, "word": "habits"}]
    )
    assert c.ipa_agree == 0
    assert c.disagreements == [
        {"word": "habit:noun", "ours": "/ˈhɑːbɪt/", "wiktionary": "/ˈhæb.ɪt/"}
    ]
    assert c.ours_without_ipa_gain_uk == 1


def test_another_part_of_speech_is_used_only_when_the_lists_is_missing() -> None:
    c = coverage([word("habit", pos="verb")], [HABIT])
    assert (c.found, c.found_same_pos, c.uk_ipa) == (1, 0, 1)
