"""How much of the word list does English Wiktionary cover? (vocabulary-import, step-wiktionary)

A measurement, not an import: nothing here changes the word list or what a learner sees. It reads
the wiktextract dump published by kaikki.org (one JSON object per line, every language), keeps the
English entries whose word is one of the list's headwords, and counts what Wiktionary could add:
a British IPA (and whether it agrees with the IPA the list already shows), Vietnamese translations,
recordings, usage examples. The matched entries are cached in git-ignored `data/private/` so later
steps never read the 24 GB file again.

Run on the owner's laptop (Wikimedia refuses the cloud sandbox):
    curl -C - -o data/private/wiktionary/raw-wiktextract-data.jsonl.gz \
        https://kaikki.org/dictionary/raw-wiktextract-data.jsonl.gz
    uv run python -m app.vocabulary.wiktionary scan
    uv run python -m app.vocabulary.wiktionary report   # again from the cache, in seconds
"""

import argparse
import gzip
import hashlib
import json
import re
from collections import Counter
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.config import REPO_ROOT
from app.vocabulary.ipa import agree
from app.vocabulary.wordlist import Word, load_wordlist

WORK = REPO_ROOT / "data" / "private" / "wiktionary"
DUMP = WORK / "raw-wiktextract-data.jsonl.gz"
CACHE = WORK / "en-entries.jsonl"
REPORT = WORK / "coverage.json"
AUTHORED = REPO_ROOT / "data" / "vocabulary" / "core-seed.yaml"
IMPORTED = REPO_ROOT / "data-sa" / "vocabulary"
SOURCE_URL = "https://kaikki.org/dictionary/raw-wiktextract-data.jsonl.gz"

# Our part of speech -> wiktextract's.
POS = {
    "noun": "noun",
    "verb": "verb",
    "adjective": "adj",
    "adverb": "adv",
    "preposition": "prep",
    "conjunction": "conj",
}
# Sound tags that mean a British accent, and those that mean another one. A transcription with
# neither is "untagged": Wiktionary often gives one IPA for all accents, so it is counted apart.
UK_TAGS = frozenset({"UK", "Received-Pronunciation", "British", "England", "Southern-England"})
OTHER_TAGS = frozenset(
    {
        "US",
        "General-American",
        "Canada",
        "Australia",
        "General-Australian",
        "New-Zealand",
        "Ireland",
        "Scotland",
        "Northern-England",
        "Wales",
        "India",
        "South-Africa",
    }
)
_PARENS = re.compile(r"\([^)]*\)")
_TIE, _NON_SYLLABIC = "͡", "̯"  # combining tie bar, non-syllabic mark
_ENGLISH = ('"lang_code": "en"', '"lang_code":"en"')


# --- reading the dump ---------------------------------------------------------------------------


def english_entries(lines: Iterable[str], words: set[str]) -> Iterator[dict[str, Any]]:
    """The English entries (`lang_code` "en" at the top level) whose word is in `words`.

    A cheap substring test skips most of the other languages before any JSON is parsed; the
    top-level check after parsing is what decides.
    """
    for line in lines:
        if not any(marker in line for marker in _ENGLISH):
            continue
        entry = json.loads(line)
        if entry.get("lang_code") == "en" and entry.get("word") in words:
            yield entry


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def scan(dump: Path, cache: Path, words: set[str]) -> int:
    """Write the matched entries to `cache` (one per line); the number written."""
    cache.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with gzip.open(dump, "rt", encoding="utf-8") as src, cache.open("w", encoding="utf-8") as out:
        for entry in english_entries(src, words):
            out.write(json.dumps(entry, ensure_ascii=False) + "\n")
            written += 1
    return written


def read_cache(cache: Path) -> list[dict[str, Any]]:
    with cache.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# --- what one entry offers (pure) ---------------------------------------------------------------


def accent(tags: Iterable[str]) -> str:
    """'uk', 'other' or 'untagged' for a sound's tags (British wins when both appear)."""
    tagset = set(tags)
    if tagset & UK_TAGS:
        return "uk"
    if tagset & OTHER_TAGS:
        return "other"
    return "untagged"


