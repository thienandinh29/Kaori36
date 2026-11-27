# PLAN — NodeTrail

**The one plan.** Where the project is, what comes next, and how each phase is judged done. It replaces
`docs/v2/plan-english-pack.md` (20 Nov 2026), which stays for its history and full log; that plan came from the owner's proposal
(`docs/v2/english-pack-proposal.vi.md`) and the strategy agreed on 18 Nov 2026. What the product does: `SPEC.md`. How we work:
`AGENTS.md`. What waits on the owner: `dolater.md`. Experiments: `research/`.

**Keep it current.** Update the Status column and the Log in the same pull request that lands the work or records a decision.
Status values: `done`, `built` (code done, gate not measured), `in progress`, `next`, `planned`, `specified`, `parked`, `cut`.

## Goal and order of priority
NodeTrail is one codebase with three kinds of value, in a fixed order:
1. **Learning:** the owner reaches IELTS 7.0 overall in summer 2027 (exam assumed 1 Jul 2027 until the owner sets a date),
   then friends and family use it free.
2. **Measured independently:** progress comes from independent tests every 4 weeks, never from NodeTrail's own estimates.
3. **Better algorithms from the data:** knowledge tracing, forgetting, reliable generated content.
4. **A portfolio** for ML engineer, AI engineer and data science roles: case studies with hypothesis, method, results and
   limits, negative results kept.

Time is split as about 65% learning English with NodeTrail, 25% building and research, 10% writing up. The exam comes first:
if building eats study time, stop at the nearest gate. Budget: 30–40 hours a week.

## Where we are (20 Nov 2026)
- **Built and in CI:** phases 0–3 and most of phase 4; the validation system (V1–V5); the two maps and "Hôm nay"; FORGET-001
  collection. 2,290 API tests and 240 web unit tests pass; 39 browser tests run on the whole stack in CI.
- **No phase gate is measured yet.** Every gate waits on the owner or on a reviewer: the owner's daily use and baseline test,
  a teacher's labels, examiner-banded essays, recordings labelled by a phonetics-trained reviewer.
