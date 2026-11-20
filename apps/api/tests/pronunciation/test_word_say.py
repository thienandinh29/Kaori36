# ruff: noqa: RUF001, RUF003
"""Step 3.7: saying a vocabulary word, analysed in memory and never stored."""

import asyncio
from pathlib import Path
from typing import Any

import pytest
from fastapi import HTTPException

from app.pronunciation.word import MODEL_FORM, low, model_phones, per_phone, phones_from_ipa
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


# The model's own symbols for five British vowels (step 3.7c), also in the pinned vocab.json.
RECOGNISER_FORMS = {"ɔ", "oː", "oʊ", "aː", "ɛː"}


def test_every_word_in_the_list_uses_only_phones_the_recogniser_knows() -> None:
    words = shared_wordlist(VOCAB, IMPORTED).words
    used = {p for w in words if w.ipa for p in phones_from_ipa(w.ipa)}
    assert used <= RECOGNISER, used - RECOGNISER
    sent = {p for w in words if w.ipa for p in model_phones(phones_from_ipa(w.ipa))}
    assert sent <= (RECOGNISER - set(MODEL_FORM)) | RECOGNISER_FORMS


def row(gop: float, heard: str | None, peak: float = 0.8) -> dict[str, Any]:
    return {"phone": "?", "gop": gop, "competitor": heard, "peak": peak, "other_peak": peak / 2}


def test_british_vowels_are_scored_in_the_models_symbols_and_shown_in_the_dictionarys() -> None:
    assert model_phones(["p", "ɒ", "t", "ɔː", "əʊ", "ɑː", "eə"]) == [
        "p", "ɔ", "t", "oː", "oʊ", "aː", "ɛː",
    ]  # fmt: skip
    # /ɔː/ heard as the model's ɔ is shown as /ɒ/, the confusion a learner knows
    out = per_phone(
        ["p", "ɔː", "t"], {"phones": [row(-0.1, None), row(-2.5, "ɔ"), row(-0.1, None)]}
    )
    assert [(p["phone"], p["heard"]) for p in out] == [("p", None), ("ɔː", "ɒ"), ("t", None)]


def test_native_variants_are_close_and_a_weak_schwa_may_vanish() -> None:
    out = per_phone(
        ["ə", "ɑː", "ə", "ɪ"],
        {"phones": [row(-2.5, "ɐ"), row(-2.0, "a"), row(-9.0, None, peak=0.01), row(-3.0, "iː")]},
    )
    assert [(p["closeness"], p["heard"], p["dropped"]) for p in out] == [
        (85, None, False), (85, None, False), (85, None, False), (37, "iː", False),
    ]  # fmt: skip  # /ɪ/ heard as /iː/ is a real confusion, never excused


def test_what_the_recogniser_cannot_tell_is_unsure_not_low() -> None:
    out = per_phone(["b", "d", "uː", "d"], {"phones": [
        row(-4.0, "p"), row(-4.0, "t"), row(-4.0, "iː"), row(-9.0, "t", peak=0.01),
    ]})  # fmt: skip
    assert [(p["closeness"], p["heard"], low(p)) for p in out[:3]] == [(70, None, False)] * 3
    assert out[3]["dropped"] and low(out[3])  # a dropped /d/ is still shown


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


