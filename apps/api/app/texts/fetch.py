"""Fetch the first reading texts (specs/listening-reading/plan.md, CP1).

    uv run python -m app.texts.fetch simple-wiki [--out DIR]   # on the owner's laptop
    uv run python -m app.texts.fetch openstax [--out DIR]
    uv run python -m app.texts.fetch clean [--write]           # the bank's OpenStax texts

Picks come from `data/english/text-picks.yaml`. Each text is written as a bank entry
(`bank.TextEntry`: slug, title, source, url, retrieved_on, text). By default they go to
`data/private/english-texts/`, which is git-ignored: the bank refuses a text until its source is
verified, so nothing is committed before the owner has read the licence. Only prose is kept: whole
paragraphs, 150 to 600 words, never cut mid-paragraph. Figure captions and empty figure
references "()" are removed (an adaptation, which both sources' ShareAlike licences allow).
OpenStax "Link to Learning" boxes (a line pointing to a video or website, with no title) and the
end-of-section matter (summary, quiz, questions, further research, references) are left out: they
are not part of the passage (found by the owner's review, 20 Nov 2026).
"""

import argparse
import json
import re
import subprocess
import time
import unicodedata
import urllib.parse
import urllib.request
from collections.abc import Callable, Collection, Iterable, Sequence
from datetime import date
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from app.sources.openstax import parse_collection, parse_module
from app.writing.analysis import words

REPO = Path(__file__).resolve().parents[4]
PICKS = REPO / "data" / "english" / "text-picks.yaml"
PRIVATE = REPO / "data" / "private" / "english-texts"
MIN_WORDS, MAX_WORDS = 150, 600
# IELTS-length academic passages (an exam passage is 700-900 words): OpenStax texts from 19 Nov.
LONG_MIN, LONG_MAX = 500, 900
# Wikimedia asks for a descriptive agent; no personal contact details are sent.
USER_AGENT = "NodeTrail-text-bank/0.1 (open-source educational project; one request per second)"
# "(White 2012)", "(Smith and Jones 2010a; Lee 2011)", "(Brown et al. 2003)".
CITATION = re.compile(
    r"\s*\((?:[A-Z][\w'.-]*(?:[ ,&]+(?:and|et al\.|[A-Z][\w'.-]*))*"
    r" \d{4}[a-z]?(?:, p+\. ?\d+)?[;,]? ?)+\)"
)
WIKI_API = "https://simple.wikipedia.org/w/api.php"
# OpenStax boxes and sections that are not part of a reading passage, by their CNXML class. The
# other feature boxes ("Beyond the Book", "Sociology in the Real World"...) are titled prose and
# stay. Every class seen in the bank's 30 source modules was looked at (20 Nov 2026).
NOT_PASSAGE = (
    "link-to-learning",
    "summary", "section-summary", "section-quiz", "short-answer", "review-questions",
    "check-understanding", "reflection-questions", "further-research", "references",
)  # fmt: skip


def slugify(text: str) -> str:
    ascii_ = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_.lower()).strip("-")[:60]


def paragraphs(text: str) -> list[str]:
    """Prose paragraphs only: no headings, lists or one-liners."""
    out = []
    for p in re.split(r"\n\s*\n|\n(?==)", text):
        p = re.sub(r"\s*\(\s*\)", "", " ".join(p.split()))  # a figure reference left empty
        p = CITATION.sub("", p)  # author-date citations: not part of an exam-style passage
        if p.startswith(("=", "Figure:", "Table:", "Note:", "Link to Learning")):
            continue
        if len(words(p)) >= 12 and p[-1:] in ".!?\"'":
            out.append(p)
    return out


def trim(paras: Sequence[str], low: int = MIN_WORDS, high: int = MAX_WORDS) -> str | None:
    """Whole paragraphs from the start, as many as fit under `high`; None under `low` words."""
    kept: list[str] = []
    n = 0
    for p in paras:
        k = len(words(p))
        if n + k > high:
            break
        kept.append(p)
        n += k
    return "\n\n".join(kept) if n >= low else None


def entry(slug: str, title: str, source: str, url: str, text: str, on: date) -> dict[str, Any]:
    return {"slug": slug, "title": title, "source": source, "url": url,
            "retrieved_on": on.isoformat(), "text": text}  # fmt: skip


def write(entries: Iterable[dict[str, Any]], out: Path) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for e in entries:
        path = out / f"{e['slug']}.yaml"
        path.write_text(yaml.safe_dump(e, allow_unicode=True, sort_keys=False, width=100), "utf-8")
        paths.append(path)
    return paths


