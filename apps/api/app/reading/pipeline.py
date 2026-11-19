"""Generate, check and store Reading questions, offline (specs/listening-reading/step-4.2b.md).

    uv run python -m app.reading.pipeline [folder] [--only SLUG] [--max-checks 40]
        [--max-cost 0.50] [--unverified]

Texts come from the bank (verified sources only); `--unverified` reads a private folder's raw
entries for development, and nothing from it may be committed. Each text is generated once per
passage version. Then up to `--max-checks` stored items are checked blind (the free checker allows
50 requests a day); the rest wait for the next run. Every model call is recorded in `llm_calls`
(`app/reading/calls.py`); no new text is generated once the run's recorded cost reaches
`--max-cost`.
"""

import argparse
import asyncio
import hashlib
import unicodedata
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb
from pydantic import TypeAdapter

from app.reading import blind
from app.reading.calls import CallLog
from app.reading.generate import SYSTEM, Generated, ReadingItem, build, prompt
from app.reading.items import Item
from app.writing.model_calls import Prices

Generate = Callable[[str, str], Awaitable[Generated | None]]  # (system, prompt) -> output
_ITEM: TypeAdapter[ReadingItem] = TypeAdapter(Item)


def sha256(passage: str) -> str:
    """The passage's fingerprint, the same wherever it is read: of its NFC form.

    The bank stores NFC text, so digests made before this normalisation stay valid; the review
    queue and the practice page hash a text file as read, and NFC makes them agree.
    """
    return hashlib.sha256(unicodedata.normalize("NFC", passage).encode()).hexdigest()


def generated_already(conn: psycopg.Connection[Any], slug: str, digest: str) -> bool:
    row = conn.execute(
        "select 1 from reading_items where text_slug=%s and passage_sha256=%s limit 1",
        (slug, digest),
    ).fetchone()
    return row is not None


def store(
    conn: psycopg.Connection[Any],
    slug: str,
    digest: str,
    kept: Sequence[ReadingItem],
    dropped: Sequence[tuple[str, str, list[str]]],
    now: datetime,
) -> None:
    for item in kept:
        conn.execute(
            "insert into reading_items(id,text_slug,passage_sha256,kind,item,status,generated_at) "
            "values (%s,%s,%s,%s,%s,'generated',%s) on conflict (id) do nothing",
            (item.id, slug, digest, item.kind, Jsonb(item.model_dump(mode="json")), now),
        )
    for item_id, kind, problems in dropped:
        conn.execute(
            "insert into reading_items(id,text_slug,passage_sha256,kind,item,status,problems,"
            "generated_at) values (%s,%s,%s,%s,'{}'::jsonb,'dropped',%s,%s) "
            "on conflict (id) do nothing",
            (item_id, slug, digest, kind, Jsonb(problems), now),
        )


async def generate_text(
    conn: psycopg.Connection[Any], slug: str, passage: str, gen: Generate, now: datetime
) -> tuple[int, int] | None:
    """(kept, dropped) for a new passage version; None if already generated or no output."""
    digest = sha256(passage)
    if generated_already(conn, slug, digest):
        return None
    out = await gen(SYSTEM, prompt(passage))
    if out is None:
        return None
    kept, dropped = build(slug, passage, out)
    store(conn, slug, digest, kept, dropped, now)
    return len(kept), len(dropped)


async def check_pending(
    conn: psycopg.Connection[Any],
    passages: dict[str, str],
    ask: blind.Ask,
    limit: int,
    model: Callable[[], str | None],
    now: datetime,
) -> dict[str, int]:
    """Blind-check up to `limit` stored items whose passage is still the current one."""
    counts = {"verified": 0, "needs_review": 0}
    rows = conn.execute(
        "select id,text_slug,passage_sha256,item from reading_items where status='generated' "
        "order by generated_at, id"
    ).fetchall()
    for item_id, slug, digest, data in rows:
        if sum(counts.values()) >= limit:
            break
        passage = passages.get(slug)
        if passage is None or sha256(passage) != digest:
            continue  # text gone or edited: its items wait (a new version is generated afresh)
        outcome, answer = await blind.check(_ITEM.validate_python(data), passage, ask)
        conn.execute(
            "update reading_items set status=%s, checker_answer=%s, checker_model=%s, "
            "checked_at=%s where id=%s",
            # No usable reply: no checker judged it, so none is named (the label backfill would
            # otherwise record the last model that answered as doubting this item).
            (outcome, answer, model() if answer is not None else None, now, item_id),
        )
        conn.commit()  # each check is paid for: keep it even if a later one fails
        counts[outcome] += 1
    return counts


