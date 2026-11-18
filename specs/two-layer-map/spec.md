# Spec: two maps and one recommendation engine

Status: **approved 18 Nov 2026** (decisions in `tasks.md`: overall 7.0, exam assumed July 2027); M1 and M2 built (M2: root cause only below 0.8, see `tasks.md`). Proposed by the owner. The owner reviews this page before any
code. It fits the current plan (`docs/v2/plan-english-pack.md`) and should be settled before phase 4's CP4, because
CP4's Reading skill nodes are the first nodes of layer 2.

## Why
Today each skill has its own path:
- the grammar roadmap picks the next grammar node;
- vocabulary has its own FSRS queue;
- writing errors move grammar nodes;
- pronunciation has its own course.

Nothing answers the learner's real question: **"with the time I have today, what should I do to raise my IELTS band?"**
Sometimes the answer is a foundation ("your Task 2 grammar is weak because conditionals are not secure"). Sometimes
it is exam practice ("your foundations are fine; practise True/False/Not Given").

## Layer 1: CEFR Knowledge Map (foundations)
What the learner *knows* about the language, by CEFR level. Almost all of it already exists:

| Part | Nodes | Evidence | Exists? |
|---|---|---|---|
| Grammar | Milestones and hidden nodes (`data/courses/english-ielts.yaml`; the proposed path has 28 milestones and 51 nodes) | Milestone tests, practice, writing errors (error map) | Yes |
| Vocabulary | One node per CEFR band (A1–C1) and the academic list (NAWL) | Derived from FSRS: the share of that band's words whose cards are stable. Not BKT, since vocabulary has no prerequisite edges | Cards yes; band nodes new |
| Pronunciation | The four sound groups (`data/courses/english-pronunciation.yaml`) | Marks after the gate (3.4b) | Yes |
| Usage | Linking words, collocations, word formation, register | Writing analysis (linking words are counted already), later items | Partly |

## Layer 2: IELTS Competency Map (exam skills)
What the learner can *do* under exam conditions:

| Skill | Competency nodes | Evidence | Exists? |
|---|---|---|---|
| Reading | Detail, main idea, inference, writer's view, skimming (the skills tagged on every Reading item) | Answers to approved items, graded by key (CP4) | Tags yes; nodes in CP4 |
| Listening | The same skills on audio, plus dictation | Answers to approved items (CP5) | No |
| Writing | Task Achievement or Response, Coherence and Cohesion, Lexical Resource, Grammatical Range and Accuracy, for Task 1 and Task 2 | Code checks on each essay (linking words, error rates, word levels, Task 1 facts). The band model's per-criterion outputs come **only after calibration against examiner bands** (phase 2 gate); until then they are shown, never used as evidence | Checks yes; nodes new |
| Speaking | Fluency and Coherence, Lexical Resource, Grammatical Range and Accuracy, Pronunciation | Phase 5 measures | No |

The estimate for each competency is a mastery probability, like every other node. It is shown as a **level band with
its uncertainty**, never as an exam band, until it is calibrated against real bands.

## The links between the layers
A hand-written, code-checked data file, `data/maps/ielts-competencies.yaml`. Each competency lists the foundations
that **support** it, each with a kind:
- `requires`: the competency cannot be good without it. Example: Writing Grammatical Range needs complex sentences,
  conditionals, relative clauses and the passive.
- `helps`: it raises the competency but is not essential. Example: Reading inference is helped by modals of
  deduction.

Examples, for the owner to correct. Four of these nodes are live today (present-perfect-vs-past, articles-basic,
conditionals-1-2, passive-present-past). The others (agreement-long-subjects, defining-relative, linking-ideas,
hedging-language) exist only in the proposed path (`specs/grammar-lessons/path.md`). The checker accepts links to
proposed nodes only as "not live yet", and the engine ignores them until they are.
- Writing GRA (Task 2) `requires` present-perfect-vs-past, articles-basic, agreement-long-subjects, conditionals-1-2,
  defining-relative and passive-present-past.
- Writing Coherence and Cohesion `requires` linking-ideas.
- Writing Lexical Resource `requires` vocabulary B1 and B2, and `helps` NAWL.
- Speaking Pronunciation `requires` the four sound groups.
- Reading detail `requires` vocabulary at the text's level; Reading writer's view `helps` hedging-language.

The checker refuses a link to a node that does not exist, a competency with no `requires` foundation, and cycles.

## The Learning Recommendation Engine
A **pure function** in `app/engine/recommend.py`, unit-tested and traced like the rest of the engine.
- **Inputs:**
  - mastery for both layers, and how much evidence each node rests on;
  - due reviews;
  - the learner's target (band per skill, exam date);
  - today's time.
- **Output:** an ordered list of 3–5 activities. Each has a `DecisionTrace`, so "Vì sao?" can explain it in
  Vietnamese.

The rules, in order:
1. **Due reviews first** (vocabulary cards, saved phrases, grammar reviews), with a cap so they never fill the whole
   day.
2. **Unmeasured before measured.** A competency with too little evidence gets a short diagnostic first: one Reading
   passage, one essay. The engine never guesses a weakness from nothing.
3. **Pick the competency with the largest gap** to the target, weighted by how close the exam is (practice weighs more
   as the exam nears).
4. **Root cause through the links.** If one of that competency's `requires` foundations is below "known" (0.9), recommend
   learning that foundation: its lesson, then practice. This is the same idea as today's remediation. The trace reads,
   for example: "Viết Task 2 yếu về ngữ pháp → câu điều kiện loại 1–2 chưa chắc (0,52) → học câu điều kiện trước". If
   all its foundations are known, recommend practising the competency itself.
5. **Balance.** At most two foundation activities in a row, and at least one exam-style activity a day once the
   foundations of the targeted skill are known.
6. **Never praise speed or streaks.** Only mastery reached is celebrated, as everywhere in NodeTrail.

## What is measured before it is trusted
- **Simulation (a CI gate, like `english_gate`):** simulated learners, each given one weak foundation behind one weak
  competency. The engine must pick that foundation (or practice, when none is weak) in at least 90% of cases. The
  report also gives how often it picks practice when a foundation is weak, and the reverse.
- **The owner's use:** two weeks of following the daily list. The owner notes each day whether it was the right thing
  to do, and the share is reported.

## Steps, each its own PR (proposed)
| Step | Work |
|---|---|
| M1 | `ielts-competencies.yaml` with layer-2 nodes and links, its checker, and vocabulary band nodes derived from FSRS |
| M2 | `engine/recommend.py`: the rules above, traces, unit tests and the simulation gate |
| M3 | API `GET /today` (the ordered list with traces) and the home page "Hôm nay" built on it |
| M4 | A page showing both maps side by side: foundations under each competency, with what is measured and how surely |

Reading competency evidence arrives with CP4, Listening with CP5, Speaking with phase 5. Until then those nodes show
"chưa đo" (not measured), and rule 2 sends the learner to a first diagnostic.

## Decisions for the owner
1. The target: band per skill (or one overall band) and the exam date.
2. The links in `ielts-competencies.yaml`: which foundations each competency `requires`.
3. Whether the band model's per-criterion outputs may become evidence once calibrated (proposed: yes, only after the
   phase 2 gate).
4. The daily balance: the review cap and how many foundation activities in a row.
5. Where it goes in the plan. Proposed: M1–M2 before CP4, so CP4 builds its Reading nodes into layer 2; M3–M4 after
   CP4.

## Not in this spec
A predicted exam band (no calibration data yet), adaptive item difficulty (Elo stays parked), teacher or class views.
