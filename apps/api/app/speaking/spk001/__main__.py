"""`python -m app.speaking.spk001 check|extract MANIFEST` (specs/speaking/step-5.6.md)."""

import argparse
import sys
from pathlib import Path

from app.config import REPO_ROOT, get_settings
from app.speaking.spk001 import extract, manifest

PRIVATE = REPO_ROOT / "data" / "private"
DEFAULT_OUT = PRIVATE / "spk-001" / "features.jsonl"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m app.speaking.spk001", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="validate a manifest and print its counts")
    c.add_argument("manifest", type=Path)
    e = sub.add_parser("extract", help="make one feature row per recording (resumable)")
    e.add_argument("manifest", type=Path)
    e.add_argument("--out", type=Path, default=DEFAULT_OUT)
    e.add_argument("--asr-url", default="", help="the recognition service (default: ASR_URL)")
    e.add_argument("--no-language", action="store_true", help="skip grammar and vocabulary checks")
    args = p.parse_args(argv)
    try:
        items = manifest.load(args.manifest)
        if args.cmd == "check":
            by = {s: sum(1 for i in items if i.split == s) for s in manifest.SPLITS}
            print(
                f"{len(items)} recordings; splits {by}; speakers {len({i.speaker for i in items})}"
            )
            return 0
        manifest.guard(items, args.out, PRIVATE)
    except manifest.ManifestError as exc:
        print(f"manifest: {exc}", file=sys.stderr)
        return 2

    import spacy

    from app.speaking.language import build_step
    from app.speaking.transcribe import Unavailable, service_transcribe

    settings = get_settings()
    url = args.asr_url or settings.asr_url
    needs_asr = any(i.words is None for i in items)
    if needs_asr and not url:
        print("some recordings have no transcript: set ASR_URL or --asr-url", file=sys.stderr)
        return 2
    transcribe = service_transcribe(url) if url else None
    if args.no_language:
        nlp, language = spacy.load("en_core_web_sm"), None
    else:
        from app.services.writing import load_grammar_step

        grammar = load_grammar_step(
            settings.writing_dir, settings.courses_dir, settings.languagetool_url
        )
        nlp, language = grammar.nlp, build_step(settings, grammar)
    try:
        counts = extract.run(items, args.out, transcribe, nlp, language, log=print)
    except Unavailable as exc:
        print(f"recognition service unavailable: {exc}. Run again to resume.", file=sys.stderr)
        return 3
    print(f"{counts} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
