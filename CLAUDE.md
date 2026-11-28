@AGENTS.md
@PLAN.md
@SPEC.md

# Claude Code on NodeTrail

The rules for every agent are in `AGENTS.md` (how we work), `SPEC.md` (what the product does and the rules the code keeps)
and `PLAN.md` (where we are, what is next); all three load above. `MAP.md` (where each module, page and migration is) is
not loaded: read it when you need a path, and update it when you add one. This file adds only what is specific to Claude Code. **Work only on the English app:** the frozen paths are in
`AGENTS.md`, "English only"; never build on them or propose work on them. If anything here disagrees with `AGENTS.md`, `AGENTS.md` wins; say so and fix one of them.

## Skills
- `/verify`: every lint, type check and test for the API and the web app. Run it before saying anything is done; for a
  change the learner can see, also rebuild the stack and run Playwright (`AGENTS.md`, "Checks").
- `/speckit-specify`, `/speckit-plan`, `/speckit-tasks`: a new feature's spec, plan and tasks, one page each, before code.

## In a cloud session
- The repository is `thienandinh29/projectQ` (shown on GitHub as Kaori36), checked out at `/home/user/projectQ`.
- If Docker is not running, start it with `nohup dockerd >/tmp/dockerd.log 2>&1 &`. When the disk fills, free the build
  cache with `docker builder prune -af` before anything else.
- Model calls from the sandbox go through the proxy, which injects the keys: `LLM_USE_ENV_PROXY=1` with placeholder keys
  (for example `DEEPSEEK_API_KEY=proxy-injected`). Never ask for a key in chat.
- Wikimedia refuses the sandbox (HTTP 429): Simple English Wikipedia is fetched on the owner's laptop.
- When the owner says "merge it when CI is green": push, open the pull request, schedule one check about 8–10 minutes later,
  and squash-merge with the full head SHA as the expected SHA once all 18 checks pass (16 before the `asr` job, step 5.1). Do not poll in a loop.
- The daily Reading blind-check task (19–28 Nov 2026) is turned off: the bank is checked (`step-4.2e.md`, T5). New questions
  are checked with `python -m app.reading.pipeline --no-generate --max-checks 45 --max-cost 0.10` when needed.

## Writing for the owner
Reply in the owner's language with the reasoning behind each decision. Lead with the outcome, then what to do next. Name
what was not done or not checked. Never write a model identifier into the repository.

## Start here
`HANDOFF.md` (loaded below) says where the work stands and what comes next; update it at the end of every session or merged
pull request. `GOAL.md` is the goal in one page; `lessons.md` holds the mistakes not to repeat (read it before a pipeline,
import or evidence change, and add an entry in the change that fixes a mistake).

@HANDOFF.md