def test_silence_around_the_word_is_cut_and_a_quick_word_is_padded() -> None:
    sent: list[int] = []

    def score(audio: bytes, phones: list[str]) -> dict[str, Any]:
        sent.append(len(audio))
        return {"recognised": [], "phones": [row(-0.1, None) for _ in phones]}

    s = service(score)
    # Two seconds of a quiet room before the word and one after made it "too quiet" (step 3.7c)
    waited = wav(hiss(2.0, 30) + tone(0.4, 3000) + hiss(1.0, 30, 2))
    assert asyncio.run(s.say(OWNER, "choose:verb", "voice-v1", waited))["ok"]
    assert sent[-1] < len(waited) / 2  # sent without most of the silence
    # A word said straight after the tap, 0.35 s in 0.45 s, was "too short"
    quick = wav(hiss(0.05, 30) + tone(0.35, 3000) + hiss(0.05, 30, 2))
    assert asyncio.run(s.say(OWNER, "choose:verb", "voice-v1", quick))["ok"]
    assert sent[-1] >= 44 + 2 * 16_000  # padded to a second for the aligner
    blip = wav(hiss(0.05, 30) + tone(0.1, 3000))
    assert asyncio.run(s.say(OWNER, "choose:verb", "voice-v1", blip))["problems"] == ["too_short"]


# --- Step 3.7b: guidance from repeated attempts, and sounds to focus on ---
import yaml  # type: ignore[import-untyped]  # noqa: E402

from app.pronunciation.word import closeness, focus, repeated  # noqa: E402

TIPS = DATA / "data" / "pronunciation" / "phone-tips.yaml"


def attempt(*phones: tuple[str, float, str | None, bool]) -> list[dict[str, Any]]:
    return [{"phone": p, "gop": g, "heard": h, "dropped": d} for p, g, h, d in phones]


GOOD = attempt(("p", -0.1, None, False), ("ɔː", -0.2, None, False), ("t", -0.1, None, False))
ORAL = attempt(("p", -0.1, None, False), ("ɔː", -1.5, "ɑː", False), ("t", -0.1, None, False))
DROP = attempt(("p", -0.1, None, False), ("ɔː", -0.2, None, False), ("t", -9.0, None, True))


def test_closeness_matches_the_web_and_low_is_under_70() -> None:
    assert (closeness(0), closeness(-3), closeness(-30)) == (100, 37, 0)
    assert closeness(-1.5) < 70 < closeness(-0.2)


def test_a_sound_low_twice_in_the_last_three_attempts_gets_a_guide() -> None:
    assert repeated([ORAL]) == []  # once is not a pattern
    assert repeated([GOOD, ORAL, ORAL])[0]["times"] == 2  # newest fine, still a pattern
    g = repeated([ORAL, GOOD, ORAL])
    assert [(x["phone"], x["heard"], x["times"], x["of"]) for x in g] == [("ɔː", "ɑː", 2, 3)]
    assert repeated([ORAL, GOOD, GOOD, ORAL]) == []  # only the last three count
    d = repeated([DROP, DROP])
    assert d[0]["phone"] == "t" and d[0]["dropped"] is True and d[0]["heard"] is None
    other_word = attempt(("k", -5.0, "g", False))
    assert repeated([ORAL, other_word, ORAL])[0]["of"] == 2  # a different sound sequence is skipped


def test_focus_ranks_sounds_by_how_often_they_are_low() -> None:
    rows = focus([ORAL, ORAL, ORAL, GOOD, DROP])
    assert [(r["phone"], r["low"], r["seen"], r["heard"]) for r in rows] == [
        ("ɔː", 3, 5, "ɑː"),
        ("t", 1, 5, None),
    ]
    assert focus([ORAL, ORAL]) == []  # seen fewer than 3 times: not enough to say


def test_every_sound_has_a_tip_and_every_pair_names_known_sounds() -> None:
    tips = yaml.safe_load(TIPS.read_text(encoding="utf-8"))
    assert set(tips["phones"]) == RECOGNISER
    assert all(t["how"] and t["example"] for t in tips["phones"].values())
    for key, pair in tips["pairs"].items():
        expected, heard = key.split(">")
        assert {expected, heard} <= RECOGNISER, key
        assert pair["tip"] and len(pair["minimal"]) == 2
    assert tips["dropped"]


