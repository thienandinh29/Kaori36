"""Fetch the first reading texts (specs/listening-reading/plan.md, CP1).

    uv run python -m app.texts.fetch simple-wiki [--out DIR]   # on the owner's laptop
    uv run python -m app.texts.fetch openstax [--out DIR]

Picks come from `data/english/text-picks.yaml`. Each text is written as a bank entry
(`bank.TextEntry`: slug, title, source, url, retrieved_on, text). By default they go to
`data/private/english-texts/`, which is git-ignored: the bank refuses a text until its source is
verified, so nothing is committed before the owner has read the licence. Only prose is kept: whole
paragraphs, 150 to 600 words, never cut mid-paragraph. Figure captions and empty figure
references "()" are removed (an adaptation, which both sources' ShareAlike licences allow).
"""

import argparse
import json
import re
import subprocess
import time
import unicodedata
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable, Sequence
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
# Wikimedia asks for a descriptive agent; no personal contact details are sent.
USER_AGENT = "NodeTrail-text-bank/0.1 (open-source educational project; one request per second)"
WIKI_API = "https://simple.wikipedia.org/w/api.php"


def slugify(text: str) -> str:
    ascii_ = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_.lower()).strip("-")[:60]


def paragraphs(text: str) -> list[str]:
    """Prose paragraphs only: no headings, lists or one-liners."""
    out = []
    for p in re.split(r"\n\s*\n|\n(?==)", text):
        p = re.sub(r"\s*\(\s*\)", "", " ".join(p.split()))  # a figure reference left empty
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


def openstax_texts(
    checkout: Path, repo: str, collection: str, commit: str, n: int
) -> list[dict[str, Any]]:
    """Up to `n` texts, one per chapter at most: the first prose section of 150-600 words."""
    coll = parse_collection(
        (checkout / "collections" / f"{collection}.collection.xml").read_bytes()
    )
    out: list[dict[str, Any]] = []
    for chapter in coll.chapters:
        if len(out) >= n:
            break
        for module in chapter.modules[1:]:  # the first page of a chapter is its introduction
            path = checkout / "modules" / module / "index.cnxml"
            if not path.exists():
                continue
            uri = f"https://github.com/{repo}/blob/{commit}/modules/{module}/index.cnxml"
            page = parse_module(path.read_bytes(), module=module, chapter_no=chapter.number,
                                chapter=chapter.title, source_uri=uri)  # fmt: skip
            prose = [
                b
                for b in page.blocks
                if b.kind == "text" and not re.search(r"\d{3,}|\$|=", b.text[:2000])
            ]
            text = next((t for t in (trim(paragraphs(b.text)) for b in prose) if t), None)
            if text:
                slug = f"os-{slugify(collection)[:20]}-{slugify(page.title)}"[:60].strip("-")
                out.append(
                    entry(
                        slug,
                        f"{page.title} ({coll.title})",
                        "openstax-reading",
                        uri,
                        text,
                        date.today(),
                    )
                )
                break
    return out


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
    parser.add_argument("source", choices=["simple-wiki", "openstax"])
    parser.add_argument("--out", type=Path, default=PRIVATE)
    parser.add_argument("--picks", type=Path, default=PICKS)
    parser.add_argument(
        "--checkouts", type=Path, default=REPO / "data" / "private" / "openstax-checkouts"
    )
    args = parser.parse_args(argv)
    picks = yaml.safe_load(args.picks.read_text(encoding="utf-8"))
    skipped: list[str] = []
    if args.source == "simple-wiki":
        entries, skipped = simple_wiki(picks["simple_wikipedia"])
    else:
        entries = []
        for book in picks["openstax"]:
            dest = args.checkouts / book["repo"].split("/")[1]
            commit = checkout(book["repo"], dest)
            found = openstax_texts(dest, book["repo"], book["collection"], commit, book["texts"])
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
