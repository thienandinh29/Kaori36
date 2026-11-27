"""Today's list (specs/two-layer-map/spec.md, M3): reads the learner's state and asks the engine.

Read-only. Foundations: grammar nodes (a milestone counts as its weakest hidden node),
pronunciation sound groups, and vocabulary bands derived from FSRS cards. Competencies: Writing ones
from essay checks (app.services.competency_evidence; measured after 3 essays), the rest not yet
(Reading arrives with CP4), so the engine asks for a diagnostic of a skill it can practise and
otherwise works from shared foundations. Every activity carries a link and the engine's
DecisionTrace.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

import yaml  # type: ignore[import-untyped]
from psycopg.types.json import Jsonb

from app.competencies.bands import band_of, bands
from app.competencies.check import PROPOSED_PATH, load_foundations
from app.competencies.model import VOCAB_BANDS, CompetencyMap, load_map
from app.curriculum.course import load_course
from app.engine.graph import UNSEEN_P_KNOWN
from app.engine.recommend import (
    KNOWN,
    MIN_EVIDENCE,
    ROOT_CAUSE_BELOW,
    Activity,
    Estimate,
    recommend,
)
from app.services.competency_evidence import SUBJECT as COMPETENCY_SUBJECT
from app.services.grammar import GrammarService
from app.services.today_plan import (
    Target,
    TodayEvidence,
    estimate_minutes,
    is_done,
    local_day,
    study_week,
    week_bounds,
)
from app.services.vocabulary import start_of_day

if TYPE_CHECKING:
    from app.services.listening_practice import ListeningPractice
    from app.services.reading_practice import ReadingPractice

GRAMMAR = "english-ielts"
PRONUNCIATION = "english-pronunciation"
PHRASES = "my-phrases"
# Writing always; Reading while a question is served (CP4); Listening while the server voice is
# on (CP5, step 4.4b); Speaking in phase 5.
AVAILABLE_SKILLS = frozenset({"writing"})
BAND_NAMES_VI = {
    "vocab-a1": "Từ vựng A1",
    "vocab-a2": "Từ vựng A2",
    "vocab-b1": "Từ vựng B1",
    "vocab-b2": "Từ vựng B2",
    "vocab-c1": "Từ vựng C1",
    "vocab-nawl": "Từ vựng học thuật (NAWL)",
}
# Where a saved answer counts towards a study day (step M5): (table, timestamp column).
STUDY_TABLES = (
    ("vocab_reviews", "answered_at"),
    ("grammar_answers", "answered_at"),
    ("reading_answers", "answered_at"),
    ("reading_own_answers", "answered_at"),
    ("listening_answers", "answered_at"),
    ("essays", "submitted_at"),
    ("speech_recordings", "created_at"),
    ("say_attempts", "said_at"),
)
REVIEW_NAMES_VI = {"vocab": "Từ vựng", "phrases": "Cụm từ đã lưu"}


class TodayService:
    def __init__(
        self,
        grammar: GrammarService,
        cmap: CompetencyMap | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        reading: "ReadingPractice | None" = None,
        listening: "ListeningPractice | None" = None,
    ) -> None:
        self.grammar = grammar
        self.reading = reading
        self.listening = listening
        self._available: set[str] = set(AVAILABLE_SKILLS)
        self.cmap = cmap or load_map()
        self.live = load_foundations().live
        self.clock = clock
        # No items file for pronunciation, so not a grammar bundle: its course only.
        self.pronunciation = load_course(grammar.courses_dir / f"{PRONUNCIATION}.yaml")

    def _names(self) -> dict[str, str]:
        names = dict(BAND_NAMES_VI) | dict(REVIEW_NAMES_VI)
        if PROPOSED_PATH.is_file():  # names of foundations not live yet (shown, never practised)
            raw = yaml.safe_load(PROPOSED_PATH.read_text(encoding="utf-8"))
            names |= {str(c["slug"]): str(c["name_vi"]) for c in raw.get("concepts", [])}
        for course in (self.grammar.bundle(GRAMMAR).course, self.pronunciation):
            for c in course.concepts:
                names[c.slug] = c.name_vi
        names |= {c.slug: c.name_vi for c in self.cmap.competencies}
        return names

    def _href(self, a: Activity) -> str:
        if a.kind == "review":
            return "/tu-vung"
        if a.kind in ("diagnostic", "practise_competency"):
            skill = next(c.skill for c in self.cmap.competencies if c.slug == a.target)
            return {"writing": "/viet", "reading": "/doc", "listening": "/nghe"}.get(skill, "/")
        return self._href_node(a.target)

    def _href_node(self, node: str) -> str:
        """Where a foundation is practised."""
        if node in VOCAB_BANDS:
            return "/tu-vung"
        if node in {c.slug for c in self.pronunciation.concepts}:
            return "/phat-am"
        concept = next(
            (c for c in self.grammar.bundle(GRAMMAR).course.concepts if c.slug == node), None
        )
        if concept is not None and concept.part_of is None:
            return f"/on-tap/cot-moc/{node}"
        return f"/on-tap/phan/{node}"

    def _state(
        self, learner_id: str, now: datetime
    ) -> tuple[dict[str, Estimate], dict[str, Estimate], dict[str, int]]:
        """(live foundations, competencies with evidence, due reviews) for a learner."""
        grammar = self.grammar.bundle(GRAMMAR).course
        with self.grammar.pool().connection() as conn:
            learner = self.grammar._learner(conn, learner_id)
            p: dict[str, float] = {}
            seen: dict[str, int] = {}
            for slug, value in conn.execute(
                "select c.slug, m.p_known from mastery m join concepts c on c.id=m.concept_id "
                "join subjects s on s.id=c.subject_id where m.learner_id=%s and s.slug in (%s,%s)",
                (learner, GRAMMAR, PRONUNCIATION),
            ).fetchall():
                p[slug] = float(value)
            for node, count in conn.execute(
                "select node, count(*) from grammar_answers where learner_id=%s and course=%s "
                "group by node",
                (learner, GRAMMAR),
            ).fetchall():
                seen[node] = int(count)
            # Competency estimates (Writing evidence from essays); evidence = distinct essays.
            comp_p: dict[str, float] = dict(
                conn.execute(
                    "select c.slug, m.p_known from mastery m join concepts c on c.id=m.concept_id "
                    "join subjects s on s.id=c.subject_id where m.learner_id=%s and s.slug=%s",
                    (learner, COMPETENCY_SUBJECT),
                ).fetchall()
            )
            comp_n: dict[str, int] = dict(
                conn.execute(
                    "select competency, count(distinct source_id) from competency_observations "
                    "where learner_id=%s group by competency",
                    (learner,),
                ).fetchall()
            )
            # Reading evidence: one per answer (specs/listening-reading/step-4.3.md).
            for comp, n in conn.execute(
                "select competency, count(*) from reading_answers where learner_id=%s "
                "group by competency",
                (learner,),
            ).fetchall():
                comp_n[comp] = comp_n.get(comp, 0) + int(n)
            # Listening evidence: one per answer (specs/listening-reading/step-4.4b.md).
            for comp, n in conn.execute(
                "select competency, count(*) from listening_answers where learner_id=%s "
                "group by competency",
                (learner,),
            ).fetchall():
                comp_n[comp] = comp_n.get(comp, 0) + int(n)
            self._available = set(AVAILABLE_SKILLS)
            if self.reading is not None and self.reading.any_served(conn):
                self._available.add("reading")
            if self.listening is not None and self.listening.available and self.listening.items():
                self._available.add("listening")
            cards = conn.execute(
                "select list_slug, word_key, fsrs_state, due_at from vocab_cards "
                "where learner_id=%s",
                (learner,),
            ).fetchall()
        foundations: dict[str, Estimate] = {}
        for c in grammar.concepts:
            if c.part_of is None:  # a milestone: its weakest hidden node
                hidden = [h.slug for h in grammar.concepts if h.part_of == c.slug]
                if hidden:
                    foundations[c.slug] = Estimate(
                        min(p.get(h, UNSEEN_P_KNOWN) for h in hidden),
                        sum(seen.get(h, 0) for h in hidden),
                    )
            else:
                foundations[c.slug] = Estimate(p.get(c.slug, UNSEEN_P_KNOWN), seen.get(c.slug, 0))
        for c in self.pronunciation.concepts:
            if c.part_of is not None:
                foundations[c.slug] = Estimate(p.get(c.slug, UNSEEN_P_KNOWN), 0)
        wordlist = self.grammar.wordlist()
        stability = {
            key: float(state.get("stability") or 0.0)
            for lst, key, state, _ in cards
            if lst == wordlist.slug
        }
        for node, band in bands(
            [(w.key, w.level, w.origin) for w in wordlist.words], stability
        ).items():
            foundations[node] = Estimate(band.p, band.reviewed)
        due = {
            "vocab": sum(1 for lst, _, _, at in cards if lst != PHRASES and at <= now),
            "phrases": sum(1 for lst, _, _, at in cards if lst == PHRASES and at <= now),
        }
        competencies = {
            slug: Estimate(float(value), int(comp_n.get(slug, 0))) for slug, value in comp_p.items()
        }
        return {k: v for k, v in foundations.items() if k in self.live}, competencies, due

    def today(self, learner_id: str, minutes: int) -> dict[str, Any]:
        """The engine's list right now, recomputed on every call (the plan's first version)."""
        return self._compute(learner_id, minutes, self.clock())

    def _compute(self, learner_id: str, minutes: int, now: datetime) -> dict[str, Any]:
        foundations, competencies, due = self._state(learner_id, now)
        names = self._names()
        result = recommend(
            self.cmap,
            foundations,
            competencies,
            due,
            frozenset(self._available),
            now.date(),
            minutes,
            now,
            names,
        )
        return {
            "activities": [
                {
                    "kind": a.kind,
                    "target": a.target,
                    "name_vi": names.get(a.target, a.target),
                    "via": a.via,
                    "href": self._href(a),
                    "trace": a.trace.model_dump(mode="json"),
                }
                for a in result.activities
            ],
            "notes": result.notes,
            "names": {k: v for k, v in names.items()},
            "target": {
                "overall": self.cmap.target.overall,
                "exam_date": self.cmap.target.exam_date.isoformat(),
                "links_status": self.cmap.status,
            },
            "due": due,
        }

    # --- today's plan, fixed for the day (specs/two-layer-map/step-m5.md) ----------------------

    def plan(self, learner_id: str, minutes: int) -> dict[str, Any]:
        """The day's first list, stored, with each activity's done mark and minutes."""
        now = self.clock()
        day = local_day(now)
        pool = self.grammar.pool()
        with pool.connection() as conn:
            learner = self.grammar._learner(conn, learner_id)
            row = conn.execute(
                "select plan from today_plans where learner_id=%s and day=%s", (learner, day)
            ).fetchone()
        if row is None:
            fresh = self._compute(learner_id, minutes, now)
            with pool.connection() as conn:
                conn.execute(
                    "insert into today_plans(learner_id,day,minutes,plan,created_at) "
                    "values (%s,%s,%s,%s,%s) on conflict (learner_id,day) do nothing",
                    (learner, day, minutes, Jsonb(fresh), now),
                )
                row = conn.execute(  # another request may have stored the day's plan first
                    "select plan from today_plans where learner_id=%s and day=%s", (learner, day)
                ).fetchone()
            assert row is not None
        stored: dict[str, Any] = row[0]
        due: dict[str, int] = stored.get("due", {})
        evidence = self._evidence(learner, start_of_day(now))
        activities = []
        for a in stored["activities"]:
            target = self._target(a["kind"], a["target"])
            planned = int(due.get(a["target"], 0))
            activities.append(
                {
                    **a,
                    "done": is_done(target, a["target"], planned, evidence),
                    "minutes": estimate_minutes(target, planned, a["target"]),
                }
            )
        return {
            **{k: v for k, v in stored.items() if k != "due"},
            "activities": activities,
            "day": day.isoformat(),
            "done_count": sum(a["done"] for a in activities),
        }

    def _target(self, kind: str, slug: str) -> Target:
        if kind == "review":
            return Target("review")
        if kind in ("diagnostic", "practise_competency"):
            skill = next((c.skill for c in self.cmap.competencies if c.slug == slug), None)
            return Target("competency", skill=skill)
        if slug in VOCAB_BANDS:
            return Target("vocab_band")
        if slug in {c.slug for c in self.pronunciation.concepts}:
            return Target("pronunciation")
        concepts = self.grammar.bundle(GRAMMAR).course.concepts
        hidden = tuple(c.slug for c in concepts if c.part_of == slug)
        return Target("grammar", nodes=(slug, *hidden))

    def _evidence(self, learner: UUID, since: datetime) -> TodayEvidence:
        with self.grammar.pool().connection() as conn:
            reviews: dict[str, int] = {}
            per_word: list[tuple[str, int]] = []
            wordlist = self.grammar.wordlist()
            for lst, key, n in conn.execute(
                "select list_slug, word_key, count(*) from vocab_reviews "
                "where learner_id=%s and answered_at>=%s group by list_slug, word_key",
                (learner, since),
            ).fetchall():
                source = "phrases" if lst == PHRASES else "vocab"
                reviews[source] = reviews.get(source, 0) + int(n)
                if lst == wordlist.slug:
                    per_word.append((str(key), int(n)))
            grammar = {
                str(node): int(n)
                for node, n in conn.execute(
                    "select node, count(*) from grammar_answers "
                    "where learner_id=%s and answered_at>=%s group by node",
                    (learner, since),
                ).fetchall()
            }
            competencies: dict[str, int] = {}
            for table in ("reading_answers", "listening_answers"):
                for comp, n in conn.execute(
                    f"select competency, count(*) from {table} "  # fixed table names
                    "where learner_id=%s and answered_at>=%s group by competency",
                    (learner, since),
                ).fetchall():
                    competencies[str(comp)] = competencies.get(str(comp), 0) + int(n)
            counts = conn.execute(
                "select (select count(*) from speech_recordings "
                "where learner_id=%s and created_at>=%s), "
                "(select count(*) from essays where learner_id=%s and submitted_at>=%s)",
                (learner, since, learner, since),
            ).fetchone()
        assert counts is not None
        by_band: dict[str, int] = {}
        for key, n in per_word:
            word = wordlist.get(key)
            if word is not None:
                band = band_of(word.level, word.origin)
                by_band[band] = by_band.get(band, 0) + n
        return TodayEvidence(
            reviews=reviews,
            bands=by_band,
            grammar=grammar,
            recordings=int(counts[0]),
            essays=int(counts[1]),
            competencies=competencies,
        )

    def week(self, learner_id: str) -> dict[str, Any]:
        """This week's days (Monday to Sunday, Vietnam time) with the answers saved on each."""
        now = self.clock()
        begin, end = week_bounds(now)
        with self.grammar.pool().connection() as conn:
            learner = self.grammar._learner(conn, learner_id)
            parts = " union all ".join(
                f"select {col} as at from {table} where learner_id=%(l)s "  # fixed names
                f"and {col}>=%(b)s and {col}<%(e)s"
                for table, col in STUDY_TABLES
            )
            stamps = [
                r[0] for r in conn.execute(parts, {"l": learner, "b": begin, "e": end}).fetchall()
            ]
        days = study_week(stamps, now)
        return {
            "days": [
                {
                    "date": d.day.isoformat(),
                    "answers": d.answers,
                    "studied": d.studied,
                    "today": d.is_today,
                    "future": d.is_future,
                }
                for d in days
            ],
            "studied_days": sum(d.studied for d in days),
        }

    def maps(self, learner_id: str) -> dict[str, Any]:
        """Both maps for one learner (spec M4): every competency with its foundations underneath,
        each estimate with the evidence it rests on. Read-only; no band is shown."""
        foundations, competencies, _ = self._state(learner_id, self.clock())
        names = self._names()
        skills: dict[str, list[dict[str, Any]]] = {}
        for c in self.cmap.competencies:
            est = competencies.get(c.slug)
            links = []
            for link in c.links:
                f = foundations.get(link.node)
                links.append(
                    {
                        "node": link.node,
                        "kind": link.kind,
                        "name_vi": names.get(link.node, link.node),
                        "live": link.node in self.live,
                        "href": self._href_node(link.node) if link.node in self.live else None,
                        **_estimate(f),
                    }
                )
            skills.setdefault(c.skill, []).append(
                {
                    "slug": c.slug,
                    "name_vi": c.name_vi,
                    "available": c.skill in self._available,
                    **_estimate(est, MIN_EVIDENCE),
                    "links": links,
                }
            )
        return {
            "skills": [{"skill": k, "competencies": v} for k, v in skills.items()],
            "known": KNOWN,
            "root_cause_below": ROOT_CAUSE_BELOW,
            "min_evidence": MIN_EVIDENCE,
            "target": {
                "overall": self.cmap.target.overall,
                "exam_date": self.cmap.target.exam_date.isoformat(),
                "links_status": self.cmap.status,
            },
        }


def _estimate(est: Estimate | None, min_evidence: int = 1) -> dict[str, Any]:
    """p and evidence, with a status: unmeasured, weak (< 0.8), growing, known (>= 0.9)."""
    if est is None or est.evidence < min_evidence:
        return {
            "p": None if est is None else round(est.p, 3),
            "evidence": 0 if est is None else est.evidence,
            "status": "unmeasured",
        }
    status = "known" if est.p >= KNOWN else ("growing" if est.p >= ROOT_CAUSE_BELOW else "weak")
    return {"p": round(est.p, 3), "evidence": est.evidence, "status": status}