def ipas(entry: dict[str, Any], which: str) -> list[str]:
    """The entry's IPA strings for one accent class, in order, without repeats."""
    seen: list[str] = []
    for sound in entry.get("sounds", ()):
        ipa = sound.get("ipa")
        if ipa and accent(sound.get("tags", ())) == which and ipa not in seen:
            seen.append(ipa)
    return seen


def audio(entry: dict[str, Any], which: str) -> list[str]:
    """Recording URLs for one accent class (the file name's En-uk-/En-us- counts as a tag)."""
    urls: list[str] = []
    for sound in entry.get("sounds", ()):
        url = sound.get("ogg_url") or sound.get("mp3_url")
        if not url:
            continue
        name = str(sound.get("audio", "")).lower()
        tags = list(sound.get("tags", ()))
        if name.startswith(("en-uk-", "en-gb-")):
            tags.append("UK")
        elif name.startswith("en-us-"):
            tags.append("US")
        if accent(tags) == which:
            urls.append(url)
    return urls


def vietnamese(entry: dict[str, Any]) -> list[str]:
    """Vietnamese translations (code "vi"), at the top level or inside senses."""
    found: list[str] = []
    places = [entry.get("translations", ())]
    places += [s.get("translations", ()) for s in entry.get("senses", ())]
    for translations in places:
        for t in translations:
            word = t.get("word")
            if t.get("code") == "vi" and word and word not in found:
                found.append(word)
    return found


def usage_examples(entry: dict[str, Any]) -> list[str]:
    """Usage examples (type "example"), not dated quotations from books."""
    return [
        e["text"]
        for s in entry.get("senses", ())
        for e in s.get("examples", ())
        if e.get("type") == "example" and e.get("text")
    ]


def ipa_agrees(ours: str, theirs: str) -> bool:
    """`ipa.agree` after Wiktionary's notation is folded (notation only, as in `ipa.py`).

    Only phonemic /…/ transcriptions are compared (a narrow [...] one is not); the tie bar of t͡ʃ d͡ʒ
    and the non-syllabic mark of ə̯ are dropped; an optional sound in round brackets, such as (ɹ) or
    (ʊ), may be said or not, so both readings are tried.
    """
    if not theirs.startswith("/"):
        return False
    text = theirs.replace(_TIE, "").replace(_NON_SYLLABIC, "")
    readings = {_PARENS.sub("", text), text.replace("(", "").replace(")", "")}
    return any(agree(ours, r) for r in readings)


# --- the coverage of the list (pure) ------------------------------------------------------------


@dataclass
class Coverage:
    words: int = 0
    found: int = 0  # any English entry with this headword
    found_same_pos: int = 0  # an entry with the list's part of speech
    uk_ipa: int = 0  # a British-tagged IPA on a same-pos entry (any entry when none has that pos)
    untagged_ipa_only: int = 0  # no British IPA, but an IPA with no accent tag
    vi: int = 0
    uk_audio: int = 0
    any_audio: int = 0
    usage_example: int = 0
    ours_with_ipa: int = 0  # the list shows an IPA (authored, or model and espeak agreed)
    ours_with_ipa_and_uk: int = 0
    ipa_agree: int = 0  # ... and one of Wiktionary's British IPAs agrees with it
    ours_without_ipa_gain_uk: int = 0  # the list has no IPA; Wiktionary has a British one
    by_origin: dict[str, dict[str, int]] = field(default_factory=dict)
    sound_tags: dict[str, int] = field(default_factory=dict)
    disagreements: list[dict[str, str]] = field(default_factory=list)  # a sample to look at
    missing: list[str] = field(default_factory=list)


