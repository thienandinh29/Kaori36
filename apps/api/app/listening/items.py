"""Listening from the Reading bank: dictation and gap-fill (specs/listening-reading/step-4.4b.md).

Pure. Items are built by code from a bank text's own sentences, so every key is right by
construction: the answer is the sentence the voice read. Only sentences the voice can say exactly
qualify (no digits, names, brackets or quotes), because nothing checks the audio yet (step 4.4a
waits for a recogniser).
"""

import difflib
import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

from app.graders.typed import grade_typed

BLANK = "___"
MIN_WORDS, MAX_WORDS, MAX_CHARS = 6, 18, 300
PER_KIND = 3  # dictation and gap-fill sentences per text
Kind = Literal["dictation", "gap"]
COMPETENCY: dict[str, str] = {"dictation": "listening-dictation", "gap": "listening-detail"}

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
_SAFE = re.compile(r"^[A-Za-z][A-Za-z ,.'?!]*[.?!]$")
_WORD = re.compile(r"[a-z]+(?:'[a-z]+)*")
_FUNCTION_TEXT = (
    "about above after again against among because before being below between both could during "
    "every from have having into itself might other their there these those through under until "
    "where which while whose would should shall within without"
)
_FUNCTION_WORDS = frozenset(_FUNCTION_TEXT.split())


@dataclass(frozen=True)
class ListeningItem:
    id: str
    text: str  # the bank text's slug
    kind: Kind
    sentence: str  # what the voice says
    answer: str  # dictation: the sentence; gap: the missing word
    prompt: str | None  # what the learner reads: the gap sentence, nothing for dictation

    @property
    def competency(self) -> str:
        return COMPETENCY[self.kind]


def _ascii(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    return text.replace("\u2019", "'").replace("\u2018", "'")


def sentences(passage: str) -> list[str]:
    """The passage's sentences in order (paragraphs split on blank lines, then sentence ends)."""
    out: list[str] = []
    for para in re.split(r"\n\s*\n", _ascii(passage)):
        flat = " ".join(para.split())
        out.extend(s.strip() for s in _SENTENCE_END.split(flat) if s.strip())
    return out


def safe(sentence: str) -> bool:
    """A sentence the voice says exactly and a learner can write without guessing a spelling."""
    words = sentence.split()
    return (
        MIN_WORDS <= len(words) <= MAX_WORDS
        and len(sentence) <= MAX_CHARS
        and _SAFE.match(sentence) is not None
        and not any(w[0].isupper() for w in words[1:])  # no names or acronyms after the first word
    )


def gap_word(sentence: str) -> str | None:
    """The longest content word of 5+ letters (the first if tied), or None."""
    candidates = [
        w for w in re.findall(r"[A-Za-z]+", sentence)
        if len(w) >= 5 and w.lower() not in _FUNCTION_WORDS and w[0].islower()
    ]  # fmt: skip
    return max(candidates, key=len) if candidates else None


def _spread(n: int, take: int) -> list[int]:
    """`take` indices spread evenly over range(n), in order."""
    if take >= n:
        return list(range(n))
    if take == 1:
        return [n // 2]
    return sorted({round(i * (n - 1) / (take - 1)) for i in range(take)})


def build(slug: str, passage: str) -> list[ListeningItem]:
    """Up to PER_KIND dictation and PER_KIND gap-fill items, alternating through the text."""
    chosen = [s for s in sentences(passage) if safe(s)]
    items: list[ListeningItem] = []
    counts = {"dictation": 0, "gap": 0}
    for n, i in enumerate(_spread(len(chosen), 2 * PER_KIND)):
        s = chosen[i]
        if n % 2 == 0:
            counts["dictation"] += 1
            items.append(
                ListeningItem(
                    f"{slug}-dictation-{counts['dictation']}", slug, "dictation", s, s, None
                )
            )
            continue
        word = gap_word(s)
        if word is None:
            continue
        counts["gap"] += 1
        prompt = re.sub(rf"\b{re.escape(word)}\b", BLANK, s, count=1)
        items.append(ListeningItem(f"{slug}-gap-{counts['gap']}", slug, "gap", s, word, prompt))
    return items


def words(text: str) -> list[str]:
    """Comparable words: NFC, case folded, straight apostrophes, punctuation dropped."""
    return _WORD.findall(_ascii(text).casefold())


WordMark = dict[str, str]


def mark_dictation(sentence: str, typed: str) -> tuple[float, bool, list[WordMark]]:
    """(share of the words right, all right, each word marked right/wrong/missed/extra)."""
    key, given = words(sentence), words(typed)
    marks: list[WordMark] = []
    right = 0
    for op, a1, a2, b1, b2 in difflib.SequenceMatcher(a=key, b=given, autojunk=False).get_opcodes():
        if op == "equal":
            right += a2 - a1
            marks += [{"word": w, "status": "right"} for w in key[a1:a2]]
        elif op == "replace":
            marks += [{"word": w, "status": "wrong"} for w in key[a1:a2]]
            marks += [{"word": w, "status": "extra"} for w in given[b1 + (a2 - a1) : b2]]
        elif op == "delete":
            marks += [{"word": w, "status": "missed"} for w in key[a1:a2]]
        else:
            marks += [{"word": w, "status": "extra"} for w in given[b1:b2]]
    return (right / len(key) if key else 0.0), key == given, marks


def grade(item: ListeningItem, answer: str) -> tuple[float, bool, list[WordMark]]:
    """Score, correct and (dictation) the word marks; a gap is one word, exact after normalising."""
    if item.kind == "dictation":
        return mark_dictation(item.sentence, answer)
    ok = grade_typed(answer, [item.answer])
    return float(ok), ok, []


# --- Shadowing (specs/listening-reading/step-4.4d.md) ---
SHADOW_PER_TEXT = 8
SHADOW_MIN_WORDS, SHADOW_MAX_WORDS = 5, 25
_SHADOW_UNSAFE = re.compile(r"[()\[\]\"“”;:/\\]|https?|www\.")


@dataclass(frozen=True)
class ShadowSentence:
    id: str
    text: str  # the bank text's slug
    sentence: str  # shown and spoken: shadowing reads along


def shadowable(sentence: str) -> bool:
    """Short enough to say in one breath group, with nothing the voice reads oddly."""
    n = len(sentence.split())
    return (
        SHADOW_MIN_WORDS <= n <= SHADOW_MAX_WORDS
        and len(sentence) <= MAX_CHARS
        and _SHADOW_UNSAFE.search(sentence) is None
        and sentence[-1:] in ".?!"
    )


def shadow_sentences(slug: str, passage: str) -> list[ShadowSentence]:
    """Up to SHADOW_PER_TEXT sentences, never one used for dictation or gap-fill (shadowing shows
    the sentence, which would give those answers away)."""
    used = {i.sentence for i in build(slug, passage)}
    pool = [s for s in sentences(passage) if shadowable(s) and s not in used]
    return [
        ShadowSentence(f"{slug}-shadow-{n + 1}", slug, pool[i])
        for n, i in enumerate(_spread(len(pool), SHADOW_PER_TEXT))
    ]
