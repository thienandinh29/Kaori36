"""Testers, their invite links and sessions (specs/speaking/step-5.5.md).

An invite is a random 256-bit token shown once; only its SHA-256 is stored. It works once and for a
limited time. Redeeming it creates a session token, also stored only as a hash, which the web keeps
in an HttpOnly cookie. A tester's identity is that session, not the learner id.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import psycopg

INVITE_DAYS = 7
SESSION_DAYS = 30
RESEARCH_NOTICE = (
    "research-v1"  # the optional notice for the report's numbers; wording: the owner's
)


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_tester(conn: psycopg.Connection[Any], label: str) -> tuple[UUID, UUID]:
    """A learner for the tester and the tester's row: (tester id, learner id)."""
    label = label.strip()
    if not 1 <= len(label) <= 60:
        raise ValueError("the label is 1 to 60 characters")
    learner = conn.execute(
        "insert into learners(display_name) values (%s) returning id", (label,)
    ).fetchone()
    assert learner is not None
    tester = conn.execute(
        "insert into testers(learner_id,label) values (%s,%s) returning id", (learner[0], label)
    ).fetchone()
    assert tester is not None
    return tester[0], learner[0]


def invite(
    conn: psycopg.Connection[Any], tester_id: UUID, now: datetime, days: int = INVITE_DAYS
) -> str:
    """A new one-time invite for the tester; the token is returned once and never stored."""
    row = conn.execute("select revoked_at from testers where id=%s", (tester_id,)).fetchone()
    if row is None:
        raise ValueError("no such tester")
    if row[0] is not None:
        raise ValueError("this tester is switched off")
    token = new_token()
    conn.execute(
        "insert into tester_invites(token_hash,tester_id,created_at,expires_at) "
        "values (%s,%s,%s,%s)",
        (hash_token(token), tester_id, now, now + timedelta(days=days)),
    )
    return token


def redeem(
    conn: psycopg.Connection[Any], token: str, now: datetime, days: int = SESSION_DAYS
) -> tuple[UUID, str, str] | None:
    """Use an invite once: (learner id, session token, label), or None when the link cannot be
    used (unknown, used, expired, or the tester is switched off)."""
    row = conn.execute(
        "update tester_invites i set used_at=%s from testers t "
        "where i.token_hash=%s and i.tester_id=t.id and i.used_at is null and i.expires_at > %s "
        "and t.revoked_at is null returning t.id, t.learner_id, t.label",
        (now, hash_token(token), now),
    ).fetchone()
    if row is None:
        return None
    session = new_token()
    conn.execute(
        "insert into tester_sessions(token_hash,tester_id,created_at,expires_at,last_seen) "
        "values (%s,%s,%s,%s,%s)",
        (hash_token(session), row[0], now, now + timedelta(days=days), now),
    )
    return row[1], session, row[2]


def session_learner(conn: psycopg.Connection[Any], token: str | None, now: datetime) -> UUID | None:
    """The learner of a valid session (not expired, tester not switched off), or None."""
    if not token:
        return None
    row = conn.execute(
        "update tester_sessions s set last_seen=%s from testers t "
        "where s.token_hash=%s and s.tester_id=t.id and s.expires_at > %s "
        "and t.revoked_at is null returning t.learner_id",
        (now, hash_token(token), now),
    ).fetchone()
    return None if row is None else row[0]


def is_tester(conn: psycopg.Connection[Any], learner: UUID) -> bool:
    return (
        conn.execute("select 1 from testers where learner_id=%s", (learner,)).fetchone() is not None
    )


def revoke(conn: psycopg.Connection[Any], tester_id: UUID, now: datetime) -> bool:
    """Switch a tester off at once: their sessions end and their invites stop working."""
    row = conn.execute(
        "update testers set revoked_at=coalesce(revoked_at,%s) where id=%s returning id",
        (now, tester_id),
    ).fetchone()
    conn.execute("delete from tester_sessions where tester_id=%s", (tester_id,))
    return row is not None


def research_consent(
    conn: psycopg.Connection[Any], learner: UUID, version: str, now: datetime
) -> None:
    if version != RESEARCH_NOTICE:
        raise ValueError("unknown notice")
    conn.execute(
        "update testers set research_consent=%s,research_consent_at=%s where learner_id=%s",
        (version, now, learner),
    )


def info(conn: psycopg.Connection[Any], learner: UUID) -> dict[str, Any] | None:
    row = conn.execute(
        "select id,label,research_consent from testers where learner_id=%s", (learner,)
    ).fetchone()
    if row is None:
        return None
    return {"id": row[0], "label": row[1], "research_consented": row[2] == RESEARCH_NOTICE}
