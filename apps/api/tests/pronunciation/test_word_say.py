# ruff: noqa: RUF001
"""Step 3.7: saying a vocabulary word, analysed in memory and never stored."""

import asyncio
from pathlib import Path
from typing import Any

import pytest
from fastapi import HTTPException

from app.pronunciation.word import per_phone, phones_from_ipa
from app.services.word_say import WordSay
from app.vocabulary.wordlist import shared_wordlist

from .test_recordings import hiss, tone, wav

DATA = Path(__file__).resolve().parents[4]
VOCAB = DATA / "data" / "vocabulary" / "core-seed.yaml"
IMPORTED = DATA / "data-sa" / "vocabulary"
OWNER = "00000000-0000-4000-8000-00000000a11c"
OTHER = "00000000-0000-4000-8000-000000000999"
# The recogniser's phones (vocab.json of the pinned facebook/wav2vec2-xlsr-53-espeak-cv-ft, SHA-256
# d732ab24…, checked on 19 Nov) that the word list uses: every word's phones must be among them.
_PHONES = (
    "aɪ aʊ b d dʒ eə eɪ f h i iə iː j k l m n p s t tʃ u uː v w z æ ð ŋ ɑː ɒ ɔɪ ɔː ə əʊ ɛ ɜː ɡ "
    "ɪ ɹ ʃ ʊ ʊə ʌ ʒ θ"
)
RECOGNISER = set(_PHONES.split())


@pytest.mark.parametrize(
    ("ipa", "phones"),
    [
        ("/ɪmˈpɔːtənt/", ["ɪ", "m", "p", "ɔː", "t", "ə", "n", "t"]),
        ("/tʃuːz/", ["tʃ", "uː", "z"]),
        ("/ˌedʒuˈkeɪʃən/", ["ɛ", "dʒ", "u", "k", "eɪ", "ʃ", "ə", "n"]),
        ("/ɪnˈvaɪrənmənt/", ["ɪ", "n", "v", "aɪ", "ɹ", "ə", "n", "m", "ə", "n", "t"]),
        ("/skweə/", ["s", "k", "w", "eə"]),
        ("/ɪə/", ["iə"]),
        ("/ɡəʊ/", ["ɡ", "əʊ"]),
    ],
)
def test_dictionary_ipa_becomes_the_recognisers_phones(ipa: str, phones: list[str]) -> None:
    assert phones_from_ipa(ipa) == phones


def test_every_word_in_the_list_uses_only_phones_the_recogniser_knows() -> None:
    words = shared_wordlist(VOCAB, IMPORTED).words
    used = {p for w in words if w.ipa for p in phones_from_ipa(w.ipa)}
    assert used <= RECOGNISER, used - RECOGNISER


def test_each_phone_shows_its_score_what_was_heard_and_a_dropped_sound() -> None:
    scored = {"phones": [
        {"phone": "tʃ", "gop": -0.2, "competitor": None, "peak": 0.9, "other_peak": 0.1},
        {"phone": "uː", "gop": -3.1, "competitor": "ʊ", "peak": 0.3, "other_peak": 0.6},
        {"phone": "z", "gop": -6.0, "competitor": "s", "peak": 0.02, "other_peak": 0.05},
    ]}  # fmt: skip
    out = per_phone(["tʃ", "uː", "z"], scored)
    assert [(p["phone"], p["heard"], p["dropped"]) for p in out] == [
        ("tʃ", None, False), ("uː", "ʊ", False), ("z", "s", True),
    ]  # fmt: skip
    with pytest.raises(ValueError):
        per_phone(["tʃ"], scored)


def service(score: Any) -> WordSay:
    return WordSay(VOCAB, IMPORTED, OWNER, score)


def speech() -> bytes:
    return wav(hiss(0.3, 30) + tone(0.5, 8000) + hiss(0.3, 30, 2))


def test_only_the_owner_with_consent_and_a_service_gets_an_analysis() -> None:
    calls: list[tuple[int, list[str]]] = []

    def score(audio: bytes, phones: list[str]) -> dict[str, Any]:
        calls.append((len(audio), phones))
        return {
            "recognised": ["tʃ", "uː", "s"],
            "phones": [
                {"phone": p, "gop": -1.0, "competitor": None, "peak": 0.8, "other_peak": 0.1}
                for p in phones
            ],
        }

    s = service(score)
    assert s.status(OWNER) == {"analysis": True, "owner": True, "consent": "voice-v1"}
    assert s.status(OTHER)["analysis"] is False
    out = asyncio.run(s.say(OWNER, "choose:verb", "voice-v1", speech()))
    assert out["ok"] and [p["phone"] for p in out["phones"]] == ["tʃ", "uː", "z"]
    assert out["heard"] == ["tʃ", "uː", "s"] and calls[0][1] == ["tʃ", "uː", "z"]
    for learner, consent, code in ((OTHER, "voice-v1", 403), (OWNER, "no", 422)):
        with pytest.raises(HTTPException) as e:
            asyncio.run(s.say(learner, "choose:verb", consent, speech()))
        assert e.value.status_code == code
    with pytest.raises(HTTPException) as e:
        asyncio.run(s.say(OWNER, "nothing:noun", "voice-v1", speech()))
    assert e.value.status_code == 404
    with pytest.raises(HTTPException) as e:
        asyncio.run(service(None).say(OWNER, "choose:verb", "voice-v1", speech()))
    assert e.value.status_code == 503
    assert service(None).status(OWNER)["analysis"] is False


def test_bad_audio_gets_advice_and_a_refused_alignment_is_said_plainly() -> None:
    def refuse(audio: bytes, phones: list[str]) -> dict[str, Any]:
        raise RuntimeError("cannot align")

    s = service(refuse)
    quiet = asyncio.run(s.say(OWNER, "choose:verb", "voice-v1", wav(hiss(1.0, 3))))
    assert quiet["ok"] is False and quiet["problems"] == ["too_quiet"]
    out = asyncio.run(s.say(OWNER, "choose:verb", "voice-v1", speech()))
    assert out == {"ok": False, "problems": ["not_analysed"], "phones": []}
