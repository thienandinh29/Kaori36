"""NGSL 1.2 and NAWL 1.2 headwords from the official files (specs/vocabulary-import, steps 1-3).

New General Service List and New Academic Word List by Browne, C., Culligan, B., and Phillips, J.,
CC BY-SA 4.0 (https://www.newgeneralservicelist.com). Only the headword, its easy-English
definition, its inflected forms and a frequency figure are taken; everything else is written later
and marked draft. Levels are estimated from frequency, never presented as official CEFR levels.
"""

import csv
import io
import re
import unicodedata
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from xml.etree import ElementTree

from app.curriculum.course import Level

Source = Literal["ngsl", "nawl"]
FILES: dict[str, str] = {
    "ngsl_stats": "NGSL_12_stats.csv",  # frequency rank (SFI) per headword
    "ngsl_definitions": "NGSL_12_with_English_definitions.xlsx",
    "ngsl_forms": "NGSL_12_lemmatized_for_teaching.csv",
    "nawl_definitions": "NAWL_12_with_en_definitions.csv",  # with the part of speech
    "nawl_forms": "NAWL_12_lemmatized_for_teaching.csv",
    "sfi_31k": "NGSLwithSFI-31K.xlsx",  # the SFI of ~31k words: orders the NAWL by frequency
    "ngsl_supplement": "SUP_lemmatized.csv",  # days, months, numbers (no rank): the narration check
}
BASE_URL = "https://www.newgeneralservicelist.com/s/"
# NGSL frequency rank -> level (the owner's decision, 16 Nov 2026); the rest of the NGSL is B2.
NGSL_BANDS: tuple[tuple[int, Level], ...] = ((500, "A1"), (1200, "A2"), (2000, "B1"))
NAWL_POS = {"n": "noun", "n pl.": "noun", "adj": "adjective", "verb": "verb", "adv": "adverb",
            "prep": "preposition"}  # fmt: skip
_LEMMA = re.compile(r"^[a-z][a-z' -]*$")
_SHEET = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


@dataclass(frozen=True)
class Headword:
    lemma: str
    source: Source
    level: Level
    definition: str
    forms: tuple[str, ...]  # the lemma first, then its inflections
    pos: str | None = None  # NAWL gives one; for the NGSL the model chooses
    rank: int | None = None  # NGSL frequency rank


@dataclass(frozen=True)
class Dropped:
    lemma: str
    source: Source
    reason: str


def clean(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split())


def xlsx_rows(path: Path) -> Iterator[dict[str, str]]:
    """The first sheet's rows as {column letter: text}; enough for these two plain files."""
    with zipfile.ZipFile(path) as book:
        strings = [
            "".join(t.text or "" for t in si.iter(_SHEET + "t"))
            for si in ElementTree.fromstring(book.read("xl/sharedStrings.xml")).iter(_SHEET + "si")
        ]
        with book.open("xl/worksheets/sheet1.xml") as sheet:
            for _, row in ElementTree.iterparse(sheet):
                if row.tag != _SHEET + "row":
                    continue
                out: dict[str, str] = {}
                for cell in row.iter(_SHEET + "c"):
                    value = cell.find(_SHEET + "v")
                    if value is None or value.text is None:
                        continue
                    column = re.sub(r"\d", "", cell.get("r", ""))
                    out[column] = strings[int(value.text)] if cell.get("t") == "s" else value.text
                row.clear()
                yield out


def _csv(path: Path) -> list[list[str]]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")  # the NAWL form lists are ISO-8859-1
    return [r for r in csv.reader(io.StringIO(text)) if r and not r[0].startswith("##")]


def forms(path: Path) -> dict[str, tuple[str, ...]]:
    return {
        r[0].strip().lower(): tuple(clean(f).lower() for f in r if f.strip()) for r in _csv(path)
    }


def ngsl_level(rank: int) -> Level:
    return next((level for top, level in NGSL_BANDS if rank <= top), "B2")


def nawl_levels(lemmas: list[str], sfi: dict[str, float]) -> dict[str, Level]:
    """The more frequent half B2, the rest C1; a word without a frequency figure is C1."""
    ordered = sorted(lemmas, key=lambda w: -sfi.get(w, -1.0))
    half = (len(ordered) + 1) // 2
    return {w: "B2" if i < half and w in sfi else "C1" for i, w in enumerate(ordered)}