def test_attempts_are_kept_without_audio_and_guide_the_next_try(database_url: str) -> None:
    from psycopg_pool import ConnectionPool

    pool = ConnectionPool(database_url, open=True)
    with pool.connection() as conn:
        row = conn.execute("insert into learners(display_name) values ('S') returning id::text")
        learner = row.fetchone()
        assert learner is not None
    seq = iter([-1.5, -0.2, -1.6])  # ɔː low, fine, low again

    def score(audio: bytes, phones: list[str]) -> dict[str, Any]:
        g = next(seq)
        return {"recognised": [], "phones": [
            {"phone": p, "gop": g if p == "oː" else -0.1,  # /ɔː/ in the model's symbol
             "competitor": "aː" if p == "oː" and g < -1 else None,
             "peak": 0.8, "other_peak": 0.1}
            for p in phones
        ]}  # fmt: skip

    s = WordSay(VOCAB, IMPORTED, learner[0], score, lambda: pool, TIPS)
    outs = [
        asyncio.run(s.say(learner[0], "important:adjective", "voice-v1", speech()))
        for _ in range(3)
    ]
    assert outs[0]["guide"] == [] and outs[1]["guide"] == []
    guide = outs[2]["guide"][0]
    assert (guide["phone"], guide["heard"], guide["times"]) == ("ɔː", "ɑː", 2)
    assert "tròn" in guide["change"] and guide["minimal"] == ["caught", "cart"] and guide["how"]
    assert all(p["how"] for p in outs[2]["phones"])
    with pool.connection() as conn:
        cols = [
            r[0]
            for r in conn.execute(
                "select column_name from information_schema.columns where table_name='say_attempts'"
            ).fetchall()
        ]
        n = conn.execute("select count(*) from say_attempts where learner_id=%s", (learner[0],))
        assert n.fetchone() == (3,)
    assert not any("audio" in c for c in cols)  # never the recording
    f = s.focus(learner[0])
    assert f["attempts"] == 3 and f["sounds"][0]["phone"] == "ɔː" and f["sounds"][0]["how"]
    with pool.connection() as conn:
        conn.execute("delete from say_attempts")
    pool.close()


def test_analysing_the_same_recording_again_is_one_attempt(database_url: str) -> None:
    """20 Nov 2026: "Phân tích lại" on the same take, or a retry after a lost reply, added an
    attempt, so one recording counted twice ("2/2 lần gần đây")."""
    from uuid import uuid4

    from psycopg_pool import ConnectionPool

    pool = ConnectionPool(database_url, open=True)
    with pool.connection() as conn:
        row = conn.execute("insert into learners(display_name) values ('T') returning id::text")
        learner = row.fetchone()
        assert learner is not None

    def score(audio: bytes, phones: list[str]) -> dict[str, Any]:
        return {
            "recognised": [],
            "phones": [
                {
                    "phone": p,
                    "gop": -1.5 if p == "oː" else -0.1,
                    "competitor": "aː" if p == "oː" else None,
                    "peak": 0.8,
                    "other_peak": 0.1,
                }
                for p in phones
            ],
        }  # fmt: skip  (/ɔː/ low every time)

    s = WordSay(VOCAB, IMPORTED, learner[0], score, lambda: pool, TIPS)
    take = uuid4()
    first = asyncio.run(s.say(learner[0], "important:adjective", "voice-v1", speech(), take))
    again = asyncio.run(s.say(learner[0], "important:adjective", "voice-v1", speech(), take))
    assert first["guide"] == [] and again["guide"] == []  # still one attempt, not "2 of 2"
    with pool.connection() as conn:
        n = conn.execute("select count(*) from say_attempts where learner_id=%s", (learner[0],))
        assert n.fetchone() == (1,)
    new = asyncio.run(s.say(learner[0], "important:adjective", "voice-v1", speech(), uuid4()))
    assert new["guide"] and new["guide"][0]["times"] == 2  # a new recording is a new attempt
    with pool.connection() as conn:
        conn.execute("delete from say_attempts where learner_id=%s", (learner[0],))
    pool.close()
