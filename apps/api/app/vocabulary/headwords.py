"""NGSL 1.2, NAWL 1.2, TSL 1.2 and BSL 1.20 headwords from the official files.

Spec: specs/vocabulary-import.

New General Service List and New Academic Word List by Browne, C., Culligan, B., and Phillips, J.;
TOEIC Service List and Business Service List by Browne, C. and Culligan, B.; all CC BY-SA 4.0
(https://www.newgeneralservicelist.com). The BSL has no definitions: the model writes them
(`step-tsl-bsl.md`). Only the headword, its easy-English
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

Source = Literal["ngsl", "nawl", "tsl", "bsl"]
FILES: dict[str, str] = {
    "ngsl_stats": "NGSL_12_stats.csv",  # frequency rank (SFI) per headword
    "ngsl_definitions": "NGSL_12_with_English_definitions.xlsx",
    "ngsl_forms": "NGSL_12_lemmatized_for_teaching.csv",
    "nawl_definitions": "NAWL_12_with_en_definitions.csv",  # with the part of speech
    "nawl_forms": "NAWL_12_lemmatized_for_teaching.csv",
    "sfi_31k": "NGSLwithSFI-31K.xlsx",  # the SFI of ~31k words: orders the NAWL by frequency
    "ngsl_supplement": "SUP_lemmatized.csv",  # days, months, numbers (no rank): the narration check
}
# The add-on lists (specs/vocabulary-import/step-tsl-bsl.md), downloaded by the `extra` step only.
EXTRA_FILES: dict[str, str] = {
    "tsl_stats": "TSL_12_stats.csv",  # rank within the TSL (its own corpus): order only
    "tsl_definitions": "TSL_12_definitions.xlsx",
    "tsl_forms": "TSL_12_lemmatized_for_teaching.csv",
    "bsl_stats": "BSL_120_stats.csv",
    "bsl_forms": "BSL_120_lemmatized_for_teaching.csv",
}
# Headwords that are prefixes, not words (the NAWL's were left out the same way).
PREFIXES = frozenset(
    {
        "anti",
        "co",
        "ex",
        "inter",
        "micro",
        "mid",
        "mini",
        "multi",
        "non",
        "post",
        "pre",
        "semi",
        "sub",
    }
)
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

    @property
    def needs_definition(self) -> bool:
        """BSL words: the list has no definition, so the model writes one (blind-checked)."""
        return not self.definition


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


def _sfi(folder: Path) -> dict[str, float]:
    """General-English frequency (SFI) of about 31k words: the scale every list is levelled on."""
    return {
        clean(r["A"]).lower(): float(r["D"])
        for r in list(xlsx_rows(folder / FILES["sfi_31k"]))[1:]
        if r.get("A") and r.get("D")
    }


def ngsl_cuts(folder: Path, sfi: dict[str, float]) -> dict[Level, float]:
    """The lowest general SFI inside each of the NGSL's A1, A2 and B1 bands."""
    cuts: dict[Level, float] = {}
    for r in _csv(folder / FILES["ngsl_stats"])[1:]:
        lemma = r[0].strip().lower()
        if not r[1].strip().isdigit() or lemma not in sfi:
            continue
        level = ngsl_level(int(r[1]))
        if level != "B2":
            cuts[level] = min(cuts.get(level, 1e9), sfi[lemma])
    return cuts


def extra_levels(
    lemmas: list[str], sfi: dict[str, float], cuts: dict[Level, float]
) -> dict[str, Level]:
    """At or above an NGSL band's lowest SFI, that level; the rest like the NAWL (B2 or C1)."""
    out: dict[str, Level] = {}
    rest: list[str] = []
    for w in lemmas:
        x = sfi.get(w)
        level = next(
            (lv for lv in ("A1", "A2", "B1") if x is not None and lv in cuts and x >= cuts[lv]),
            None,
        )
        if level is None:
            rest.append(w)
        else:
            out[w] = level
    return out | nawl_levels(rest, sfi)


def read_extra(folder: Path, known: set[str]) -> tuple[list[Headword], list[Dropped]]:
    """TSL then BSL headwords not in `known` (the list's lemmas); a word in both is the TSL's."""
    sfi = _sfi(folder)
    cuts = ngsl_cuts(folder, sfi)
    definitions = {
        clean(r.get("A", "")).lower(): clean(r.get("B", ""))
        for r in list(xlsx_rows(folder / EXTRA_FILES["tsl_definitions"]))[1:]
    }
    words: list[Headword] = []
    dropped: list[Dropped] = []
    seen = set(known)
    for source in ("tsl", "bsl"):
        src: Source = "tsl" if source == "tsl" else "bsl"
        family = forms(folder / EXTRA_FILES[f"{source}_forms"])
        candidates: list[tuple[str, str]] = []
        for r in _csv(folder / EXTRA_FILES[f"{source}_stats"])[1:]:
            lemma = clean(r[0]).lower()
            if not lemma or lemma in seen:
                continue  # already in the list (or in the TSL): not counted as read twice
            seen.add(lemma)
            definition = definitions.get(lemma, "") if src == "tsl" else ""
            if definition and _check(lemma, definition, src):
                definition = ""  # unusable (it contains the word): the model writes one, checked
            if lemma in PREFIXES:
                why: str | None = "a prefix, not a word"
            elif not _LEMMA.match(lemma) or len(lemma) > 40:
                why = "not a plain lowercase headword"
            else:
                why = None
            if why:
                dropped.append(Dropped(lemma, src, why))
                continue
            candidates.append((lemma, definition))
        levels = extra_levels([c[0] for c in candidates], sfi, cuts)
        for lemma, definition in candidates:
            words.append(
                Headword(lemma, src, levels[lemma], definition, family.get(lemma, (lemma,)))
            )
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
