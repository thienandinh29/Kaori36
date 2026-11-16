# ruff: noqa: RUF001, RUF002, RUF003  (IPA symbols are the point of this module)
"""Do two IPA transcriptions of a word say the same thing? (specs/vocabulary-import, step 5)

The imported list shows a word's IPA only when two independent sources agree: espeak-ng (rules) and
the model. Transcriptions differ in notation as well as in substance, so both are first put in one
notation. Only notation is normalised here; a different vowel, consonant or stressed syllable
stays a disagreement, and the word then gets no IPA (the owner's rule: never fill a disagreement).

Notation folded together (each a convention, not a different pronunciation):
- espeak's symbols: ɹ→r, ɐ→ə, ɛ→e, ᵻ→ɪ, g→ɡ, iə→ɪə (the NEAR vowel); syllabic n̩ l̩ → ən əl;
- vowel length marks (iː/i, uː/u: the weak forms dictionaries write without length);
- the word-final happY vowel (ɪ/i);
- secondary stress, which dictionaries often leave out.
Primary stress is kept and compared by syllable: espeak puts the mark before the vowel, dictionaries
before the syllable, so the stress is the index of the vowel group that follows the mark.
"""

from dataclasses import dataclass

VOWELS = set("aeiouæɑɒɔəɜɪʊʌɐɛᵻɚɝøœɘɵ")
PRIMARY, SECONDARY, LENGTH = "ˈ", "ˌ", "ː"
_SYMBOLS = {
    "ɹ": "r",
    "ɐ": "ə",
    "ɛ": "e",
    "ᵻ": "ɪ",
    "g": "ɡ",
    "ɾ": "t",
    "'": PRIMARY,
    ",": SECONDARY,
}
_SYLLABIC = "̩"  # combining vertical line below


@dataclass(frozen=True)
class Shape:
    """A transcription reduced to its sounds and the syllable that carries the primary stress."""

    sounds: str
    stress: int | None  # index of the stressed vowel group; None: not marked


def shape(ipa: str) -> Shape | None:
    """The comparable form of a transcription, or None when it is not one word's IPA."""
    text = ipa.strip().strip("/[]").replace(" ", "").replace(".", "")
    if not text or any(c.isdigit() for c in text):
        return None
    for consonant in "nlm":
        text = text.replace(consonant + _SYLLABIC, "ə" + consonant)
    text = "".join(_SYMBOLS.get(c, c) for c in text).replace(LENGTH, "").replace(SECONDARY, "")
    text = text.replace("iə", "ɪə")
    if text.count(PRIMARY) > 1:
        return None
    groups, stress, previous_vowel = 0, None, False
    for c in text:
        if c == PRIMARY:
            stress, previous_vowel = groups, False
            continue
        vowel = c in VOWELS
        if vowel and not previous_vowel:
            groups += 1
        previous_vowel = vowel
    sounds = text.replace(PRIMARY, "")
    if sounds.endswith("ɪ"):  # happY: dictionaries write i, espeak ɪ
        sounds = sounds[:-1] + "i"
    if groups == 1:
        stress = 0  # one syllable: the mark is optional
    return Shape(sounds, stress)


def agree(a: str, b: str) -> bool:
    """True when both transcriptions give the same sounds and stress the same syllable."""
    x, y = shape(a), shape(b)
    return x is not None and y is not None and x.stress is not None and x == y
