# AGENTS.md: how to work on NodeTrail

The working agreement for any coding agent (Claude Code, Codex, others) and for people joining. It says **how** we work.
**What** the product must do is in `SPEC.md`; **where we are and what comes next** is in `PLAN.md`; **where things are** is
in `MAP.md`. If these files disagree with each other, say so and ask; do not pick one silently.

## The project in one paragraph
NodeTrail is an English (IELTS) learning app for Vietnamese learners, A1–C1, all four skills. One owner (a student and aspiring
ML engineer) builds it with an AI coding agent. The owner is also the first learner: IELTS in summer 2027, target 7.0 overall.
It is one codebase with three kinds of value, in this order: the owner improves with it; the improvement is measured
independently; the data improves the algorithms; the research becomes a portfolio. NodeTrail began as a contest build for any
subject (team repo `thienandinh29/SenaEmpire36`, frozen after 8 Nov 2026); that engine stays in the code for other subjects later.
Mascot: **Sena** the monkey.

## Read first, in this order
1. `PLAN.md`: the current phase, what is next, what waits on the owner.
2. `SPEC.md`: what the product does and the rules the code keeps (the contract).
3. The spec of the feature you touch: `specs/<feature>/spec.md`, `plan.md`, `tasks.md`, and its `step-*.md` pages.
4. `MAP.md` for paths; `dolater.md` for the owner's open work. `docs/archive/contest-2026/` is history only: its lanes,
   timeline and freeze rules no longer apply.

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
8. **Push and open a pull request only when the owner says so.** CI must be green (8 jobs, each on push and on the pull
   request: 16 checks). Squash-merge with the expected head SHA, so nothing lands that CI did not see. Delete nothing on
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

## Architecture rules (the code keeps these; do not work around them)
- **The LLM is not the decision maker.** The learning engine decides what to learn next: BKT for mastery, rules over the
  graphs for placement and remediation, FSRS for review, the recommendation engine for "Hôm nay". These are pure functions
  in `apps/api/app/engine/`, unit-tested, and every decision returns a `DecisionTrace` (shown as "Vì sao?").
- **Graders score work objectively:** answer keys, typed answers exact after normalisation, LanguageTool and ERRANT,
  a pinned band model shown only as a range, phone recognition and GOP. A model's opinion is never a grade.
- **LLM calls go only through `apps/api/app/llm/gateway.py`** with `routing.yaml` (task × tier → ordered models). Never
  call a model SDK or HTTP API from a feature. Every call is budgeted and logged in `llm_calls`.
- **Generated content is verified by a different model family**, answering blind from the cited text only; the gateway
  refuses a checker of the generator's family. Unverified content is never served. The gate reduces errors; it does not
  remove them, so catch rates are measured.
- **No long work inside a request.** Use the Postgres `topic_jobs` queue and the separate worker.
- **The Socratic tutor never hands over the answer.** Sena praises real mastery only, never speed or streaks.

## Who decides what is true (validation)
**The developer is not the ground truth** (`specs/validation/spec.md`). Every label and gate result records its tier:
- **Gold:** an expert (English teacher, trained IELTS rater, phonetics expert) or an expert-labelled dataset. Gates need Gold.
- **Silver:** at least two independent checks agree (a licence-checked source, code checks, a blind checker of another
  family). Learner-facing content needs Silver.
- **Bronze:** one source (a model, the owner, an extraction). Development only.

The owner's judgement on correct English is learner feedback or Bronze; **nothing is promoted by the owner's approval
alone**. Never write "the owner labels/confirms" as a gate's truth in a new spec. NodeTrail never grades its own effect:
progress is measured by independent tests every 4 weeks (`app/progress/`), kept apart from learner data.

## Data, privacy and sources
- **Secrets only in `.env`.** Never read it, print it, commit it or paste a key in chat. Document every new variable in
  `.env.example`. In the cloud sandbox, model keys are injected by the proxy (`LLM_USE_ENV_PROXY=1` with placeholder keys).
- **A voice is personal data.** Recording is owner-only until a privacy review; audio is deleted after analysis unless the
  owner keeps it; only per-sound scores are stored for said words. Nobody else's voice is ever served.
- **Private evaluation data** (copyrighted essays, recordings, labels) stays in git-ignored `data/private/`; commit only
  metrics and reports.
- **Sources:** record the licence of every source from its own page; never NoDerivatives; flag NonCommercial and
  ShareAlike. No real exam passages or past papers. Prefer structured sources (`apps/api/app/sources/`).
- **The owner's decisions in data are never overwritten** by code or by an import (for example Reading review decisions in
  `data/english/reading-items/`).

## Database
Migrations in `supabase/migrations/`, numbered in order (`0037` is the latest), **additive only**. Never edit a migration
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
