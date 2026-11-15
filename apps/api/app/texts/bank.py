"""The text bank: texts the owner added, each tied to a verified source.

Spec: specs/listening-reading/step-4.1.md.

The licence is copied from the source at load; a text can never claim one its source lacks.
"""

import hashlib
import sys
import unicodedata
from collections.abc import Collection
from datetime import date
from pathlib import Path
from typing import Annotated

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError

from app.sources.candidates import Candidates, load_candidates
from app.texts.features import TextFeatures, features
from app.writing.analysis import words

MIN_WORDS = 80
MAX_WORDS = 1200
Slug = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=60)]
REPO = Path(__file__).resolve().parents[4]
DEFAULT_DIR = REPO / "data" / "english" / "texts"
DEFAULT_CANDIDATES = REPO / "data" / "sources" / "english-candidates.yaml"


class TextEntry(BaseModel):
    """What the owner writes in a text file."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    slug: Slug
    title: str = Field(min_length=1)
    source: Slug  # a slug from the candidates file
    url: HttpUrl
    author: str | None = None
    retrieved_on: date
    text: str = Field(min_length=1)


class BankText(BaseModel):
    """A loaded text: the entry, the licence copied from its source, and its measured features."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    entry: TextEntry
    text: str  # NFC-normalised
    licence: str
    checked_on: date
    share_alike: bool
    non_commercial: bool
    features: TextFeatures


class Refusal(BaseModel):
    model_config = ConfigDict(frozen=True)
    where: str
    reason: str


class Bank(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    texts: tuple[BankText, ...] = ()
    refused: tuple[Refusal, ...] = ()


def _flags(licence: str) -> tuple[bool, bool]:
    parts = licence.upper().replace("-", " ").split()
    return "SA" in parts or "SHAREALIKE" in parts, "NC" in parts or "NONCOMMERCIAL" in parts


def admit(
    entry: TextEntry, candidates: Candidates, known: Collection[str] | None = None
) -> BankText | str:
    """The loaded text, or the reason it is refused."""
    source = next((c for c in candidates.candidates if c.slug == entry.source), None)
    if source is None:
        return f"unknown source {entry.source!r}"
    if source.status != "verified" or not (source.licence and source.checked_on):
        return f"source {entry.source!r} is {source.status}: its licence has not been verified"
    text = unicodedata.normalize("NFC", entry.text).strip()
    n = len(words(text))
    if not MIN_WORDS <= n <= MAX_WORDS:
        return f"{n} words; a text must have {MIN_WORDS} to {MAX_WORDS}"
    share_alike, non_commercial = _flags(source.licence)
    return BankText(
        entry=entry,
        text=text,
        licence=source.licence,
        checked_on=source.checked_on,
        share_alike=share_alike,
        non_commercial=non_commercial,
        features=features(text, known),
    )


def load_bank(folder: Path, candidates: Candidates, known: Collection[str] | None = None) -> Bank:
    texts: list[BankText] = []
    refused: list[Refusal] = []
    slugs: set[str] = set()
    digests: dict[str, str] = {}
    for path in sorted(folder.glob("*.y*ml")):
        try:
            entry = TextEntry.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        except (ValidationError, yaml.YAMLError, UnicodeDecodeError, TypeError) as exc:
            refused.append(Refusal(where=path.name, reason=str(exc).splitlines()[0]))
            continue
        result = admit(entry, candidates, known)
        if isinstance(result, str):
            refused.append(Refusal(where=path.name, reason=result))
            continue
        digest = hashlib.sha256(" ".join(result.text.lower().split()).encode()).hexdigest()
        if entry.slug in slugs:
            refused.append(Refusal(where=path.name, reason=f"duplicate slug {entry.slug!r}"))
        elif digest in digests:
            refused.append(Refusal(where=path.name, reason=f"same text as {digests[digest]!r}"))
        else:
            slugs.add(entry.slug)
            digests[digest] = entry.slug
            texts.append(result)
    return Bank(texts=tuple(texts), refused=tuple(refused))


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    folder = Path(args[0]) if args else DEFAULT_DIR
    candidates = Path(args[1]) if len(args) > 1 else DEFAULT_CANDIDATES
    bank = load_bank(folder, load_candidates(candidates))
    for t in bank.texts:
        f = t.features
        flags = ",".join(
            name
            for name, on in (("share-alike", t.share_alike), ("non-commercial", t.non_commercial))
            if on
        )
        print(
            f"{t.entry.slug}\t{t.entry.source}\t{t.licence}\t{f.words}w\t{f.sentences}s\t"
            f"mean {f.mean_sentence_words}\tlong {f.long_word_share}\t"
            f"ttr {f.type_token_ratio}\t{flags}"
        )
    for r in bank.refused:
        print(f"REFUSED {r.where}: {r.reason}")
    print(f"{len(bank.texts)} loaded, {len(bank.refused)} refused")
    return 1 if bank.refused else 0


if __name__ == "__main__":
    raise SystemExit(main())
