# SPEC — NodeTrail (what the product does, and the rules it keeps)

This is the product contract. It says **what** NodeTrail does for a learner and **which rules the code enforces**, so a change
that breaks one of them is a bug or needs the owner's decision. How we work: `AGENTS.md`. Where we are and what comes next:
`PLAN.md`. Each feature's detail: `specs/<feature>/`. Status words here: **built** (in the app, tested, in CI), **partly
built**, **specified** (a spec, no code), **planned**. Last checked against the code: 20 Nov 2026.

## Positioning and users
*An English learning app for Vietnamese learners: knows where you are, and leads you onward.* The four IELTS skills, A1 to C1.
- **First learner:** the owner (IELTS in summer 2027, target 7.0 overall). Then friends and family, free.
- **Later:** Vietnamese self-learners and university students; teachers and centres (a class view) after that.

## Problem
Median online-course completion is about 12.6% (Jordan, 2015). Self-learners don't know where to start, forget what they
learned, and get feedback that is either a single band score or a chatbot's opinion, with no idea what to practise next.
Vietnamese learners share specific weak points (final consonants, /θ ð/, articles, plural and third-person -s, tense choice)
that generic courses do not target.

## Core loop
Level test → grammar roadmap of CEFR milestones → **assess → learn → practise → adjust → review**, across vocabulary,
grammar, writing, pronunciation, reading, listening and speaking. Every skill feeds one mastery model, shown on two maps, and
one engine chooses each day's work.

## Features
| # | Feature | What the learner does (web page) | Status |
|---|---|---|---|
| 1 | **Hôm nay and the two maps** | 3–5 activities a day, each with "Vì sao?" (`/`); the CEFR foundation map and the IELTS competency map as a graph with the weakest link marked (`/ban-do`) | built (M1–M4). Writing, Reading and Listening feed competencies; the links between maps are Bronze ("đề xuất") until a teacher checks a sample |
| 2 | **Level test and grammar roadmap** | Level test (`/kiem-tra`); milestones with hidden nodes (`/lo-trinh`); a failed milestone test opens its nodes and remediates the weakest prerequisite; practice per node (`/on-tap/...`); delayed re-checks of "known" nodes on the home page | built: 10 milestones, 19 hidden nodes, 76 draft items (owner-only until reviewed). A longer path (28 milestones, 51 nodes) is proposed, not live |
| 3 | **Vocabulary** | FSRS review cards with meaning, gap-fill, collocation, word form and recall items (`/tu-vung`); hear the word; say the word and see each sound | built: 3,663 words (NGSL/NAWL + 130 authored), draft until a teacher checks a sample |
| 4 | **Grammar lessons** | A lesson before practice: English voice, English and Vietnamese subtitles by level, a board, checkpoints (`/hoc/{node}`) | partly built: the player and one sample lesson; lessons from licence-checked textbooks are specified |
| 5 | **Writing (Task 2 and Task 1)** | Write in the browser (`/viet`); the result (`/bai-viet/{id}`): "Sửa trước" (at most 5 things), grammar errors (LanguageTool, ERRANT, mapped to nodes), feedback on the four criteria with quoted evidence, hint-first self-correction, a paragraph rewrite, saved phrases as cards, repeated errors across essays; Task 1 facts checked against the chart's data; your own Task 2 question, and a timed 40-minute exam; Task 2 structure checks (every part of the question answered, a clear and consistent position, a hint on undeveloped paragraphs) | built (2.1–2.10, 2.11b). No band is shown yet: the band model is not calibrated on examiner-banded essays |
| 6 | **Pronunciation** | Read authored sentences aloud (`/phat-am`): a recording-quality check, then the target sounds Vietnamese speakers often miss are scored; sounds to focus on | built, owner only. Raw scores and "chưa chắc" only: nothing is marked wrong until false alarms are measured on Gold labels |
| 7 | **Reading** | Practice by question type with the deciding sentence highlighted (`/doc/{slug}`); timed 20-minute tests (`/doc/{slug}/thi`); a test taken elsewhere, pasted, marked from its official key with each wrong answer explained (`/doc/bai-cua-ban`) | built. Bank: 30 OpenStax texts; questions are generated, checked blind and reviewed; only Silver questions are served (2 approved so far). Pasted tests: owner only, explanations "chưa kiểm chứng", private to the learner |
| 8 | **Listening** | Dictation and gap-fill from bank sentences (`/nghe/{slug}`); a whole passage by ear, then its questions (`/nghe/bai/{slug}`); shadowing of bank sentences or a YouTube video (`/noi-duoi`) | built; needs the server voice (compose profile `speech`). Machine voice, not exam audio |
| 9 | **Speaking (Part 1–3)** | Guided practice and a strict mock: transcript, fluency measures, grammar and vocabulary from the Writing pipeline, pronunciation on read-aloud only | specified (`specs/speaking/`); waits on the owner's choice of recogniser. No Speaking band before the owner's exam |
| 10 | **Explanations of wrong answers** | Why the key is right and what trap each wrong option set, after answering | specified (CP4b in `specs/listening-reading/spec.md`) |
| 11 | **Reviewer portal** | Teachers and raters label content through a private link, blind (`/kiem-duyet`); the owner's review queue for Reading (`/duyet-doc`) | built (V1–V3, V5) |
| 12 | **Progress study** | An independent test every 4 weeks, recorded by CLI, compared with NodeTrail's own estimates | built (V4); waits on the owner's baseline test |

