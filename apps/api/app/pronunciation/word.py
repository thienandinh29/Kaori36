# ruff: noqa: RUF001, RUF002, RUF003
"""Saying one vocabulary word (specs/pronunciation/step-3.7.md): its dictionary IPA as the
recogniser's phones, and the service's per-phone output as the learner sees it.

Pure. Nothing here marks a sound right or wrong: thresholds wait for the pronunciation gate, so the
learner sees raw scores, "bỏ mất âm" when a phone was not said at all, and what was heard instead.
"""

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from app.pronunciation.evidence import is_dropped

# Longest first: two-character phones of British dictionary IPA, written as the recogniser's.
_MULTI = {
    "tʃ": "tʃ", "dʒ": "dʒ", "iː": "iː", "uː": "uː", "ɑː": "ɑː", "ɔː": "ɔː", "ɜː": "ɜː",
    "eɪ": "eɪ", "aɪ": "aɪ", "ɔɪ": "ɔɪ", "aʊ": "aʊ", "əʊ": "əʊ", "ɪə": "iə", "eə": "eə",
    "ʊə": "ʊə",
}  # fmt: skip
_SINGLE = {"e": "ɛ", "r": "ɹ", "g": "ɡ"}  # dictionary letters the recogniser writes otherwise
_IGNORED = set("/ˈˌ.()‿ ")


def phones_from_ipa(ipa: str) -> list[str]:
    """`/ɪmˈpɔːtənt/` -> ["ɪ", "m", "p", "ɔː", "t", "ə", "n", "t"]; stress and slashes dropped."""
    text = "".join(c for c in ipa.strip() if c not in _IGNORED)
    out: list[str] = []
    i = 0
    while i < len(text):
        pair = text[i : i + 2]
        if pair in _MULTI:
            out.append(_MULTI[pair])
            i += 2
            continue
        if text[i] == "ː" and out:  # a length mark after a phone the table does not pair
            out[-1] += "ː"
        else:
            out.append(_SINGLE.get(text[i], text[i]))
        i += 1
    return out


# The recogniser writes some British vowels with its own symbols (the keys below are the
# dictionary's, the values the model's): on the native British voice almost every one of them was
# heard as the model's symbol (measured 19 Nov, 80 words x 3 recordings; step-3.7c.md). A sound is
# scored against the model's symbol and shown in the dictionary's.
MODEL_FORM = {"ɒ": "ɔ", "ɔː": "oː", "əʊ": "oʊ", "ɑː": "aː", "eə": "ɛː"}
DICTIONARY_FORM = {v: k for k, v in MODEL_FORM.items()}
# What the model hears on correct native speech for a sound, which is no error: weak and unstressed
# variants only. The confusions that matter (long/short vowel pairs, TH/T...) are never listed here.
ACCEPTED = {
    "ə": {"ɐ", "ɪ", "ɨ"},
    "ɪ": {"ɨ", "i", "ə"},
    "i": {"ɪ", "iː"},
    "ɑː": {"a", "ɑ"},
    "eə": {"ɛ", "eː"},
    "ɒ": {"ɑ"},
    "u": {"ʊ", "uː"},
}
# Where the recogniser cannot tell on native speech: English voiced stops are often voiceless
# unaspirated, which this model (trained mostly on other languages) hears as p, t, k (b 13/30,
# d 25/51, g 15/27 low on the native voice, mostly inside words), and the Southern British /uː/ is
# fronted, heard as iː (10/21). Such a reading is shown as unsure (amber, never counted low or
# used for guidance) and nothing is claimed about what was heard. A real error of this kind is
# hidden too; that is the price of no false alarms until Gold labels measure it.
UNSURE = {"b": {"p"}, "d": {"t"}, "ɡ": {"k"}, "uː": {"iː", "ʉː"}}
DROPPABLE = {"ə"}  # an unstressed schwa may vanish in natural speech: never shown as dropped
ACCEPTED_CLOSENESS = 85