- **Content is still draft.** Grammar items, the word list, the sample lesson, the error map, the competency links and the
  pronunciation tips wait for a teacher. Reading: 30 OpenStax texts, 291 questions on the current passages (52 verified and
  waiting for the owner's review, 2 approved, 206 waiting for blind checks run by a daily batch).
- **Most time-critical:** the owner's **baseline test** on all four skills. Every week of learning before it is a week the
  progress study cannot see.

## Roadmap to summer 2027
| When | Focus | Done when | Status |
|---|---|---|---|
| 18 Nov – 31 Dec 2026 | **Stabilise and baseline.** Validation system; Reading MVP; the two maps and the recommendation engine; FORGET-001 collecting; a baseline from an independent test on four skills; KT-001 and FORGET-001 data collection starts | NodeTrail is the owner's daily study tool; the baseline is recorded | in progress: everything built; baseline and daily use pending |
| Jan – Feb 2027 | **Learn and research.** Daily use; the first essays rated by an independent rater; KT-001 report; FORGET-001 first numbers (after 4+ weeks) | A first ML case study with real data | planned |
| Mar – Apr 2027 | **AI reliability and analytics.** VER-001 benchmark of the question pipeline; Speaking (phase 5); human-in-the-loop review in steady use; learning analytics | Two more case studies with evidence | planned |
| May – Jun 2027 | **IELTS first.** Feature freeze except fixes; exam practice; independent mock tests | Exam readiness measured, not guessed | planned |
| Summer 2027 | **Exam and portfolio.** The exam and its result; reports, an English README, architecture docs, a demo | The portfolio is published; negative results stay in it | planned |

If the exam result falls short of 7.0, the honest record of the gap is still part of the portfolio. Realistic gains from the
studies the owner's research cites (to check in the papers): about +0.5 band after 200–240 hours of instruction (Elder and
O'Loughlin, 2003), +0.30 on average after about 284 hours (Kang et al., 2021), faster from bands 4–6 than above 6.5. A 7.0 is a
matter of structured hours.

## Product phases and their gates
A phase ends only when its gate is measured, with labels of the tier the gate names (`specs/validation/spec.md`). A missed
target is recorded with the number and the reason, never hidden.

| Phase | Goal (spec) | Gate (measured) | Status |
|---|---|---|---|
| 0 | Foundations: code sandbox, one-command start, CI runs the whole stack | Escape tests; code practice through the API; start confirmed on the owner's laptop | done |
| 1 | Roadmap, level test, vocabulary, grammar (`specs/level-test/`, `vocabulary/`, `web-english/`, `grammar-lessons/`) | Placement accuracy ≥ 90% with ≤ 20 questions (simulated now: 85% single-gap, 92% any state, the recorded baseline); verifier catch rate on 50 planted-error items; the owner studies daily for 2 weeks | built; gate pending (daily use, planted items, teacher review) |
| 2 | Writing, Task 2 then Task 1 (`specs/writing/`, steps 2.1–2.10) | Error → node mapping ≥ 90% on 100 errors checked by a teacher; QWK ≥ 0.7 against examiner bands on 50–100 private essays; band stability | built; gate waits on examiner-banded essays and a teacher |
| 3 | Pronunciation (`specs/pronunciation/`, steps 3.1–3.7c) | False alarms ≤ 10% on 50–100 of the owner's kept recordings labelled by a phonetics-trained reviewer (Gold), before any red mark; speechocean762 baseline recorded (sentence r 0.59, phone AUC 0.86) | built; gate waits on the reviewer's labels; 3.6b part 2 waits on the L2-ARCTIC licence check |
| 4 | Reading and Listening (`specs/listening-reading/plan.md`, checkpoints CP0–CP6) | Every question verified blind and reviewed before it enters the bank; an expert's labels against the checker on 50 items (agreement, kappa) | in progress (table below) |
| 5 | Speaking Part 1–3, then opening to testers (`specs/speaking/`) | Per-user limits and a daily cost cap working; ≥ 5 of 10 testers still using it after 2 weeks; old errors falling over 4 weeks; word error rate and grammar-flag accuracy measured | specified; waits on the owner's decisions |

### Phase 4 checkpoints
| CP | Work | Status |
|---|---|---|
| CP1 | Texts: 30 OpenStax texts (B2–C1, licence read by the owner); Simple English Wikipedia (A2–B1) must be fetched on the owner's laptop | partly done (OpenStax done) |
| CP2a | Generation (DeepSeek) and blind check (free Ernie), every call logged with a cost cap; a daily batch checks up to 45 questions | built, running daily |
| CP2b | Planted-error test of the checker on Reading items (50 faulty + 50 good) | next (needs the bank; "two defensible answers" faults need a teacher) |
| CP3 | Owner's review queue (`/duyet-doc`, by passage, keyboard) and the agreement report | built; the owner's review of 52 questions pending |
| CP4 | Reading practice and timed tests (`/doc`), Silver questions only | built |
| CP4b | Why the wrong answer tempted you: first on a test taken outside the app (`step-4.3d.md`), then on the bank's questions (planted-test gate) | in progress: 4.3d part 1 built (paste, check, mark, explain); part 2 next |
| CP4c | Exam details: time warnings, highlighting, side by side, play-once mode | proposed; order is the owner's call |
| CP5 | Listening: dictation and gap-fill (5a), whole passages (5b), shadowing; the audio check (4.4a) built ahead | built; the owner decides whether the machine voice is good enough for whole passages |
| CP6 | Gate report `docs/v2/reading-listening-eval.md` | planned (needs CP2b and the teacher's 50 labels) |

## Next, in order (the owner may reorder)
1. **Owner:** baseline test on four skills (a Cambridge book under exam conditions, scores recorded with `app.progress.cli`);
   daily use; find a teacher (reviewer brief in `specs/validation/reviewer-brief.vi.md`). These unblock more than any build.
   Reviewing the bank's Reading questions on `/duyet-doc` is optional now (when more drills are wanted).
2. **Speaking research and decisions:** a deep-research run (including recognisers that fit a CPU-only machine with about
   4 GB), then the recogniser and the transcript consent wording (`docs/v2/asr-candidates.md` recommends Whisper small.en).
3. **Build next: feedback on a Reading test taken outside the app** (`specs/listening-reading/step-4.3d.md`, CP4b first, owner's
   decision 22 Nov): paste the passage, questions, official key and your answers; code marks against the official key; the model
   explains each wrong answer with CP4b's trap list (unchecked label); vocabulary cards from the passage. Then CP4b for the bank's
   own questions, CP4c exam details, CP2b planted test, the CP6 report, then phase 5 Speaking. The bank stays for drills and
   Listening; reviewing it is optional now, not daily work.
4. **Writing feedback quality (step 2.11):** measure stability on ~20 web essays (the owner collects them); the TR/CC
   structure checks are built (2.11b); then the blind check of claims (planted test first), "Sửa trước" to 3 items. Writing's main measure is
   errors per opportunity next to sentence complexity, not a band.
5. **Ongoing:** the daily Reading blind-check batch; fixes from the owner's use.

## Research tracks (`research/`)
| Id | Question | Status |
|---|---|---|
| KT-001 | Does BKT predict the next answer better than simple baselines (past accuracy, moving average, Elo)? Time split; AUC, log loss, Brier, calibration; also on a public dataset | planned (needs a dataset's licence and the owner's answers) |
| FORGET-001 | What is forgotten after about a week, and does FSRS know? Does BKT overestimate retained grammar? | collecting since 18 Nov; first report after about 4 weeks (≥ 200 delayed reviews) |
| VER-001 | How reliable and costly is the generated-content pipeline? Defect escape, false rejection, review rate, cost per accepted item | planned (needs the teacher's 50 labels) |
| PRON-001 | Does comparing /æ/ only with /ɛ/ make that sound group usable? | done on synthetic speech: false alarms 60% → 10% |

Deep knowledge tracing, a home-made LLM or a band model trained from scratch are not planned: there is not enough data, and
choosing the simple model that fits, and showing why, is the stronger evidence.

## Decisions waiting on the owner (detail in `dolater.md`)
- Order of the next builds: CP4b, CP4c, CP6, Speaking.
- Speaking: the recogniser, the transcript consent wording, whether to look for a rater for 30+ recordings.
- Whether the machine voice is good enough for whole-passage Listening.
- Licences to read: L2-ARCTIC (Vietnamese speakers, pronunciation benchmark), Simple English Wikipedia, the male voice's
  datasets.
- Paying reviewers or not; a paid checker or not (free models allow about 40 Reading checks a day).
- Before anyone else records: a privacy review of the voice policy. Before any paid tier: replace or relicense the NonCommercial
  sources.

## The owner's hands-on work (for the career goal)
The measurement and analysis are the owner's, not the agent's: the placement curve and the verifier catch rate with intervals
(phase 1); scorer selection, QWK and the fine-tuning notebook (phase 2); GOP and false-alarm evaluation (phase 3); the agreement
report against a teacher (phase 4); fluency measures and the tester report (phase 5). One decision-log entry a week in
`docs/v2/decision-log.md`, in the owner's words.

## Frozen and parked
- **Frozen (21 Nov 2026, owner's decision): everything that is not the English app.** Deep Research, the topic flow, code
  practice, uploads, other subjects (maths, Python, statistics) and the contest specs stay in the repository and keep passing
  CI, but nobody builds on them before the exam. The exact paths: `AGENTS.md`, "English only".
- **Parked English ideas** (later, if they earn their place): Elo item difficulty, mastery hysteresis wired with stored
  state, the classroom layer (slides, whiteboard), login and payment (login returns with phase 5's testers).

## Risks
- **The project eats study time.** Stop at the nearest gate.
- **No reviewer found.** Every gate needs Gold labels; without a teacher the app stays a well-tested draft. Finding one is
  the owner's single most important non-study task.
- **One learner.** N-of-1 data cannot support general claims; reports say so.
- **Free checker limits and drift.** Ernie is a free preview model: rerun the planted test before each batch; dots is the backup.
- **Scores are estimates.** Every score shown is a range until measured against examiners. No Speaking band before the exam.
- **Solo practice has limits.** Speech-recognition feedback helps most with explicit corrections and with peers, least alone and
  for stress and intonation; one Vietnamese study saw no Speaking band gain. NodeTrail is one part of Speaking practice, next to
  speaking with a partner or teacher.
- **Licences.** NonCommercial and ShareAlike sources block a paid tier until replaced.

## Log
| Date | Change |
|---|---|
| 2026-11-27 | Fix, Reading 4.3d (owner's first real use): the key and answer reader missed `1.TRUE`, `1-TRUE`, `1A`, `Q1:`, `Câu 1:`, and a "Questions 1–13" header lost the whole key; unreadable answers were taken as all blank; the page hid the server's message and cleared the paste. All fixed; the message now shows under the form and the paste stays |
| 2026-11-26 | Vocabulary: Wiktionary coverage measured (`specs/vocabulary-import/step-wiktionary.md`, owner's request): kaikki.org's wiktextract dump would add a British IPA to 713 of the 981 words without one (IPA 73% → 93%); its British IPA agrees with ours on 93% after notation folds; Vietnamese translations for 68%. Nothing imported; Wiktionary's licence and an enrichment step are the owner's decisions |
| 2026-11-23 | Reading 4.3d part 1 built (CP4b first): paste a test taken elsewhere on `/doc/bai-cua-ban`, the model lists the questions, code reads the official key and the learner's answers, the learner confirms, code marks, each wrong answer explained with the trap list (code names T/F/NG and completion traps) and labelled "chưa kiểm chứng". Owners only; one BKT observation per answered question, once per test fingerprint. Migration 0040. Real-paste accuracy not measured |
| 2026-11-22 | Owner's decision: Reading feedback on tests taken outside the app (Cambridge books, official samples) comes next, as CP4b's first step (`step-4.3d.md`): pasted, marked by code against the official key, wrong answers explained with the trap list, vocabulary cards, evidence once per question; the pasted test stays private. The generated bank stays for drills and Listening; its review is optional. Cambridge material never enters the bank |
| 2026-11-22 | Writing 2.11b built: each Task 2 question's parts (authored; for an own question proposed by code and ticked by the learner, owner's decision), one separate `writing_structure` call describing position and paragraphs with quotes checked in their paragraph, and code's findings (missing part, no position, flipped position, "có thể chưa được phát triển" as a hint). Owners only, never evidence; precision not measured. Migration 0039 |
| 2026-11-21 | Writing step 2.11 from an outside review of the feedback (owner's adjustments): stability measurement (tool built; ~20 web essays to collect), TR/CC structure checks with development as a hint, a blind check of claims by Gemini after a planted test, "Sửa trước" to 3 items, and errors per opportunity next to complexity as Writing's main measure |
| 2026-11-21 | Writing step 2.10, owner's request: write on your own Task 2 question (checked, private to the essay) and a timed 40-minute exam mode on any Task 2 question (server clock, late marked) |
| 2026-11-21 | Writing step 2.9 from an outside review: errors grouped by kind, word count apart from Task Response, complexity as reference, the 0.25 raw-score threshold labelled an assumption, rewrites checked for kept meaning (new facts, flipped negations, dropped argument) |
| 2026-11-21 | Writing: a band per criterion (TR, CC, LR, GRA) specified, owner's request (`specs/writing/spec.md` 8b): shown as a range only where that criterion reaches QWK ≥ 0.7 on held-out examiner-banded essays, never without the overall band. Import of item files now brings newer checks into decided questions (#131) |
| 2026-11-20 | Speaking guided mode, owner's decision: idea building for Part 2/3 (a way to build an answer, never a script) and the same question up to three times with shrinking time for fluency; only first tries count as evidence |
| 2026-11-20 | The owner's Speaking research read (Bronze): it confirms our recogniser measurements. Added to `specs/speaking/spec.md`: recogniser settings, pauses from the raw audio, checks before feedback, a missing -s/-ed never a grammar error, uncertain words, and **no Speaking band before the exam** (the progress study gives it). Solo-practice limits under Risks |
| 2026-11-20 | Lighter loading: `CLAUDE.md` no longer loads `MAP.md` (read on demand); the product's rules live only in `SPEC.md` (Contract), and `AGENTS.md` points to them |
| 2026-11-20 | `PLAN.md` becomes the one plan, with `AGENTS.md` (how we work) and a rewritten `SPEC.md` (what the product does and the rules it keeps), all checked against the code. The target is 7.0 overall (the owner's setting in `data/maps/ielts-competencies.yaml`, 18 Nov); the older plan's 6.5 came from the 14 Nov proposal. Earlier history: `docs/v2/plan-english-pack.md` |
| 2026-11-20 | Say-word: one attempt per recording (migration 0037). Writing 2.6–2.8, CP5b whole passages, shadowing fixes, OpenStax passages cleaned (106 new questions); CP4b specified |
