"""Validation labels CLI (specs/validation/step-v1.md).

    uv run python -m app.validation.cli backfill      # existing decisions -> labels (safe to rerun)
    uv run python -m app.validation.cli summary       # items per content type and effective tier
    uv run python -m app.validation.cli add-reviewer --name "Cô Lan" --role expert_teacher \
        --expertise "10 năm dạy IELTS" --consented
    uv run python -m app.validation.cli issue-token --reviewer <id>     # the private link, once
    uv run python -m app.validation.cli make-batch --content reading_item --name "Đọc đợt 1"
"""

import argparse
import json
from datetime import UTC, datetime

import psycopg

from app.services.backend import learner_uuid
from app.services.reading_review import load_passages
from app.services.review_portal import (
    QUEUES,
    create_batch,
    grammar_items,
    issue_token,
    reading_strata,
    revoke_tokens,
    speech_targets,
    vocab_id,
)
from app.validation.sampling import everything, random_sample, stratified
from app.validation.store import LabelIn, add_label, add_reviewer, summary
from app.vocabulary.wordlist import shared_wordlist

_VERDICT = {"verified": "right", "needs_review": "wrong"}


def backfill(conn: psycopg.Connection) -> dict[str, int]:
    """Copy the owner's sound labels and every Reading item's checks into `labels`."""
    counts = {"speech_target": 0, "reading_code_check": 0, "reading_model": 0, "reading_owner": 0}
    for rec, target, value, at in conn.execute(
        "select recording_id::text,target,label,labelled_at from speech_labels"
    ).fetchall():
        add_label(
            conn,
            LabelIn(
                content_type="speech_target",
                content_id=f"{rec}:{target}",
                aspect="phone_ok",
                value=value,
                role="owner_developer",
                labelled_at=at,
            ),
        )
        counts["speech_target"] += 1
    rows = conn.execute(
        "select id,status,review_was,checker_model,checked_at,reviewed_at,review_note "
        "from reading_items where status <> 'generated'"
    ).fetchall()
    for item_id, status, was, model, checked_at, reviewed_at, note in rows:
        base = {"content_type": "reading_item", "content_id": item_id, "aspect": "item_ok"}
        add_label(
            conn,
            LabelIn(
                **base,
                value="wrong" if status == "dropped" else "right",
                role="code_check",
                name="reading",
                labelled_at=checked_at,
            ),
        )
        counts["reading_code_check"] += 1
        before = was if status in ("approved", "rejected") else status
        if model and before in _VERDICT:
            add_label(
                conn,
                LabelIn(
                    **base, value=_VERDICT[before], role="model", name=model, labelled_at=checked_at
                ),
            )
            counts["reading_model"] += 1
        if status in ("approved", "rejected"):
            add_label(
                conn,
                LabelIn(
                    **base,
                    value="right" if status == "approved" else "wrong",
                    role="owner_developer",
                    note=note,
                    labelled_at=reviewed_at,
                ),
            )
            counts["reading_owner"] += 1
    return counts


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - database
    from app.config import get_settings

    parser = argparse.ArgumentParser(prog="python -m app.validation.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("backfill")
    sub.add_parser("summary")
    rev = sub.add_parser("add-reviewer")
    rev.add_argument("--name", required=True)
    rev.add_argument("--role", required=True)
    rev.add_argument("--expertise", default="")
    rev.add_argument("--consented", action="store_true", help="they agreed to how labels are used")
    tok = sub.add_parser("issue-token", help="print a reviewer's private link once")
    tok.add_argument("--reviewer", required=True)
    tok.add_argument("--base-url", default="http://localhost:3000")
    sub.add_parser("revoke-token").add_argument("--reviewer", required=True)
    bat = sub.add_parser("make-batch", help="a fixed stratified sample for reviewers")
    bat.add_argument("--content", required=True, choices=sorted(QUEUES))
    bat.add_argument("--name", required=True)
    bat.add_argument("--size", type=int, default=50)
    bat.add_argument("--seed", type=int, default=1)
    bat.add_argument(
        "--role", help="speech_target only: expert_teacher instead of phonetics_expert"
    )
    bat.add_argument(
        "--learner", help="speech_target only: the owner whose kept recordings to send"
    )
    args = parser.parse_args(argv)
    with psycopg.connect(get_settings().database_url) as conn:
        if args.cmd == "backfill":
            out: object = backfill(conn)
        elif args.cmd == "summary":
            out = summary(conn)
        elif args.cmd == "issue-token":
            token = issue_token(conn, args.reviewer)
            out = {
                "link": f"{args.base_url.rstrip('/')}/kiem-duyet#{token}",
                "note": "Shown once; send it privately. Revoke with revoke-token.",
            }
        elif args.cmd == "revoke-token":
            out = {"revoked": revoke_tokens(conn, args.reviewer)}
        elif args.cmd == "make-batch":
            settings = get_settings()
            if args.content == "reading_item":
                disagreed, agreed = reading_strata(conn)
                sample = stratified(disagreed, agreed, args.size, args.seed)
            elif args.content == "text_level":
                texts = load_passages(settings.reading_texts_dir)
                sample = everything(list(texts), args.seed)
            elif args.content == "grammar_item":
                ids = list(grammar_items(settings.items_dir / "english-ielts.yaml"))
                sample = random_sample(ids, args.size, args.seed)
            elif args.content == "vocab_entry":
                words = shared_wordlist(
                    settings.vocab_dir / "core-seed.yaml", settings.vocab_imported_dir
                ).words
                sample = random_sample([vocab_id(w) for w in words], args.size, args.seed)
            else:
                if not args.learner:
                    parser.error("speech_target needs --learner (an owner's id)")
                owners = {
                    str(learner_uuid(x.strip()))
                    for x in settings.draft_item_learners.split(",")
                    if x.strip()
                }
                learner = str(learner_uuid(args.learner))
                try:
                    sample = everything(speech_targets(conn, learner, owners), args.seed)
                except ValueError as err:
                    parser.error(str(err))
            if not sample.item_ids:
                parser.error("nothing to sample yet")
            try:
                bid = create_batch(conn, args.name, args.content, sample, args.seed, args.role)
            except ValueError as err:
                parser.error(str(err))
            out = {"batch_id": bid, "items": len(sample.item_ids), "population": sample.population}
        else:
            if not args.consented:
                parser.error("a reviewer is added only after they consent (--consented)")
            out = {
                "reviewer_id": add_reviewer(
                    conn, args.name, args.role, args.expertise, datetime.now(UTC)
                )
            }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