def gateway_generate(observe: Callable[[Any], None]) -> Generate:  # pragma: no cover - model
    from app.llm.gateway import Gateway, GenerationLimits, complete_with_metadata, gateway_scope
    from app.llm.providers import default_gateway

    base = default_gateway()
    gateway = Gateway(
        base.routing, base.adapters, request_timeout=180, total_timeout=400,
        task_limits={"reading_items": GenerationLimits(8192, 0)}, observe_attempt=observe,
    )  # fmt: skip

    async def gen(system: str, text: str) -> Generated | None:
        try:
            with gateway_scope(gateway):
                out = await complete_with_metadata(
                    "reading_items", "free", system, [{"role": "user", "content": text}], Generated
                )
        except Exception as exc:
            print(f"generation failed: {type(exc).__name__}: {exc}")
            return None
        return out.value if isinstance(out.value, Generated) else None

    return gen


def gateway_ask(
    observe: Callable[[Any], None],
) -> tuple[blind.Ask, Callable[[], str | None]]:  # pragma: no cover - model
    from app.llm.gateway import (
        Gateway,
        GatewayError,
        complete_with_metadata,
        gateway_scope,
        verification_scope,
    )
    from app.llm.providers import default_gateway

    base = default_gateway()
    gateway = Gateway(base.routing, base.adapters, observe_attempt=observe)

    last: list[str] = []

    async def ask(system: str, text: str) -> blind.Reply | None:
        try:
            # The generator's family is never the checker.
            with gateway_scope(gateway), verification_scope("deepseek"):
                out = await complete_with_metadata(
                    "reading_check",
                    "free",
                    system,
                    [{"role": "user", "content": text}],
                    blind.Reply,
                )
        except GatewayError:
            return None
        last.append(out.route.model)
        return out.value if isinstance(out.value, blind.Reply) else None

    return ask, lambda: last[-1] if last else None


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - database and models
    from app.config import get_settings
    from app.sources.candidates import load_candidates
    from app.texts.bank import DEFAULT_CANDIDATES, DEFAULT_DIR, load_bank
    from app.texts.levels import load_entries

    parser = argparse.ArgumentParser(prog="python -m app.reading.pipeline")
    parser.add_argument("folder", type=Path, nargs="?", default=DEFAULT_DIR)
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--max-checks", type=int, default=40)
    parser.add_argument("--unverified", action="store_true", help="development: a private folder")
    parser.add_argument("--no-generate", action="store_true", help="only check stored items")
    parser.add_argument("--max-cost", type=float, default=0.50, help="US$ for this run")
    args = parser.parse_args(argv)
    if args.unverified:
        passages = {e.slug: e.text for e in load_entries(args.folder)}
    else:
        bank = load_bank(args.folder, load_candidates(DEFAULT_CANDIDATES))
        for r in bank.refused:
            print(f"refused {r.where}: {r.reason}")
        passages = {t.entry.slug: t.text for t in bank.texts}
    if args.only:
        passages = {k: v for k, v in passages.items() if k in args.only}
    now = datetime.now(UTC)
    settings = get_settings()
    log = CallLog(Prices(settings.llm_price_input_per_mtok, settings.llm_price_output_per_mtok))
    ask, model = gateway_ask(log.observe)
    with psycopg.connect(settings.database_url) as conn:
        if not args.no_generate:
            gen = gateway_generate(log.observe)
            for slug, passage in passages.items():
                if log.cost_usd >= args.max_cost:
                    print(f"cost cap US${args.max_cost:.2f} reached: {slug} and later texts wait")
                    break
                done = asyncio.run(generate_text(conn, slug, passage, gen, now))
                log.flush(conn, now)
                conn.commit()
                if done is not None:
                    print(f"{slug}: kept {done[0]}, dropped {done[1]}")
        try:
            counts = asyncio.run(check_pending(conn, passages, ask, args.max_checks, model, now))
        finally:
            log.flush(conn, now)
            conn.commit()
    print(f"checked: {counts}")
    print(log.summary())
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