# --- Simple English Wikipedia ------------------------------------------------------------------


Get = Callable[[str], dict[str, Any]]


def http_json(url: str) -> dict[str, Any]:  # pragma: no cover - network
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as r:
        out: dict[str, Any] = json.loads(r.read())
    return out


def simple_wiki(
    titles: Sequence[str], get: Get = http_json, pause: float = 1.0
) -> tuple[list[dict[str, Any]], list[str]]:
    """Entries for the titles, and the titles skipped with why."""
    entries, skipped = [], []
    for i, title in enumerate(titles):
        if i and pause:
            time.sleep(pause)
        query = urllib.parse.urlencode({
            "action": "query", "format": "json", "formatversion": "2", "redirects": "1",
            "prop": "extracts|info|revisions", "explaintext": "1", "exsectionformat": "wiki",
            "inprop": "url", "rvprop": "ids", "titles": title,
        })  # fmt: skip
        page = get(f"{WIKI_API}?{query}")["query"]["pages"][0]
        if page.get("missing"):
            skipped.append(f"{title}: no such page")
            continue
        text = trim(paragraphs(page.get("extract", "")))
        if text is None:
            skipped.append(f"{title}: under {MIN_WORDS} words of prose")
            continue
        revision = page["revisions"][0]["revid"]  # the exact version read, for the record
        url = f"https://simple.wikipedia.org/w/index.php?oldid={revision}"
        entries.append(
            entry(
                f"sw-{slugify(page['title'])}",
                page["title"],
                "simple-wikipedia",
                url,
                text,
                date.today(),
            )
        )
    return entries, skipped


# --- OpenStax ----------------------------------------------------------------------------------


def page_text(blocks: Sequence[str], low: int, high: int, joined: bool) -> str | None:
    """A page's passage: whole paragraphs in order, `low` to `high` words.

    `joined`: paragraphs run on across the page's prose sections (IELTS-length passages);
    otherwise the first section that alone gives enough words (the first bank, 18-19 Nov).
    """
    if joined:
        return trim([p for b in blocks for p in paragraphs(b)], low, high)
    return next((t for t in (trim(paragraphs(b), low, high) for b in blocks) if t), None)


def openstax_texts(
    checkout: Path,
    repo: str,
    collection: str,
    commit: str,
    n: int,
    *,
    skip: Collection[str] = (),
    low: int = LONG_MIN,
    high: int = LONG_MAX,
    joined: bool = True,
) -> list[dict[str, Any]]:
    """Up to `n` new texts, one per chapter at most, never one whose slug is in `skip`.

    A chapter that already has a text in the bank is passed over, so a new run never rewrites a
    text whose questions exist (they would turn stale).
    """
    coll = parse_collection(
        (checkout / "collections" / f"{collection}.collection.xml").read_bytes()
    )
    out: list[dict[str, Any]] = []
    for chapter in coll.chapters:
        if len(out) >= n:
            break
        pages = []
        for module in chapter.modules[1:]:  # the first page of a chapter is its introduction
            path = checkout / "modules" / module / "index.cnxml"
            if not path.exists():
                continue
            uri = f"https://github.com/{repo}/blob/{commit}/modules/{module}/index.cnxml"
            page = parse_module(path.read_bytes(), module=module, chapter_no=chapter.number,
                                chapter=chapter.title, source_uri=uri,
                                drop_classes=NOT_PASSAGE)  # fmt: skip
            slug = f"os-{slugify(collection)[:20]}-{slugify(page.title)}"[:60].strip("-")
            pages.append((slug, uri, page))
        if any(slug in skip for slug, _, _ in pages):
            continue  # this chapter already has a text in the bank
        for slug, uri, page in pages:
            prose = [
                b.text
                for b in page.blocks
                if b.kind == "text" and not re.search(r"\d{3,}|\$|=", b.text[:2000])
            ]
            text = page_text(prose, low, high, joined)
            if text:
                out.append(
                    entry(slug, f"{page.title} ({coll.title})", "openstax-reading", uri, text,
                          date.today())
                )  # fmt: skip
                break
    return out


def _prose(xml: bytes, drop: Collection[str]) -> list[str]:
    page = parse_module(xml, module="", chapter_no=0, chapter="", source_uri="", drop_classes=drop)
    return [p for b in page.blocks if b.kind == "text" for p in paragraphs(b.text)]