Owner-only today: draft grammar items and lessons, model feedback on writing, recording, the review pages. There is no login:
the learner id is in the browser, and "owner" means the ids in `DRAFT_ITEM_LEARNERS`.

## Engine (deterministic, tested)
- **Mastery:** Bayesian Knowledge Tracing per learner × node (grammar nodes, pronunciation sound groups, IELTS competencies,
  vocabulary bands). Parameters are book defaults until fitted (`engine/bkt_fit.py`, KT-001).
- **Spaced repetition:** FSRS for vocabulary and saved phrases.
- **Placement and remediation:** rules over the milestone graph (pass → nodes assumed known; fail → open nodes, test 1–2 items
  each, remediate the weakest prerequisite).
- **Recommendation ("Hôm nay"):** due reviews first (capped at about a third), a diagnostic for an unmeasured competency, the
  largest gap traced to its weakest foundation, balance rules. A simulation gate in CI.
- **Graders:** answer keys; typed answers exact after normalisation; LanguageTool and ERRANT; a pinned band model shown only
  as a calibrated range; phone recognition and GOP. Elo item difficulty is parked until there is enough answer data.

### Decision audit trail
Every engine decision returns a `DecisionTrace` next to its result, stored per learner and shown in Vietnamese as "Vì sao?":
- `kind`: `bkt_update` | `placement_step` | `root_cause` | `next_item` | `review` (and the recommendation engine's own);
- `concept_slug`, `at`; `prior` P(L_{t-1}); `evidence` (item, correct or wrong, misconception, slip and guess used);
  `posterior` P(L_t) after the evidence and the learning transition;
- `rule`: which rule fired and which branch was chosen; `alternatives`: the other candidates and why they lost.
Traces are pure data (no database inside the engine). `bkt.update` and `srs.review` stay as they are; traced wrappers add
the trace.

## Contract: rules the code enforces
**Architecture**
- **The LLM is not the decision maker.** The engine decides what to learn next and the graders score; models only explain
  and generate, always citing their source text. A model's opinion is never a grade.
- **Every model call goes through `apps/api/app/llm/gateway.py`** with `routing.yaml` (task × tier → ordered models); no
  feature calls a model SDK or API directly.
- **No long work inside a request:** the Postgres `topic_jobs` queue and a separate worker.
- **The Socratic tutor never hands over the answer;** hints come first. Sena praises real mastery only, never speed or streaks.
- Engine decisions are pure functions in `apps/api/app/engine/`, unit-tested, each returning a `DecisionTrace`.

**Content and verification**
- **Verification gate.** A generator writes each item citing its source text; a model of a **different family** answers it
  blind from that text only (no key, no other context); a mismatch or "cannot tell" sends it to review. Routing today:
  DeepSeek generates; a free Ernie model checks Reading questions and lesson checkpoints (dots as backup); Gemini verifies
  other generated content. The gateway refuses a checker of the generator's family.
- **A Reading question is served only when** it is approved, its `item_ok` labels are Silver or Gold and "right", its passage
  is unchanged (NFC SHA-256), and its code checks pass. Options and headings are shown in a fixed shuffled order on every
  surface; answers are stored in the original order.
- **Listening keys are right by construction:** dictation and gap-fill come from the text's own sentences that the voice reads
  exactly; whole-passage questions are the passage's served Reading questions (headings left out). The text of a sentence or
  passage never reaches the browser before the learner answers.
- **Draft content** (not yet reviewed) is shown only to the owner and labelled "Bản nháp". The owner's review decisions are
  Bronze and never overwritten by an import.

**Evidence and mastery**
- One BKT observation per answer; a blank gives no evidence; aided answers (after a hint) count less than unaided ones;
  delayed re-checks and said-word scores never change mastery.
- Writing evidence moves a node only through the error map (`data/writing/error-map.yaml`); unmapped errors are shown but
  move nothing. AI corrections are labelled "gợi ý từ AI" and are never evidence.
- Pronunciation evidence has three outcomes: wrong (below the mark threshold, a competitor heard), right (above the accept
  threshold), inconclusive (moves nothing, shown "chưa chắc"). Marks per sound group exist only after thresholds are applied
  from Gold labels on at least 50 recordings.

**Scores shown to learners**
- A band is always a range, only from a model calibrated on examiner-banded essays, never from an LLM. No band for Task 1,
  and none for a Task 2 essay that is more than 15% repeated or memorised text. Feedback quotes must be exact substrings of
  the learner's text.
- Progress is measured by independent tests (`progress_tests`, touched only by `app/progress/`), never by NodeTrail's own
  estimates.

**Limits and cost**
- Daily limits per plan (`apps/api/app/plans.yaml`: free 3 essays and 6 model calls, pro 15 and 40, owner 100 and 300) and a
  service-wide daily cost cap (`LLM_DAILY_COST_CAP_USD`), checked before every model call; every call logged in `llm_calls`.
- Offline batches (question generation, blind checks, imports) run with an explicit cost cap per run.

**Privacy**
- A voice is personal data. Consent (`voice-v1`) before recording; owner only until a privacy review; recordings deleted
  after 24 hours unless kept; said words keep per-sound scores only, one attempt per recording. Only the owner's kept
  recordings may be played to a reviewer the owner chose, through the portal, after an explicit command.
- Writing sent to a model provider needs the consent notice. Private evaluation data (copyrighted essays, recordings,
  labels) stays in git-ignored `data/private/`; only metrics are committed.

### Who decides what is true
**The developer is not the ground truth** (`specs/validation/spec.md`). Gold (an expert or an expert-labelled dataset) for
gates; Silver (two independent checks agree) for learner-facing content; Bronze (one source) for development only. The owner
is learner, developer and tester, not the judge of correct English. Every label records its tier in `labels`.

**Sources:** the licence of every source is read from its own page and recorded; never NoDerivatives; NonCommercial and
ShareAlike flagged; no real exam passages or past papers.

## Interfaces
- **Web** (`apps/web`, Next.js, Vietnamese UI): `/`, `/ban-do`, `/kiem-tra`, `/lo-trinh`, `/on-tap/{kind}/{slug}`, `/hoc/{slug}`,
  `/tu-vung`, `/viet`, `/viet/{prompt}`, `/bai-viet/{id}`, `/phat-am`, `/doc`, `/doc/{slug}`, `/doc/{slug}/thi`, `/nghe`,
  `/nghe/{slug}`, `/nghe/bai/{slug}`, `/noi-duoi`, `/duyet-doc` (owner), `/kiem-duyet` (reviewers), `/gioi-thieu`; the contest's
  topic research at `/kham-pha`. The browser calls the API only through the server proxy `app/api/backend/[...path]`, which
  adds the API key and forwards an allow-listed set of query parameters.
- **API** (`apps/api`, FastAPI, every route except `/health` behind `X-API-Key`), by group: `/today`, `/maps`; `/level-tests`, `/roadmap`,
  `/milestones`, `/nodes`, `/grammar-runs`, `/rechecks`; `/vocab/*` (session, answers, say), `/phrases`; `/lessons`;
  `/writing/prompts` (and `/check`), `/writing/tests`, `/essays` (corrections, rewrites, patterns); `/recordings`, `/pronunciation/prompts`; `/reading/*`
  (texts, items, tests, review); `/listening/*` (texts, items, passages); `/shadowing/texts`; `/speech`; `/review/*` (reviewer
  token in `X-Reviewer-Token`); `/learners` creates a learner id. Contest-era groups (`/topics`, `/graph`, `/tutor`,
  `/placement`, `/next-item`, `/reviews/due`, `/exam-plan`, `/ask`, `/uploads`, `/code`) remain for other subjects; 79 paths in
  all on 20 Nov 2026.
- **Services** (`docker-compose.yml`): db, migrate, api, worker, sandbox, runner, web; opt-in profiles `writing`
  (LanguageTool), `scoring` (band model), `speech` (Piper voice), `pronunciation` (phone recogniser), `tei` (embeddings).

## Non-functional
- Vietnamese-first UI and explanations; the English being learned is shown and heard in English. UTF-8, NFC.
- Every explanation traceable to a source chunk; every source's licence recorded; no NoDerivatives sources.
- Runs on the owner's laptop (8 GB, a 4 GB Docker VM): heavy services are opt-in profiles, one at a time; heavy batch work
  (embedding, fine-tuning) runs on free GPU notebooks.
- Learner data private by default.

## Other subjects: frozen
NodeTrail began as a tutor for any subject: Deep Research on open textbooks, courses for Python and statistics, uploads. That
engine is still in the code and still passes CI, but it is **frozen** (owner's decision, 21 Nov 2026): no feature, fix beyond
keeping CI green, or plan touches it before the owner's exam. The exact frozen paths are in `AGENTS.md` ("English only"). Its
contest routes (listed under Interfaces) are not part of the English product. Uploads sent to model providers were allowed for the 2026 contest demo only and are not
offered to real learners without a privacy review. History: `docs/archive/contest-2026/`.

## Non-goals (for now)
- Gamified streaks or speed rewards.
- Content without a trusted, licence-checked source.
- A band from a model alone, or a band shown as a point.
- Real exam passages or past papers (copyrighted).
- A native-like or accent score; marking free-speech pronunciation.
- A mobile app (the web app works on a phone), payment, login (until testers need it).
