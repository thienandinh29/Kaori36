"""Generated Reading questions as committed files (specs/listening-reading/step-4.2d.md).

    uv run python -m app.reading.itemfile export [--out DIR]
    uv run python -m app.reading.itemfile import [DIR]

Generation runs where model calls are possible, review runs on the owner's laptop, and a sandbox's
database is thrown away; so questions travel as one YAML file per text. Import only adds missing
rows: a row that exists (perhaps already reviewed) is never overwritten.
"""

import argparse
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg
import yaml  # type: ignore[import-untyped]
from psycopg.types.json import Jsonb

from app.reading.pipeline import sha256

REPO = Path(__file__).resolve().parents[4]
DEFAULT_DIR = REPO / "data" / "english" / "reading-items"
COLUMNS = (
    "id", "kind", "status", "item", "problems", "checker_answer", "checker_model",
    "generated_at", "checked_at", "reviewed_at", "review_note", "review_was",
)  # fmt: skip
_TIMES = ("generated_at", "checked_at", "reviewed_at")
_MARKS = ", ".join(["%s"] * len(COLUMNS))


def export(conn: psycopg.Connection[Any], texts: Mapping[str, tuple[str, str]], out: Path) -> int:
    """Write every stored item of the texts (slug -> (source, passage)); returns the count."""
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for slug, (source, _passage) in sorted(texts.items()):
        rows = conn.execute(
            f"select passage_sha256, {', '.join(COLUMNS)} from reading_items "
            "where text_slug=%s order by passage_sha256, id",
            (slug,),
        ).fetchall()
        if not rows:
            continue
        by_digest: dict[str, list[dict[str, Any]]] = {}
        for digest, *values in rows:
            row = dict(zip(COLUMNS, values, strict=True))
            for t in _TIMES:
                if row[t] is not None:
                    row[t] = row[t].isoformat()
            by_digest.setdefault(digest, []).append(row)
        doc = {
            "text_slug": slug,
            "source": source,
            "versions": [{"passage_sha256": d, "items": items} for d, items in by_digest.items()],
        }
        (out / f"{slug}.yaml").write_text(
            yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=110), encoding="utf-8"
        )
        n += len(rows)
    return n


def import_(
    conn: psycopg.Connection[Any], folder: Path, passages: Mapping[str, str]
) -> dict[str, int]:
    """Add missing rows; never overwrite. `passages` (slug -> current text) finds stale versions."""
    counts = {"added": 0, "kept": 0, "stale": 0}
    for path in sorted(folder.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        slug = str(doc["text_slug"])
        current = passages.get(slug)
        for version in doc["versions"]:
            digest = str(version["passage_sha256"])
            stale = current is None or sha256(current) != digest
            for row in version["items"]:
                values = [row.get(c) for c in COLUMNS]
                for i, c in enumerate(COLUMNS):
                    if c in _TIMES and values[i] is not None:
                        values[i] = datetime.fromisoformat(str(values[i]))
                    elif c in ("item", "problems"):
                        values[i] = Jsonb(values[i] if values[i] is not None else [])
                cur = conn.execute(
                    f"insert into reading_items(text_slug, passage_sha256, {', '.join(COLUMNS)}) "
                    f"values (%s, %s, {_MARKS}) on conflict (id) do nothing",
                    (slug, digest, *values),
                )
                added = cur.rowcount == 1
                counts["added" if added else "kept"] += 1
                counts["stale"] += int(added and stale)
    return counts


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - database
    from app.config import get_settings
    from app.sources.candidates import load_candidates
    from app.texts.bank import DEFAULT_CANDIDATES, load_bank
    from app.texts.bank import DEFAULT_DIR as TEXTS
    from app.validation.cli import backfill

    parser = argparse.ArgumentParser(prog="python -m app.reading.itemfile")
    sub = parser.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("export")
    ex.add_argument("--out", type=Path, default=DEFAULT_DIR)
    im = sub.add_parser("import")
    im.add_argument("folder", type=Path, nargs="?", default=DEFAULT_DIR)
    args = parser.parse_args(argv)
    bank = load_bank(TEXTS, load_candidates(DEFAULT_CANDIDATES))
    with psycopg.connect(get_settings().database_url) as conn:
        if args.cmd == "export":
            texts = {t.entry.slug: (t.entry.source, t.text) for t in bank.texts}
            print(f"exported {export(conn, texts, args.out)} items to {args.out}")
        else:
            counts = import_(conn, args.folder, {t.entry.slug: t.text for t in bank.texts})
            print(f"imported: {counts}")
            print(f"labels: {backfill(conn)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
