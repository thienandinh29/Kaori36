# SPEC — NodeTrail

Positioning: *An English learning app for Vietnamese learners: knows where you are, and leads you onward.* It covers
the four IELTS skills, from A1 to C1.
Target users: Vietnamese self-learners and university students preparing for IELTS. The first learner is the owner
(IELTS in summer 2027, target 6.5), then friends and family, free. Teachers and centres (a class view) come later.
The master roadmap, with a measured gate per phase: `docs/v2/plan-english-pack.md`.

## Problem
Median online-course completion is ~12.6% (Jordan, 2015). Self-learners don't know where to start, forget what they
learned, and get feedback that is either a single band score or a chatbot's opinion, with no idea what to practise
next. Vietnamese learners also share specific weak points (final consonants, articles, plural and third-person -s,
tense choice) that generic courses do not target.

## Core loop
Level test → grammar roadmap of CEFR milestones → **assess → learn → practice → adjust → review**, across vocabulary,
grammar, writing, pronunciation, reading, listening and speaking. Every skill feeds the same mastery model.

## Features (status in `docs/v2/plan-english-pack.md`)
1. **Level test and roadmap.** Milestones by CEFR level, each with hidden nodes. A failed milestone test opens its nodes
   and remediates the weakest prerequisite. Node brightness = mastery.
2. **Vocabulary.** NGSL/NAWL plus authored words, FSRS review cards, objective item types (meaning, gap-fill,
   collocation, word form). No prerequisite edges.
3. **Grammar practice and lessons.** Items with a misconception on every wrong option. Lessons from licence-checked
   open textbooks: an English voice, English and Vietnamese subtitles by level, a whiteboard, and checkpoints.
4. **Writing (Task 2 and Task 1).** Errors from LanguageTool typed by ERRANT and mapped to grammar nodes. Feedback on
   the four criteria with quoted evidence. A band shown as a range. Paragraph rewrites. Task 1 facts checked against
   the chart's data.
5. **Pronunciation.** Read authored sentences aloud. A recording-quality check, then the target sounds Vietnamese
   speakers often miss are scored. Nothing is marked wrong until false alarms are measured on recordings labelled by
   a trained reviewer (Gold).
6. **Reading and Listening.** Levelled open texts, IELTS-style questions generated ahead, checked blind and reviewed by
   hand. Audio by the self-hosted voice.
7. **Speaking (Part 1–3).** Transcript, grammar and vocabulary from the Writing pipeline, pronunciation from phase 3,
   fluency measures. No band without examiner ratings.
8. **Socratic help and review.** Hints never hand over the answer. FSRS schedules review; good phrases become cards.

## Engine (deterministic, testable)
- Mastery: Bayesian Knowledge Tracing per learner × node (grammar nodes, pronunciation sound groups, later Reading and
  Listening skills).
- Item difficulty / learner ability: Elo (parked until there is enough answer data).
- Spaced repetition: FSRS.
- Path selection & remediation: rule engine over the graph + mastery state.
- Grading: objective graders: answer keys, typed answers exact after normalisation, LanguageTool and ERRANT for
  writing errors, a small band model for essays (shown as a range), phone recognition and GOP for pronunciation.
- LLM + RAG: explanations only, with citations.

### Decision audit trail (explainability)
Every engine decision returns a `DecisionTrace` next to its result, so NodeTrail can show *why* it concluded a
learner is weak at concept A and not B:
- `kind`: `bkt_update` | `placement_step` | `root_cause` | `next_item` | `review`
- `concept_slug`, `at`
- `prior`: P(L_{t-1}) before the evidence; `evidence`: item, correct/wrong, misconception, slip/guess used;
  `posterior`: P(L_t) after the evidence and the learning transition
- `rule`: which rule fired and which branch was chosen (e.g. "wrong on loops → descend to prerequisite
  boolean-expressions, lowest p_known 0.31")
- `alternatives`: the other candidates considered and why they lost

Traces are pure data (no DB inside the engine), stored per learner, returned by the API, and rendered in Vietnamese
in a "Vì sao?" panel. Existing functions (`bkt.update`, `srs.review`) stay as they are; traced wrappers add the trace.

### Verification gate (generated content)
A two-step pipeline for every generated question:
1. **Generator** writes the item and cites the `chunk_id`s it is based on.
2. **Verifier** receives **only the text of those chunks** (no other context, no answer key), tries to answer the item
   blind, and its answer is compared with the key.
The verifier is **always a different model family from the generator** (today DeepSeek generates and a free Ernie
model checks; the gateway refuses a checker of the generator's family), so a model never grades its own output
(self-preference bias).
Unanswerable or mismatched → `status = needs_review` and the item is **not served**; only `verified` items reach
learners. Tutor hints go through the same check against their cited chunks before display. Pass/fail counts feed
`guardrails/metrics.py`, next to the error rate measured on the human-labelled sample.

### Who decides what is true (validation)
**The developer is not the ground truth.** Correctness of answer keys, example sentences, pronunciation targets, text
levels and bands comes from experts or expert-labelled datasets, not from the owner's judgement. Every label records
its tier: **Gold** (expert), **Silver** (two independent checks agree, or a Gold sample shows the process is
reliable), **Bronze** (one source). Gates need Gold, learner-facing content needs Silver, Bronze is for development
only. Progress is measured by independent tests, never by NodeTrail's own mastery estimates. Design:
`specs/validation/spec.md`; experiments: `research/`.

## Non-functional
- Vietnamese-first UI and explanations; the English being learned is shown and heard in English.
- **A voice is personal data.** Recordings stay on our own machines, are deleted after analysis unless the learner
  keeps them, and need consent. Only the owner records until a privacy review.
- Every explanation traceable to a source chunk.
- Learner data private by default (Supabase RLS).
- **Uploads (from the contest demo; for other subjects later):** an uploaded file is read, chunked and sent to the
  model APIs, so it leaves our servers. This was allowed for the 2026 competition demo only, with a notice accepted
  first (`vi` i18n file) and deletion after the demo. It is not offered to real learners: that needs a privacy review
  first (provider data terms, consent, retention, or a self-hosted model).

## Other subjects (later)
NodeTrail began as a tutor for any subject: Deep Research on open textbooks, courses for Python and statistics,
uploads. That engine is still in the code (`apps/api/app/research/`, `app/sources/`, `data/courses/`) and is the base
for other subjects later; it is not developed further now. The 2026 contest demo, with its two modes (Nhanh and Deep
Research) and its quality bar, is described in `docs/archive/contest-2026/`. The old plan, `docs/v2/plan-m0-m1.md`, is
superseded.

## Non-goals (for now)
- Gamified streaks or speed rewards.
- Generating content without a trusted, licence-checked source.
- A band score from a model alone: bands are shown as ranges, and only where an evaluation against examiner bands
  exists.
- Real exam passages or past papers (copyrighted).
