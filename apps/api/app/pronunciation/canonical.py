# ruff: noqa: RUF001
"""The expected phones of each prompt and where its target sounds are (step 3.3).

Pure: the targets come from rules over the canonical phones, so a new prompt needs no hand-marked
positions and the owner reviews one list. Only the target positions of a prompt are ever judged; the
other phones help the alignment.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml  # type: ignore[import-untyped]

VOWEL_CHARS = set("aeiouæɑɒɔəɜɪʊʌɐɛᵻɚɝøœɘɵy")
FINALS = {"final-t": "t", "final-k": "k", "final-p": "p", "final-s": "s", "final-z": "z"}
ANYWHERE = {
    "th-voiceless": {"θ"},
    "th-voiced": {"ð"},
    "sh-s": {"ʃ"},
    "ch-j": {"tʃ", "dʒ"},
    "r-l": {"ɹ", "l"},
    "long-ee": {"iː"},
    "long-oo": {"uː"},
    "ae-e": {"æ"},
}


@dataclass(frozen=True)
class Word:
    text: str
    phones: tuple[str, ...]


@dataclass(frozen=True)
class Target:
    sound: str  # a sound id from sounds.yaml
    word: int  # index of the word in the prompt
    phone: int  # index of the phone in the whole prompt (the alignment's order)
    text: str  # the word, for the learner


def is_vowel(phone: str) -> bool:
    return phone[0] in VOWEL_CHARS


def load_canonical(path: Path) -> dict[str, list[Word]]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {
        pid: [Word(str(w), tuple(str(p).split())) for w, p in words] for pid, words in raw.items()
    }


def flat(words: Sequence[Word]) -> list[str]:
    return [p for w in words for p in w.phones]


def targets(words: Sequence[Word], sounds: Sequence[str]) -> list[Target]:
    """The positions of the prompt's target sounds, in phone order, each position once."""
    found: dict[int, Target] = {}
    offset = 0
    for i, w in enumerate(words):
        ph = w.phones
        for sound in sounds:
            if sound in FINALS and len(ph) >= 2 and ph[-1] == FINALS[sound]:
                found.setdefault(
                    offset + len(ph) - 1, Target(sound, i, offset + len(ph) - 1, w.text)
                )
            elif sound in ANYWHERE:
                for j, p in enumerate(ph):
                    if p in ANYWHERE[sound]:
                        found.setdefault(offset + j, Target(sound, i, offset + j, w.text))
            elif sound == "clusters":
                for j in cluster_positions(ph):
                    found.setdefault(offset + j, Target(sound, i, offset + j, w.text))
        offset += len(ph)
    return [found[k] for k in sorted(found)]


def cluster_positions(phones: Sequence[str]) -> list[int]:
    """Consonants in a run of two or more at the start or end of a word (street, texts, month)."""
    out: list[int] = []
    start = 0
    while start < len(phones) and not is_vowel(phones[start]):
        start += 1
    if start >= 2:
        out += range(start)
    end = len(phones)
    while end > 0 and not is_vowel(phones[end - 1]):
        end -= 1
    if len(phones) - end >= 2:
        out += range(end, len(phones))
    return sorted(set(out))


def check(
    canonical: Mapping[str, Sequence[Word]],
    prompts: Mapping[str, tuple[str, Sequence[str]]],
    phone_set: set[str],
) -> list[str]:
    """Each prompt has phones for each word, in the model's set, and every target sound occurs."""
    problems = []
    for pid, (text, sounds) in prompts.items():
        words = canonical.get(pid)
        if words is None:
            problems.append(f"{pid}: no canonical phones")
            continue
        said = [t.strip(".,?!").lower() for t in text.split()]
        if [w.text.lower() for w in words] != said:
            problems.append(f"{pid}: words differ from the prompt")
        unknown = sorted({p for p in flat(words) if p not in phone_set})
        if unknown:
            problems.append(f"{pid}: phones not in the model's set: {unknown}")
        hit = {t.sound for t in targets(words, sounds)}
        problems += [f"{pid}: target {s} never occurs" for s in sounds if s not in hit]
    return problems


def phone_set(path: Path) -> set[str]:
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }
