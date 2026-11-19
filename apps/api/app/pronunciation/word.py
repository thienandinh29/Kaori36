# ruff: noqa: RUF001, RUF002
"""Saying one vocabulary word (specs/pronunciation/step-3.7.md): its dictionary IPA as the
recogniser's phones, and the service's per-phone output as the learner sees it.

Pure. Nothing here marks a sound right or wrong: thresholds wait for the pronunciation gate, so the
learner sees raw scores, "bỏ mất âm" when a phone was not said at all, and what was heard instead.
"""

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


def per_phone(phones: Sequence[str], scored: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Each expected phone with its score, what competed with it, and whether it was dropped."""
    got = scored["phones"]
    if len(got) != len(phones):
        raise ValueError("the service returned a different number of phones")
    return [
        {
            "phone": p,
            "gop": g["gop"],
            "heard": g["competitor"],
            "dropped": is_dropped(g),
        }
        for p, g in zip(phones, got, strict=True)
    ]
