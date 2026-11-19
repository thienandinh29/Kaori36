"""The audio check for synthetic Listening (specs/listening-reading/step-4.4a.md).

A Listening answer must be heard, not only written in the script: after a script line is voiced
and transcribed, each answer on that line must appear, in order and contiguous, in the normalised
transcript. Every rule here errs towards "not recovered": a false "not recovered" costs an item, a
false "recovered" would serve an unhearable answer.
Pure: no audio, no recogniser, no database.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

MAX_ATTEMPTS = 2

_UNIT_WORDS = (
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen"
    " sixteen seventeen eighteen nineteen"
)
_ORDINAL_WORDS = (
    "first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth thirteenth"
    " fourteenth fifteenth sixteenth seventeenth eighteenth nineteenth"
)
_TENS_WORDS = "twenty thirty forty fifty sixty seventy eighty ninety"
_UNITS = {w: i for i, w in enumerate(_UNIT_WORDS.split())}
_TENS = {w: 10 * i for i, w in enumerate(_TENS_WORDS.split(), start=2)}
_ORDINAL_UNITS = {w: i for i, w in enumerate(_ORDINAL_WORDS.split(), start=1)}
_ORDINAL_TENS = {"twentieth": 20, "thirtieth": 30}
_REPEAT = {"double": 2, "triple": 3}
_ZERO_WORDS = {"oh", "nought"}


def _is_digit_word(token: str) -> bool:
    """A single spoken digit (or a written one), the only thing "double"/"triple" may repeat."""
    return (
        (token.isdigit() and len(token) == 1) or _UNITS.get(token, 99) < 10 or token in _ZERO_WORDS
    )


def _numeric(token: str) -> bool:
    return token.isdigit() or token in _UNITS or token in _TENS or token in _REPEAT


def _word_number(tokens: Sequence[str], i: int) -> tuple[int, int] | None:
    """Number words from tokens[i]: (value, next index) or None; "eleven thirty" stops at eleven."""
    total = current = 0
    last: str | None = None
    j = i
    while j < len(tokens):
        w = tokens[j]
        unit = _UNITS.get(w, _ORDINAL_UNITS.get(w))
        tens = _TENS.get(w, _ORDINAL_TENS.get(w))
        if unit is not None:
            if not (last in (None, "hundred", "thousand") or (last == "tens" and unit < 10)):
                break
            current += unit
            last = "unit"
        elif tens is not None:
            if last not in (None, "hundred", "thousand"):
                break
            current += tens
            last = "tens"
        elif w in ("hundred", "thousand") and last in ("unit", "tens") and 0 < current < 100:
            if w == "hundred":
                current *= 100
            else:
                total += current * 1000
                current = 0
            last = w
            j += 1
            if (
                j + 1 < len(tokens)
                and tokens[j] == "and"
                and (tokens[j + 1] in _UNITS or tokens[j + 1] in _TENS)
            ):
                j += 1
            continue
        elif w in ("hundred", "thousand") and last == "hundred" and w == "thousand":
            total += current * 1000
            current = 0
            last = w
            j += 1
            continue
        else:
            break
        j += 1
        if w in _ORDINAL_UNITS or w in _ORDINAL_TENS:
            break  # an ordinal ends its number
    if last is None:
        return None
    return total + current, j


def _numbers(tokens: list[str]) -> list[str]:
    """Number words and repeats to digit groups; consecutive digit groups joined into one token."""
    tokens = [
        "0"
        if t in _ZERO_WORDS
        and (
            (k > 0 and _numeric(tokens[k - 1])) or (k + 1 < len(tokens) and _numeric(tokens[k + 1]))
        )
        else t
        for k, t in enumerate(tokens)
    ]
    groups: list[tuple[str, bool]] = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in _REPEAT and i + 1 < len(tokens) and _is_digit_word(tokens[i + 1]):
            nxt = tokens[i + 1]
            digit = nxt if nxt.isdigit() else "0" if nxt in _ZERO_WORDS else str(_UNITS[nxt])
            groups.append((digit * _REPEAT[t], True))
            i += 2
            continue
        if t.isdigit():
            groups.append((t, True))
            i += 1
            continue
        parsed = _word_number(tokens, i)
        if parsed is not None:
            groups.append((str(parsed[0]), True))
            i = parsed[1]
            continue
        groups.append((t, False))
        i += 1
    joined: list[str] = []
    previous_digit = False
    for text, is_digit in groups:
        if is_digit and previous_digit:
            joined[-1] += text
        else:
            joined.append(text)
        previous_digit = is_digit
    return joined


def _spelled(tokens: list[str]) -> list[str]:
    """Three or more single letters in a row are one spelled word: "h e n r y" → "henry"."""
    out: list[str] = []
    run: list[str] = []
    for t in [*tokens, ""]:
        if len(t) == 1 and t.isalpha():
            run.append(t)
            continue
        out.extend(["".join(run)] if len(run) >= 3 else run)
        run = []
        if t:
            out.append(t)
    return out


def normalise(text: str) -> list[str]:
    """The comparable words of a script line, an answer or a transcript (one function for all)."""
    s = unicodedata.normalize("NFC", text).lower()
    s = re.sub("['\u2019`]", "", s)
    s = re.sub(r"£\s*(\d+)(?:\.(\d{1,2}))?", lambda m: f" {m[1]} pounds {m[2] or ''} ", s)
    s = re.sub(r"\$\s*(\d+)(?:\.(\d{1,2}))?", lambda m: f" {m[1]} dollars {m[2] or ''} ", s)
    s = re.sub(r"(\d)\s*%", r"\1 per cent ", s)
    s = re.sub(r"\b(\d+)(?:st|nd|rd|th)\b", r"\1", s)
    s = re.sub(r"(?<=\d)[:.,](?=\d)", " ", s)
    s = re.sub(r"[\W_]+", " ", s)
    tokens: list[str] = []
    for t in s.split():
        tokens.extend(["per", "cent"] if t == "percent" else [t])
    return _spelled(_numbers(tokens))


def _contains(haystack: Sequence[str], needle: Sequence[str]) -> bool:
    n = len(needle)
    return n > 0 and any(
        list(haystack[k : k + n]) == list(needle) for k in range(len(haystack) - n + 1)
    )


def recovered(answer: str, transcript: str) -> bool:
    """True when the answer's words appear, in order and contiguous, in the transcript."""
    return _contains(normalise(transcript), normalise(answer))


