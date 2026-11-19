"""Store Writing competency evidence (specs/two-layer-map/writing-evidence.md).

Competencies are concepts of the subject `ielts-competencies`, so their mastery uses the same table,
BKT and "Vì sao?" traces as every other node. Each observation is also logged with its essay; the
unique key makes a retried essay job count nothing twice.
"""

from collections.abc import Sequence
from datetime import datetime
from functools import cache
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
import yaml  # type: ignore[import-untyped]

from app.competencies.model import CompetencyMap, load_map
from app.engine import bkt
from app.engine.trace import fmt_p
from app.services.backend import save_trace
from app.services.learning import save_mastery
from app.texts.levels import FORMS, known_up_to
from app.writing.competency import Observation, Rules, load_rules

SUBJECT = "ielts-competencies"


@cache
def known_b1() -> frozenset[str]:
    forms = yaml.load(
        FORMS.read_text(encoding="utf-8"), Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    )
    return frozenset(known_up_to(forms))


@cache
def rules(writing_dir: Path) -> Rules:
    return load_rules(writing_dir / "competency-rules.yaml")


def competency_ids(
    conn: psycopg.Connection[Any], cmap: CompetencyMap
) -> tuple[UUID, dict[str, UUID]]:
    row = conn.execute(
        "insert into subjects(slug,name_vi,name_en) values (%s,%s,%s) "
        "on conflict (slug) do update set slug=excluded.slug returning id",
        (SUBJECT, "Kỹ năng thi IELTS", "IELTS competencies"),
    ).fetchone()
    assert row is not None
    subject = row[0]
    ids: dict[str, UUID] = {}
    for c in cmap.competencies:
        got = conn.execute(
            "insert into concepts(subject_id,slug,name_vi,name_en) values (%s,%s,%s,%s) "
            "on conflict (subject_id,slug) do update set name_vi=excluded.name_vi "
            "returning id",
            (subject, c.slug, c.name_vi, c.name_en),
        ).fetchone()
        assert got is not None
        ids[c.slug] = got[0]
    return subject, ids


def apply(
    conn: psycopg.Connection[Any],
    learner: UUID,
    essay_id: UUID,
    found: Sequence[Observation],
    params: bkt.BKTParams,
    now: datetime,
    cmap: CompetencyMap | None = None,
) -> list[dict[str, Any]]:
    """One BKT update per competency per essay; returns what moved (for the essay result).

    Rules about the same essay are not independent evidence, so they are not separate BKT
    observations: a competency passes for this essay when more than half of its rules pass. Every
    rule is still logged, with the competency's estimate before and after, so "Vì sao?" can say
    which checks passed. A retried essay job finds its rows already there and counts nothing.
    """
    cmap = cmap or load_map()
    subject, ids = competency_ids(conn, cmap)
    names = {c.slug: c.name_vi for c in cmap.competencies}
    rows = conn.execute(
        "select concept_id, p_known from mastery where learner_id=%s and concept_id = any(%s)",
        (learner, list(ids.values())),
    ).fetchall()
    p = {cid: float(v) for cid, v in rows}
    by_comp: dict[str, list[Observation]] = {}
    for o in found:
        by_comp.setdefault(o.competency, []).append(o)
    moved = []
    for competency, obs in by_comp.items():
        done = conn.execute(
            "select 1 from competency_observations where source='essay' and source_id=%s "
            "and competency=%s limit 1",
            (essay_id, competency),
        ).fetchone()
        if done is not None:
            continue  # this essay already counted for this competency
        cid = ids[competency]
        before = p.get(cid, params.p_init)
        passed_n = sum(o.passed for o in obs)
        passed = passed_n * 2 > len(obs)
        after, trace = bkt.update_traced(
            before, passed, params, concept_slug=competency, now=now,
            item_id=f"essay:{essay_id}:{competency}",
        )  # fmt: skip
        checks = "; ".join(f"{o.explain_vi} ({'đạt' if o.passed else 'chưa'})" for o in obs)
        trace = trace.model_copy(
            update={
                "rule": "writing.competency",
                "rule_vi": (
                    f"{names[competency]}: {passed_n}/{len(obs)} kiểm tra đạt ({checks}) → bài này "
                    f"{'đạt' if passed else 'chưa đạt'}; ước lượng từ {fmt_p(before)} thành "
                    f"{fmt_p(after)}. Đây là kiểm tra tự động (bản nháp), không phải band điểm."
                ),
            }
        )
        for o in obs:
            conn.execute(
                "insert into competency_observations(learner_id,competency,source,source_id,"
                "rule,passed,value,p_before,p_after,observed_at) "
                "values (%s,%s,'essay',%s,%s,%s,%s,%s,%s,%s)",
                (learner, competency, essay_id, o.rule, o.passed, o.value, before, after, now),
            )
        save_mastery(conn, learner, cid, after)
        save_trace(conn, learner, subject, trace)
        p[cid] = after
        moved.append(
            {
                "competency": competency,
                "passed": passed,
                "checks": [{"rule": o.rule, "passed": o.passed, "value": o.value} for o in obs],
                "p_before": round(before, 4),
                "p_after": round(after, 4),
            }
        )
    return moved
