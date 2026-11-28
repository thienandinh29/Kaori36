# AGENTS.md: how to work on NodeTrail

The working agreement for any coding agent (Claude Code, Codex, others) and for people joining. It says **how** we work.
**What** the product must do is in `SPEC.md`; **where we are and what comes next** is in `PLAN.md`; **where things are** is
in `MAP.md`. If these files disagree with each other, say so and ask; do not pick one silently.

## The project in one paragraph
NodeTrail is an English (IELTS) learning app for Vietnamese learners, A1–C1, all four skills. One owner (a student and aspiring
ML engineer) builds it with an AI coding agent. The owner is also the first learner: IELTS in summer 2027, target 7.0 overall.
It is one codebase with three kinds of value, in this order: the owner improves with it; the improvement is measured
independently; the data improves the algorithms; the research becomes a portfolio. NodeTrail began as a contest build for any
subject (team repo `thienandinh29/SenaEmpire36`, frozen after 8 Nov 2026); that engine stays in the code but is frozen
(see "English only" below).
Mascot: **Sena** the monkey.

## Read first, in this order
0. `HANDOFF.md`: where the work stands right now and the next step; `GOAL.md` (the goal in one page) and `lessons.md` (mistakes
   not to repeat) once, then when relevant.
1. `PLAN.md`: the current phase, what is next, what waits on the owner.
2. `SPEC.md`: what the product does and the rules the code keeps (the contract).
3. The spec of the feature you touch: `specs/<feature>/spec.md`, `plan.md`, `tasks.md`, and its `step-*.md` pages.
4. `MAP.md` for paths (read on demand, not loaded every session); `dolater.md` for the owner's open work. Many `MAP.md`
   rows describe frozen contest code: check the list below before using one.

## English only: what is frozen (owner's decision, 21 Nov 2026)
All work is on the English (IELTS) app. The contest's any-subject engine stays in the repository and keeps passing CI, but
it is **frozen**: do not build on it, extend it, refactor it, read it for ideas, propose work on it, or wire English features
into it. If an English task seems to need something frozen, stop and ask the owner; do not quietly reuse it.

**Frozen** (touch only to keep CI green after a change elsewhere, with the smallest fix):
- **Deep Research and the topic flow:** `apps/api/app/research/`, `app/uploads/`, `app/content/`, `app/tutor/`, `app/rag/`,
  `app/guardrails/`; services `topics.py`, `topic_readiness.py`, `indexing.py`, `graph_confirmation.py`,
  `learner_sessions.py`; routes `/topics`, `/graph`, `/placement`, `/next-item`, `/reviews/due`, `/exam-plan`, `/ask`,
  `/uploads`, `/tutor/hint`; the `tei` compose profile and embeddings.
- **Code practice:** `runner/`, `apps/api/app/graders/code.py`, `app/services/code_practice.py`, `/code/*`.
- **The web's topic explorer:** `apps/web/app/kham-pha/`, `components/workspace.tsx`, `knowledge-map.tsx`, `use-learning.ts`,
  `source-link.tsx`, `trace-panel.tsx`, `async-state.tsx`; `lib/data-client.ts`, `mock.ts`, `fixtures.ts`,
  `api.generated.ts`, `layout.ts`.
- **Other subjects' data:** `data/courses/python-basics.yaml`, `statistics-intro.yaml`, `ielts-academic-writing.yaml` (an
  old contest course spec; the English writing feature does not use it), `data/golden/`, `data/guardrails/`, `data/eval/`,
  `data/kg/`, `data/raw/`; the library manifests in `data/sources/` other than `english-candidates.yaml`.
- **Contest specs:** `specs/code-sandbox/`, `contracts/`, `deep-research-integration/`, `graph-confirmation/`,
  `graph-confirmation-contract/`, `guardrails/`, `integration/`, `library/`, `model-test/`, `next-item/`,
  `p2-graph-confirmation/`, `p2-integration/`, `p2-local/`, `p3-integration/`, `retrieval/`, `topic-metrics/`.
- **History, not instructions:** `docs/archive/contest-2026/`, `docs/v2/plan-m0-m1.md`, `docs/v2/plan-to-tet-2027.md`,
  `docs/v2/plan-english-pack.md`, `context/product-brief.vi.md` (the any-subject brief). A plan or brief there never
  overrides `PLAN.md`.
- **Other subjects:** maths, Python, statistics, uploads for learners. Not planned before the owner's exam.

**Shared, so active, but changed only for English needs:** `apps/api/app/engine/` (BKT, FSRS, the graphs, milestones,
recommendation), `app/llm/` (the gateway), `app/jobs/` (the worker), `app/sources/` (OpenStax parsing for Reading texts),
`app/curriculum/` (the English courses), `app/evalkit/`, `app/validation/`, `app/graders/` except `code.py`,
`apps/web/lib/contracts.ts` and `lib/decode.ts`.

## The working agreement
- **The owner decides; the agent proposes.** When a choice is the owner's (scope, order, a dependency, a source, a
  threshold that changes what learners see), give a recommendation with the reason and the cost, then wait. "Start X",
  "alright" or "go" is the go-ahead for the step just proposed, not for the next one.
- **Ask before** pushing, opening or merging a pull request, adding a dependency, deleting data, changing a migration's
  meaning, spending money on model calls beyond a stated cap, or making an architectural change. Approval for one step does
  not carry over to the next. "Merge it when CI is green" covers that one pull request.
- **Reply in the owner's language** (English or Vietnamese), with the reasoning behind decisions. Short, plain, numbers
  with their uncertainty. Say what you did not do or could not check.