def model_phones(phones: Sequence[str]) -> list[str]:
    """The expected phones in the recogniser's own symbols (what is sent for alignment)."""
    return [MODEL_FORM.get(p, p) for p in phones]


def per_phone(phones: Sequence[str], scored: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Each expected phone (dictionary form) with its score, what competed with it (shown in the
    dictionary's symbols), and whether it was dropped; native variants count as close."""
    got = scored["phones"]
    if len(got) != len(phones):
        raise ValueError("the service returned a different number of phones")
    out: list[dict[str, Any]] = []
    for p, g in zip(phones, got, strict=True):
        near = closeness(float(g["gop"]))
        heard = g["competitor"]
        dropped = is_dropped(g) and p not in DROPPABLE
        if heard in ACCEPTED.get(p, ()) or (p in DROPPABLE and is_dropped(g)):
            near, heard = max(near, ACCEPTED_CLOSENESS), None
        elif heard in UNSURE.get(p, ()) and not dropped:
            near, heard = max(near, LOW), None
        out.append(
            {
                "phone": p,
                "gop": g["gop"],
                "closeness": near,
                "heard": DICTIONARY_FORM.get(heard, heard) if heard else None,
                "dropped": dropped,
            }
        )
    return out


# --- Guidance from repeated attempts (specs/pronunciation/step-3.7b.md) ---
LOW = 70  # closeness under this counts as "not yet" for guidance (a practice hint, not a mark)
WINDOW, REPEATS = 3, 2  # the same sound low in 2 of the last 3 attempts at a word


def closeness(gop: float) -> int:
    """A rough 0-100 reading of a phone's GOP (0 is the best); the web shows the same number."""
    return max(0, min(100, round(100 * math.exp(gop / 3))))


def low(p: Mapping[str, Any]) -> bool:
    near = p.get("closeness")
    return bool(p["dropped"]) or (closeness(float(p["gop"])) if near is None else int(near)) < LOW


def repeated(attempts: Sequence[Sequence[Mapping[str, Any]]]) -> list[dict[str, Any]]:
    """Sounds of one word low in REPEATS of its last WINDOW attempts (newest first), with what
    was most often heard instead. Attempts with a different phone sequence are not compared."""
    if not attempts:
        return []
    recent = [
        a for a in attempts[:WINDOW] if [p["phone"] for p in a] == [p["phone"] for p in attempts[0]]
    ]
    out: list[dict[str, Any]] = []
    for i, p in enumerate(attempts[0]):
        lows = [a[i] for a in recent if low(a[i])]
        if len(lows) < REPEATS:
            continue
        heard = Counter(x["heard"] for x in lows if x["heard"] and not x["dropped"])
        out.append(
            {
                "index": i,
                "phone": p["phone"],
                "times": len(lows),
                "of": len(recent),
                "heard": heard.most_common(1)[0][0] if heard else None,
                "dropped": sum(1 for x in lows if x["dropped"]) * 2 > len(lows),
            }
        )
    return out


def focus(
    attempts: Sequence[Sequence[Mapping[str, Any]]], min_seen: int = 3, top: int = 5
) -> list[dict[str, Any]]:
    """Across all words: the sounds most often low, seen at least `min_seen` times."""
    seen: Counter[str] = Counter()
    lows: Counter[str] = Counter()
    heard: dict[str, Counter[str]] = {}
    for a in attempts:
        for p in a:
            seen[p["phone"]] += 1
            if low(p):
                lows[p["phone"]] += 1
                if p["heard"] and not p["dropped"]:
                    heard.setdefault(p["phone"], Counter())[p["heard"]] += 1
    rows = [
        {
            "phone": ph,
            "low": lows[ph],
            "seen": n,
            "share": round(lows[ph] / n, 2),
            "heard": heard[ph].most_common(1)[0][0] if ph in heard else None,
        }
        for ph, n in seen.items()
        if n >= min_seen and lows[ph] > 0
    ]
    rows.sort(key=lambda r: (-float(r["share"] or 0), -int(r["low"] or 0), str(r["phone"])))
    return rows[:top]