def _choose(word: Word, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    same = [e for e in entries if e.get("pos") == POS[word.pos]]
    return same or entries


def coverage(
    words: Sequence[Word], entries: Iterable[dict[str, Any]], sample: int = 40
) -> Coverage:
    by_word: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        by_word.setdefault(entry["word"], []).append(entry)
    c = Coverage(words=len(words))
    tags: Counter[str] = Counter()
    origins: dict[str, Counter[str]] = {}
    for word in words:
        o = origins.setdefault(word.origin, Counter())
        o["words"] += 1
        mine = by_word.get(word.lemma, [])
        if not mine:
            c.missing.append(word.key)
            continue
        c.found += 1
        o["found"] += 1
        if any(e.get("pos") == POS[word.pos] for e in mine):
            c.found_same_pos += 1
        chosen = _choose(word, mine)
        for e in chosen:
            for sound in e.get("sounds", ()):
                if sound.get("ipa"):
                    tags.update(sound.get("tags", ()) or ["(none)"])
        uk = [i for e in chosen for i in ipas(e, "uk")]
        untagged = [i for e in chosen for i in ipas(e, "untagged")]
        if uk:
            c.uk_ipa += 1
            o["uk_ipa"] += 1
        elif untagged:
            c.untagged_ipa_only += 1
        if any(vietnamese(e) for e in chosen):
            c.vi += 1
            o["vi"] += 1
        if any(audio(e, "uk") for e in chosen):
            c.uk_audio += 1
        if any(audio(e, w) for e in chosen for w in ("uk", "other", "untagged")):
            c.any_audio += 1
        if any(usage_examples(e) for e in chosen):
            c.usage_example += 1
        if word.ipa:
            c.ours_with_ipa += 1
            if uk:
                c.ours_with_ipa_and_uk += 1
                if any(ipa_agrees(word.ipa, i) for i in uk):
                    c.ipa_agree += 1
                elif len(c.disagreements) < sample:
                    c.disagreements.append(
                        {"word": word.key, "ours": word.ipa, "wiktionary": " ".join(uk)}
                    )
        elif uk:
            c.ours_without_ipa_gain_uk += 1
    c.by_origin = {k: dict(v) for k, v in sorted(origins.items())}
    c.sound_tags = dict(tags.most_common(25))
    return c


def share(part: int, whole: int) -> str:
    return f"{part}/{whole} ({100 * part / whole:.1f}%)" if whole else f"{part}/0"


def summary(c: Coverage) -> dict[str, str]:
    return {
        "found (any part of speech)": share(c.found, c.words),
        "found with the list's part of speech": share(c.found_same_pos, c.words),
        "British IPA": share(c.uk_ipa, c.words),
        "only an IPA with no accent tag": share(c.untagged_ipa_only, c.words),
        "Vietnamese translation": share(c.vi, c.words),
        "British recording": share(c.uk_audio, c.words),
        "any recording": share(c.any_audio, c.words),
        "a usage example (not a quotation)": share(c.usage_example, c.words),
        "our IPA agrees with a British one": share(c.ipa_agree, c.ours_with_ipa_and_uk),
        "words with no IPA now that would get a British one": share(
            c.ours_without_ipa_gain_uk, c.words - c.ours_with_ipa
        ),
    }


# --- command line -------------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.vocabulary.wiktionary")
    parser.add_argument("command", choices=["scan", "report"])
    parser.add_argument("--dump", type=Path, default=DUMP)
    parser.add_argument("--cache", type=Path, default=CACHE)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args(argv)
    words = load_wordlist(AUTHORED, IMPORTED).words
    source: dict[str, str] = {}
    if args.command == "scan":
        if not args.dump.is_file():
            parser.error(f"{args.dump} not found; download {SOURCE_URL} first (see the module doc)")
        source = {"url": SOURCE_URL, "file": args.dump.name, "sha256": sha256(args.dump)}
        n = scan(args.dump, args.cache, {w.lemma for w in words})
        print(f"{n} English entries kept in {args.cache}")
    if not args.cache.is_file():
        parser.error(f"{args.cache} not found; run `scan` first")
    if not source and args.report.is_file():
        source = json.loads(args.report.read_text(encoding="utf-8")).get("source", {})
    c = coverage(words, read_cache(args.cache))
    result = {"source": source, "summary": summary(c), **asdict(c)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps({"summary": result["summary"]}, indent=2, ensure_ascii=False))
    print(f"full report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