def not_passage(xml: bytes) -> set[str]:
    """The paragraphs of a module that come from boxes or sections in `NOT_PASSAGE`."""
    return set(_prose(xml, ())) - set(_prose(xml, NOT_PASSAGE))


def clean(text: str, xml: bytes) -> tuple[str, list[str]]:
    """A bank passage without the paragraphs `not_passage` finds, everything else as it was; and
    the paragraphs removed. Paragraphs are compared as `paragraphs` writes them."""
    drop = not_passage(xml)
    kept: list[str] = []
    removed: list[str] = []
    for para in text.split("\n\n"):
        normal = paragraphs(para)
        (removed if normal and normal[0] in drop else kept).append(para)
    return "\n\n".join(kept), removed


def module_xml(url: str) -> bytes:  # pragma: no cover - network
    """A text's source module at the commit it was taken from (its recorded GitHub URL)."""
    m = re.fullmatch(r"https://github.com/([^/]+/[^/]+)/blob/([0-9a-f]{40})/(.+)", url)
    if m is None:
        raise ValueError(f"not a pinned GitHub file URL: {url}")
    raw = f"https://raw.githubusercontent.com/{m.group(1)}/{m.group(2)}/{m.group(3)}"
    req = urllib.request.Request(raw, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        data: bytes = r.read()
    return data


def clean_bank(bank: Path, write_files: bool) -> int:  # pragma: no cover - network
    changed = 0
    for path in sorted(bank.glob("*.yaml")):
        entry = yaml.safe_load(path.read_text(encoding="utf-8"))
        if entry.get("source") != "openstax-reading":
            continue
        text, removed = clean(entry["text"], module_xml(entry["url"]))
        time.sleep(0.5)
        if not removed:
            continue
        changed += 1
        print(f"{entry['slug']}: {len(removed)} paragraph(s) removed, "
              f"{len(words(entry['text']))} -> {len(words(text))} words")  # fmt: skip
        for para in removed:
            print(f"    - {para[:100]}")
        if write_files:
            entry["text"] = text
            write([entry], bank)
    print(f"{changed} text(s) {'cleaned' if write_files else 'to clean (run with --write)'}")
    return 0


def checkout(repo: str, dest: Path) -> str:  # pragma: no cover - git
    if not (dest / ".git").exists():
        subprocess.run(["git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--no-checkout",
                        f"https://github.com/{repo}.git", str(dest)], check=True)  # fmt: skip
        subprocess.run(["git", "sparse-checkout", "set", "--no-cone", "/collections/",
                        "/modules/*/index.cnxml"], cwd=dest, check=True)  # fmt: skip
        subprocess.run(["git", "checkout", "-q"], cwd=dest, check=True)
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=dest, check=True, capture_output=True,
                          text=True).stdout.strip()  # fmt: skip


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - network
    parser = argparse.ArgumentParser(prog="python -m app.texts.fetch")
    parser.add_argument("source", choices=["simple-wiki", "openstax", "clean"])
    parser.add_argument("--write", action="store_true", help="clean: rewrite the bank's files")
    parser.add_argument("--out", type=Path, default=PRIVATE)
    parser.add_argument("--picks", type=Path, default=PICKS)
    parser.add_argument(
        "--checkouts", type=Path, default=REPO / "data" / "private" / "openstax-checkouts"
    )
    parser.add_argument(
        "--bank", type=Path, default=REPO / "data" / "english" / "texts",
        help="texts already in the bank: their chapters are passed over",
    )  # fmt: skip
    args = parser.parse_args(argv)
    picks = yaml.safe_load(args.picks.read_text(encoding="utf-8"))
    skipped: list[str] = []
    if args.source == "clean":
        return clean_bank(args.bank, args.write)
    if args.source == "simple-wiki":
        entries, skipped = simple_wiki(picks["simple_wikipedia"])
    else:
        entries = []
        for book in picks["openstax"]:
            dest = args.checkouts / book["repo"].split("/")[1]
            commit = checkout(book["repo"], dest)
            have = {p.stem for p in args.bank.glob("*.yaml")} if args.bank.is_dir() else set()
            found = openstax_texts(
                dest, book["repo"], book["collection"], commit, book["texts"], skip=have
            )
            if len(found) < book["texts"]:
                skipped.append(f"{book['collection']}: found {len(found)} of {book['texts']}")
            entries += found
    for path in write(entries, args.out):
        print(f"wrote {path}")
    for s in skipped:
        print(f"skipped {s}")
    print(f"{len(entries)} texts in {args.out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