- **Report honestly.** Failing tests are reported with their output. A skipped step is named. A number from simulated or
  synthetic data is called that. Never present sample data as real.
- **The owner's research is input, not truth.** A deep-research report the owner shares is Bronze: read it, say what you
  agree and disagree with, and put agreed changes into the existing documents (spec, plan, `dolater.md`), not into new files.
- **If the owner cannot explain a piece of code the agent wrote, the agent explains it before the merge.**

## How a change is made
1. **Branch** from the latest `main`: `feat/…`, `fix/…`, `docs/…`, or `data/…`. Never commit to `main`; never force push.
2. **Spec first** for a new route, contract field, table or module: a one-page `specs/<feature>/step-x.y.md` (what, why,
   what is measured, what is not claimed), or Spec Kit (`/speckit-specify` → `/speckit-plan` → `/speckit-tasks`) for a new
   feature. Bug fixes and small changes inside an existing spec are exempt; add a short "Fix" note to that spec instead.
3. **Build in small steps** with tests: pure functions for decisions, unit tests for every rule, an API test against a real
   database, Vitest for web logic, and a Playwright test for any user-visible flow.
4. **Run it for real** before calling it done: the stack, the page in a phone-size browser, a real model call where the step
   needs one (with a cost cap). Each step must run for real before the next one starts.
5. **Run every check** (below). Web behaviour changed → rebuild the stack and run Playwright too: CI runs it, and a change
   that passes Vitest alone has failed there before.
6. **Update the documents in the same change:**
   - `PLAN.md`: the Status column and the Log, when work lands or a decision is made;
   - `MAP.md`: a row for a new module, page, route group or migration;
   - the feature's `tasks.md` and step page;
   - `dolater.md`: when the step adds work only the owner can do;
   - `README.md` (Vietnamese, public): when a skill's status changes.
7. **Commit** with a message in English that says what changed and why. End it with the attribution lines your tool asks for.
8. **Push and open a pull request only when the owner says so.** CI must be green (9 jobs, each on push and on the pull
   request: 18 checks). Squash-merge with the expected head SHA, so nothing lands that CI did not see. Delete nothing on
   the way.

## Checks (all must pass before "done")
From `apps/api` (needs the database: `docker compose up -d --wait db`, port 54322):
```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy . && uv run pytest -q
```
From `apps/web`:
```bash
pnpm typecheck && pnpm lint && pnpm format:check && pnpm test
```
The whole stack and the browser tests (from the repository root, then `apps/web`), with test-only secrets:
```bash
export API_KEY=ci-only-api-key-0123456789 RUNNER_TOKEN=ci-only-runner-token-0123456789 DRAFT_ITEM_LEARNERS=00000000-0000-4000-8000-0000000e2e01 COMPOSE_PROFILES=writing LANGUAGETOOL_URL=http://languagetool:8010 TTS_URL=
docker compose up -d --build --wait && bash scripts/stack-smoke.sh
```
```bash
E2E_LEARNER_ID=00000000-0000-4000-8000-0000000e2e01 LANGUAGETOOL_URL=http://languagetool:8010 npx --no-install playwright test --trace off
```
CI (`.github/workflows/ci.yml`) also runs the evaluation gates (placement, the English level test, the recommendation
engine) against committed baselines in `evals/baselines/`, the sandbox escape tests, the grader self-test, and builds the
scorer, voice and pronunciation images. A gate that drops below its baseline fails CI; raise a baseline only with the owner. CI does not run Prettier; run `pnpm format:check` yourself.

## The product's rules
`SPEC.md`, "Contract", is the one list of the rules the code keeps: the engine decides and the LLM explains, every model call
goes through the gateway, a different model family verifies generated content, what may be served, what counts as evidence,
how scores are shown, limits and cost, voice privacy, who decides what is true (Gold, Silver, Bronze), sources and licences.
Read it before touching any of these; never work around one of them. A change to a rule is the owner's decision, made in
`SPEC.md` first.

Two rules about how you work, not what the product does:
- **Secrets only in `.env`.** Never read it, print it, commit it or paste a key in chat. Document every new variable in
  `.env.example`.
- **The developer is not the ground truth.** Never write "the owner labels/confirms" as a gate's truth in a spec or a
  report; the owner's judgement on correct English is learner feedback or Bronze.

## Database
Migrations in `supabase/migrations/`, numbered in order (`0050` is the latest), **additive only**. Never edit a migration
that has been merged. Tests make a throwaway migrated database per run (`apps/api/tests/conftest.py`); they never touch
development data.

## Language rules
- Code, identifiers, comments, commit messages and developer docs: **English**.
- Everything a learner sees (UI text, Sena, feedback, explanations): **Vietnamese**, in the i18n files
  (`apps/web/messages/`, `vi` default, `en` secondary), never hard-coded. The English being learned is shown and heard in
  English.
- UTF-8 everywhere, NFC normalisation, diacritic-aware search and tokenisation.

## Code conventions
- Python 3.12: full type hints; ruff (lint and format), mypy and pytest clean. Small modules; algorithms as pure functions.
- TypeScript: `strict`, no `any`; ESLint, Prettier, Vitest; Playwright tests at phone size in `apps/web/e2e/`.
- Pin what you depend on: model weights and images by SHA-256, packages by lockfile (`uv.lock`, `pnpm-lock.yaml`; pnpm 10.20 as in CI).
- Measurements committed as JSON baselines with intervals (`evals/baselines/`), produced by a command anyone can rerun.

## Running out of room or time
If a task grows beyond what was agreed, stop and propose a cut (what to keep, what to move to the plan) instead of
extending it. The exam comes first: if the project eats study time, stop at the nearest gate.
