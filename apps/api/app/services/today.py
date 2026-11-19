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
from typing import Any

from app.competencies.bands import bands
from app.competencies.check import load_foundations
from app.competencies.model import VOCAB_BANDS, CompetencyMap, load_map
from app.curriculum.course import load_course
from app.engine.graph import UNSEEN_P_KNOWN
from app.engine.recommend import Activity, Estimate, recommend
from app.services.competency_evidence import SUBJECT as COMPETENCY_SUBJECT
from app.services.grammar import GrammarService

GRAMMAR = "english-ielts"
PRONUNCIATION = "english-pronunciation"
PHRASES = "my-phrases"
AVAILABLE_SKILLS = frozenset({"writing"})  # Reading with CP4, Listening with CP5, Speaking phase 5
BAND_NAMES_VI = {
    "vocab-a1": "Từ vựng A1",
    "vocab-a2": "Từ vựng A2",
    "vocab-b1": "Từ vựng B1",
    "vocab-b2": "Từ vựng B2",
    "vocab-c1": "Từ vựng C1",
    "vocab-nawl": "Từ vựng học thuật (NAWL)",
}
REVIEW_NAMES_VI = {"vocab": "Từ vựng", "phrases": "Cụm từ đã lưu"}


class TodayService:
    def __init__(
        self,
        grammar: GrammarService,
        cmap: CompetencyMap | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.grammar = grammar
        self.cmap = cmap or load_map()
        self.live = load_foundations().live
        self.clock = clock
        # No items file for pronunciation, so not a grammar bundle: its course only.
        self.pronunciation = load_course(grammar.courses_dir / f"{PRONUNCIATION}.yaml")

    def _names(self) -> dict[str, str]:
        names = dict(BAND_NAMES_VI) | dict(REVIEW_NAMES_VI)
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
        if a.target in VOCAB_BANDS:
            return "/tu-vung"
        if a.target in {c.slug for c in self.pronunciation.concepts}:
            return "/phat-am"
        concept = next(
            (c for c in self.grammar.bundle(GRAMMAR).course.concepts if c.slug == a.target), None
        )
        if concept is not None and concept.part_of is None:
            return f"/on-tap/cot-moc/{a.target}"
        return f"/on-tap/phan/{a.target}"

    def today(self, learner_id: str, minutes: int) -> dict[str, Any]:
        now = self.clock()
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
        names = self._names()
        result = recommend(
            self.cmap,
            {k: v for k, v in foundations.items() if k in self.live},
            {
                slug: Estimate(float(value), int(comp_n.get(slug, 0)))
                for slug, value in comp_p.items()
            },
            due,
            AVAILABLE_SKILLS,
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
        }