def _check(lemma: str, definition: str, source: Source) -> str | None:
    from app.vocabulary.wordlist import occurrences

    if not _LEMMA.match(lemma) or len(lemma) > 40:
        return "not a plain lowercase headword"
    if len(definition) < 5:
        return "no definition"
    if occurrences(lemma, definition):
        return "the definition contains the word itself"
    return None


def read(folder: Path) -> tuple[list[Headword], list[Dropped]]:
    """Every headword with a usable definition, NGSL first, and what was left out and why."""
    words: list[Headword] = []
    dropped: list[Dropped] = []
    ranks = {r[0].strip().lower(): int(r[1]) for r in _csv(folder / FILES["ngsl_stats"])[1:]}
    ngsl_forms = forms(folder / FILES["ngsl_forms"])
    rows = list(xlsx_rows(folder / FILES["ngsl_definitions"]))[1:]  # header: Word, Definitions
    for row in rows:
        lemma, definition = clean(row.get("A", "")).lower(), clean(row.get("B", ""))
        why = _check(lemma, definition, "ngsl") or (None if lemma in ranks else "no frequency rank")
        if why:
            dropped.append(Dropped(lemma, "ngsl", why))
            continue
        words.append(Headword(lemma, "ngsl", ngsl_level(ranks[lemma]), definition,
                              ngsl_forms.get(lemma, (lemma,)), rank=ranks[lemma]))  # fmt: skip
    seen = {w.lemma for w in words} | {d.lemma for d in dropped}
    sfi = {
        clean(r["A"]).lower(): float(r["D"])
        for r in list(xlsx_rows(folder / FILES["sfi_31k"]))[1:]
        if r.get("A") and r.get("D")
    }
    nawl_forms = forms(folder / FILES["nawl_forms"])
    candidates: list[tuple[str, str, str]] = []
    for r in _csv(folder / FILES["nawl_definitions"])[1:]:
        lemma, definition, pos = clean(r[0]).lower(), clean(r[1]), clean(r[2])
        if lemma in seen:
            dropped.append(Dropped(lemma, "nawl", "already in the NGSL"))
            continue
        seen.add(lemma)
        why = _check(lemma, definition, "nawl") or (
            None if pos in NAWL_POS else f"part of speech {pos!r} is not practised"
        )
        if why:
            dropped.append(Dropped(lemma, "nawl", why))
            continue
        candidates.append((lemma, definition, NAWL_POS[pos]))
    levels = nawl_levels([c[0] for c in candidates], sfi)
    for lemma, definition, pos in candidates:
        words.append(Headword(lemma, "nawl", levels[lemma], definition,
                              nawl_forms.get(lemma, (lemma,)), pos=pos))  # fmt: skip
    return words, dropped


SUPPLEMENT = FILES["ngsl_supplement"]


@dataclass(frozen=True)
class FormEntry:
    headword: str
    level: Level
    forms: tuple[str, ...]  # the headword first


def form_index(folder: Path) -> dict[str, FormEntry]:
    """Every NGSL and NAWL headword with its estimated level and inflected forms.

    Unlike `read`, nothing is left out: function words and the supplementary list are kept, because
    the lesson narration check needs them (specs/grammar-lessons). Levels use the same bands.
    """
    out: dict[str, FormEntry] = {}
    ranks = {r[0].strip().lower(): int(r[1]) for r in _csv(folder / FILES["ngsl_stats"])[1:]}
    for head, words in forms(folder / FILES["ngsl_forms"]).items():
        if head in ranks:
            out[head] = FormEntry(head, ngsl_level(ranks[head]), words)
    if (folder / SUPPLEMENT).is_file():
        for head, words in forms(folder / SUPPLEMENT).items():
            out.setdefault(head, FormEntry(head, "A1", words))
    sfi = {
        clean(r["A"]).lower(): float(r["D"])
        for r in list(xlsx_rows(folder / FILES["sfi_31k"]))[1:]
        if r.get("A") and r.get("D")
    }
    nawl = {h: w for h, w in forms(folder / FILES["nawl_forms"]).items() if h not in out}
    for head, level in nawl_levels(list(nawl), sfi).items():
        out[head] = FormEntry(head, level, nawl[head])
    return out
