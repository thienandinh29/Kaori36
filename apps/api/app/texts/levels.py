"""How well do the measured features track the owner's CEFR labels? (plan.md, CP1)

    uv run python -m app.texts.levels sheet [folder] --out sheet.csv   # `level` left empty
    uv run python -m app.texts.levels score sheet.csv [--out report.json]

The owner fills `level` (A1-C1) by reading each text. `score` reports, per feature, the
Spearman rank correlation with those labels and how many texts it rests on. It measures
agreement only: no level is ever assigned from the features. The "unknown share" feature uses
the NGSL/NAWL form index (`data-sa/vocabulary/forms.yaml`, CC BY-SA 4.0): the share of words not
among the forms of A1-B1 headwords.
"""

import argparse
import csv
import json
import math
from collections.abc import Collection, Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from app.texts.bank import REPO, TextEntry
from app.texts.features import features

LEVELS = ("A1", "A2", "B1", "B2", "C1")
FEATURES = ("words", "mean_sentence_words", "long_word_share", "type_token_ratio", "unknown_share")
FORMS = REPO / "data-sa" / "vocabulary" / "forms.yaml"


def known_up_to(forms: Mapping[str, Sequence[str]], level: str = "B1") -> set[str]:
    """Every form of every headword at `level` or below."""
    top = LEVELS.index(level)
    out: set[str] = set()
    for head, (lv, *rest) in forms.items():
        if LEVELS.index(lv) <= top:
            out |= {str(head).lower(), *(str(f).lower() for f in rest)}
    return out


def ranks(values: Sequence[float]) -> list[float]:
    """1-based ranks, ties sharing their mean rank."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            out[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return out


def spearman(x: Sequence[float], y: Sequence[float]) -> float | None:
    """Pearson correlation of the ranks; None when either side has no spread or n < 3."""
    if len(x) != len(y) or len(x) < 3:
        return None
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry, strict=True))
    sx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    sy = math.sqrt(sum((b - my) ** 2 for b in ry))
    return round(sxy / (sx * sy), 3) if sx and sy else None


def sheet_rows(entries: Sequence[TextEntry], known: Collection[str]) -> list[dict[str, Any]]:
    rows = []
    for e in entries:
        f = features(e.text, known).to_json()
        rows.append({"slug": e.slug, "title": e.title, "source": e.source,
                     **{k: f[k] for k in FEATURES}, "level": ""})  # fmt: skip
    return rows


def score(rows: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    labelled = [r for r in rows if r.get("level", "").strip().upper() in LEVELS]
    y = [float(LEVELS.index(r["level"].strip().upper())) for r in labelled]
    out: dict[str, Any] = {"labelled": len(labelled), "unlabelled": len(rows) - len(labelled)}
    out["levels"] = {
        lv: sum(1 for r in labelled if r["level"].strip().upper() == lv) for lv in LEVELS
    }
    out["spearman"] = {}
    for name in FEATURES:
        pairs = [
            (float(r[name]), v)
            for r, v in zip(labelled, y, strict=True)
            if r.get(name) not in ("", "None", None)
        ]
        out["spearman"][name] = {
            "rho": spearman([p[0] for p in pairs], [p[1] for p in pairs]),
            "n": len(pairs),
        }
    out["note"] = (
        "Agreement of each feature with the owner's labels, nothing more. With n = 30, a rho "
        "of about 0.36 is the smallest that differs from zero at the 5% level (two-sided); "
        "the labels are one person's judgement."
    )
    return out


def load_entries(folder: Path) -> list[TextEntry]:
    return [
        TextEntry.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))
        for p in sorted(folder.glob("*.yaml"))
    ]


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - files
    parser = argparse.ArgumentParser(prog="python -m app.texts.levels")
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sheet")
    s.add_argument(
        "folder", type=Path, nargs="?", default=REPO / "data" / "private" / "english-texts"
    )
    s.add_argument("--out", type=Path, required=True)
    c = sub.add_parser("score")
    c.add_argument("sheet", type=Path)
    c.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if args.cmd == "sheet":
        forms = yaml.load(
            FORMS.read_text(encoding="utf-8"), Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader)
        )
        rows = sheet_rows(load_entries(args.folder), known_up_to(forms))
        with args.out.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["slug"])
            w.writeheader()
            w.writerows(rows)
        print(f"{len(rows)} texts -> {args.out}; fill the `level` column (A1-C1), then run `score`")
        return 0
    with args.sheet.open(encoding="utf-8") as f:
        report = score(list(csv.DictReader(f)))
    text = json.dumps(report, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
