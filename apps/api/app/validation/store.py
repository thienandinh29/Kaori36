"""Labels and reviewers in the database (specs/validation/step-v1.md).

The tier and independence key of every label are set here from its role (app.validation.tiers),
never taken from the caller. A later label from the same source on the same aspect replaces the
earlier one.
"""

from datetime import datetime

import psycopg
from pydantic import BaseModel, ConfigDict, Field

from app.validation.tiers import (
    CONTENT_TYPES,
    EXPERT_ROLES,
    Effective,
    Label,
    effective,
    own_tier,
    source_of,
)


class LabelIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content_type: str
    content_id: str = Field(min_length=1)
    aspect: str = Field(min_length=1, max_length=40)
    value: str = Field(min_length=1, max_length=80)
    role: str
    name: str = ""  # the model id, source slug, dataset or code check
    reviewer_id: str | None = None
    note: str | None = Field(default=None, max_length=500)
    labelled_at: datetime | None = None


def add_reviewer(
    conn: psycopg.Connection, display_name: str, role: str, expertise: str, consented_at: datetime
) -> str:
    if role not in EXPERT_ROLES:
        raise ValueError(f"a reviewer's role is one of {sorted(EXPERT_ROLES)}")
    row = conn.execute(
        "insert into reviewers(display_name,role,expertise,consented_at) values (%s,%s,%s,%s) "
        "returning id::text",
        (display_name, role, expertise, consented_at),
    ).fetchone()
    assert row is not None
    return str(row[0])


def add_label(conn: psycopg.Connection, label: LabelIn) -> None:
    if label.content_type not in CONTENT_TYPES:
        raise ValueError(f"unknown content type: {label.content_type}")
    tier = own_tier(label.role)
    if label.role in EXPERT_ROLES:
        row = conn.execute(
            "select role from reviewers where id::text=%s", (label.reviewer_id,)
        ).fetchone()
        if row is None or row[0] != label.role:
            raise ValueError("the reviewer does not exist or has another role")
    elif label.reviewer_id is not None:
        raise ValueError("only an expert label names a reviewer")
    source, independence = source_of(label.role, name=label.name, reviewer_id=label.reviewer_id)
    conn.execute(
        "insert into labels(content_type,content_id,aspect,value,role,source,independence,tier,"
        "reviewer_id,note,labelled_at) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,coalesce(%s,now())) "
        "on conflict (content_type,content_id,aspect,source) do update set value=excluded.value,"
        "role=excluded.role,independence=excluded.independence,tier=excluded.tier,"
        "note=excluded.note,labelled_at=excluded.labelled_at",
        (
            label.content_type,
            label.content_id,
            label.aspect,
            label.value,
            label.role,
            source,
            independence,
            tier,
            label.reviewer_id,
            label.note,
            label.labelled_at,
        ),
    )


def labels_for(
    conn: psycopg.Connection, content_type: str, content_id: str, aspect: str
) -> list[Label]:
    rows = conn.execute(
        "select role,value,independence from labels "
        "where content_type=%s and content_id=%s and aspect=%s order by id",
        (content_type, content_id, aspect),
    ).fetchall()
    return [Label(role, value, independence) for role, value, independence in rows]


def effective_tier(
    conn: psycopg.Connection, content_type: str, content_id: str, aspect: str
) -> Effective:
    return effective(labels_for(conn, content_type, content_id, aspect))


def summary(conn: psycopg.Connection) -> dict[str, dict[str, int]]:
    """Content type/aspect -> effective tier (or 'disputed') -> number of items."""
    rows = conn.execute(
        "select content_type,aspect,content_id,role,value,independence from labels "
        "order by content_type,aspect,content_id,id"
    ).fetchall()
    groups: dict[tuple[str, str, str], list[Label]] = {}
    for ctype, aspect, cid, role, value, independence in rows:
        groups.setdefault((ctype, aspect, cid), []).append(Label(role, value, independence))
    out: dict[str, dict[str, int]] = {}
    for (ctype, aspect, _), labels in groups.items():
        result = effective(labels)
        key = "disputed" if result.disputed else (result.tier or "none")
        bucket = out.setdefault(f"{ctype}/{aspect}", {})
        bucket[key] = bucket.get(key, 0) + 1
    return out