Reason = Literal["recovered", "not_heard", "not_in_script"]


@dataclass(frozen=True)
class Result:
    answer: str
    line: int | None  # the script line the answer is on; None when it is on no line
    reason: Reason

    @property
    def ok(self) -> bool:
        return self.reason == "recovered"


def check(lines: Sequence[str], answers: Sequence[str], transcripts: Sequence[str]) -> list[Result]:
    """Each answer against the transcript of the first script line that contains it."""
    if len(lines) != len(transcripts):
        raise ValueError(f"{len(lines)} script lines but {len(transcripts)} transcripts")
    script = [normalise(line) for line in lines]
    results: list[Result] = []
    for answer in answers:
        words = normalise(answer)
        line = next((k for k, s in enumerate(script) if _contains(s, words)), None)
        if line is None:
            results.append(Result(answer, None, "not_in_script"))
        else:
            heard = _contains(normalise(transcripts[line]), words)
            results.append(Result(answer, line, "recovered" if heard else "not_heard"))
    return results


@dataclass(frozen=True)
class Decision:
    resynthesise: tuple[int, ...]  # lines to voice again more slowly, then check again
    dropped: tuple[str, ...]  # answers whose questions are never served

    @property
    def passed(self) -> bool:
        return not self.resynthesise and not self.dropped


def decide(results: Sequence[Result], attempt: int) -> Decision:
    """After attempt `attempt` (1-based): retry unheard lines slower until MAX_ATTEMPTS, then drop.

    An answer missing from its script is a generation fault, dropped at once (re-voicing cannot
    fix it).
    """
    dropped = [r.answer for r in results if r.reason == "not_in_script"]
    unheard = [r for r in results if r.reason == "not_heard"]
    if attempt < MAX_ATTEMPTS:
        lines = tuple(sorted({r.line for r in unheard if r.line is not None}))
        return Decision(lines, tuple(dropped))
    return Decision((), tuple(dropped + [r.answer for r in unheard]))
