"""Explain the bank's Reading questions, offline (CP4b on the bank's own questions, step 1).

    uv run python -m app.reading.explain_run [folder] [--max-cost 0.10] [--include-verified N]
        [--only ITEM_ID]

One DeepSeek call per question (gateway task `reading_explain`), kept only when code's checks pass
(`app/reading/explain.py`). Approved questions first; `--include-verified N` also explains up to N
verified (not yet approved) questions, to build the planted test of the next step: nothing here is
shown to a learner. A question is explained once per version of its passage and of itself. Every
call is recorded in `llm_calls`; no new call starts once the run's recorded cost reaches
`--max-cost`.
"""

import argparse
import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb
from pydantic import TypeAdapter

from app.reading.calls import CallLog
from app.reading.explain import (
    EXPLAINED_KINDS,
    SYSTEM,
    ExplainedItem,
    ExplainOut,
    check,
    fingerprint,
    prompt,
)
from app.reading.items import Item
from app.reading.pipeline import sha256

Explain = Callable[[str, str], Awaitable[ExplainOut | None]]  # (system, prompt) -> output
_ITEM: TypeAdapter[Any] = TypeAdapter(Item)


def pending(
    conn: psycopg.Connection[Any],
    passages: dict[str, str],
    include_verified: int = 0,
    only: frozenset[str] = frozenset(),
) -> list[tuple[str, str, ExplainedItem]]:
    """(item id, passage, item) to explain: approved first, then up to N verified; never twice for
    the same passage and question versions; headings are not explained yet."""
    rows = conn.execute(
        "select i.id, i.text_slug, i.passage_sha256, i.item, i.status from reading_items i "
        "where i.kind = any(%s) and i.status in ('approved','verified') "
        "order by (i.status = 'approved') desc, i.generated_at, i.id",
        (list(EXPLAINED_KINDS),),
    ).fetchall()
    done = {
        (r[0], r[1], r[2])
        for r in conn.execute(
            "select item_id, passage_sha256, item_sha256 from reading_explanations"
        ).fetchall()
    }
    out: list[tuple[str, str, ExplainedItem]] = []
    verified = 0
    for item_id, slug, digest, data, status in rows:
        if only and item_id not in only:
            continue
        passage = passages.get(slug)
        if passage is None or sha256(passage) != digest:
            continue  # text gone or edited: not served, so not explained
        item = _ITEM.validate_python(data)
        if (item_id, digest, fingerprint(item)) in done:
            continue
        if status == "verified":
            if verified >= include_verified:
                continue
            verified += 1
        out.append((item_id, passage, item))
    return out


async def explain_pending(
    conn: psycopg.Connection[Any],
    todo: list[tuple[str, str, ExplainedItem]],
    explain: Explain,
    model: Callable[[], str | None],
    log: CallLog,
    max_cost: float,
    now: datetime,
) -> dict[str, int]:
    counts = {"checked": 0, "dropped": 0, "no_reply": 0, "waiting": 0}
    for n, (item_id, passage, item) in enumerate(todo):
        if log.cost_usd >= max_cost:
            counts["waiting"] = len(todo) - n
            break
        out = await explain(SYSTEM, prompt(passage, item))
        log.flush(conn, now)
        if out is None:
            counts["no_reply"] += 1  # tried again on the next run
            conn.commit()
            continue
        kept, problems = check(out, passage, item)
        status = "checked" if kept else "dropped"
        body = kept.to_json() if kept else out.model_dump(mode="json")
        conn.execute(
            "insert into reading_explanations(item_id,passage_sha256,item_sha256,status,"
            "explanation,skills,problems,model,generated_at) values (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "on conflict do nothing",
            (item_id, sha256(passage), fingerprint(item), status, Jsonb(body),
             list(kept.skills) if kept else [], Jsonb(problems), model(), now),
        )  # fmt: skip
        conn.commit()  # each call is paid for: keep it even if a later one fails
        counts[status] += 1
    return counts


def gateway_explain(
    observe: Callable[[Any], None],
) -> tuple[Explain, Callable[[], str | None]]:  # pragma: no cover - model
    from app.llm.gateway import Gateway, complete_with_metadata, gateway_scope
    from app.llm.providers import default_gateway

    base = default_gateway()
    gateway = Gateway(base.routing, base.adapters, request_timeout=120, observe_attempt=observe)
    last: list[str] = []

    async def explain(system: str, text: str) -> ExplainOut | None:
        try:
            with gateway_scope(gateway):
                out = await complete_with_metadata(
                    "reading_explain", "free", system, [{"role": "user", "content": text}],
                    ExplainOut,
                )  # fmt: skip
        except Exception as exc:
            print(f"explanation failed: {type(exc).__name__}: {exc}")
            return None
        last.append(out.route.model)
        return out.value if isinstance(out.value, ExplainOut) else None

    return explain, lambda: last[-1] if last else None


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - database and models
    from app.config import get_settings
    from app.sources.candidates import load_candidates
    from app.texts.bank import DEFAULT_CANDIDATES, DEFAULT_DIR, load_bank
    from app.writing.model_calls import Prices

    parser = argparse.ArgumentParser(prog="python -m app.reading.explain_run")
    parser.add_argument("folder", type=Path, nargs="?", default=DEFAULT_DIR)
    parser.add_argument("--max-cost", type=float, default=0.10, help="US$ for this run")
    parser.add_argument("--include-verified", type=int, default=0, metavar="N")
    parser.add_argument("--only", action="append", default=[])
    args = parser.parse_args(argv)
    bank = load_bank(args.folder, load_candidates(DEFAULT_CANDIDATES))
    passages = {t.entry.slug: t.text for t in bank.texts}
    settings = get_settings()
    log = CallLog(Prices(settings.llm_price_input_per_mtok, settings.llm_price_output_per_mtok))
    explain, model = gateway_explain(log.observe)
    now = datetime.now(UTC)
    with psycopg.connect(settings.database_url) as conn:
        todo = pending(conn, passages, args.include_verified, frozenset(args.only))
        print(f"to explain: {len(todo)}")
        counts = asyncio.run(explain_pending(conn, todo, explain, model, log, args.max_cost, now))
    print(f"explained: {counts}")
    print(log.summary())
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
