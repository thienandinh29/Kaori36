# Spec: plans (free, pro, owner) and their daily limits

The owner's request (16 Nov 2026): free learners get a daily limit, paying learners more. Payment and login do not exist
yet (a learner is an id in the browser), so this step builds only the server-side mechanism they will plug into.

## Plans
- `free` (default for everyone), `pro` (set by the owner by hand for now; later by a payment), `owner`.
- **`owner` is never stored:** a learner is the owner when their id is in `DRAFT_ITEM_LEARNERS` (the owner's list).
- The plan is decided by the server only; nothing the browser sends can change it.
- Named "plan", not "tier": `tier` already means the model routing tier (free or pro model) in `app/llm/routing.yaml`.

## Limits (`apps/api/app/plans.yaml`)
| Plan | Essays a day | Model calls a day (feedback, corrections, rewrites) |
|---|---|---|
| free | 3 | 6 |
| pro | 15 | 40 |
| owner | 100 | 300 |
`WRITING_DAILY_ESSAYS` and `LLM_DAILY_CALLS_PER_LEARNER`, **when set in `.env`**, override the free plan's numbers (as before).
`LLM_DAILY_COST_CAP_USD` stays one cap for the whole service, whatever the plan: it protects the owner's money.

## Storage and tools
- Migration `0019_learner_plans.sql` (additive): `learners.plan` text, default `free`, only `free` or `pro`.
- `python -m app.services.plans show <learner_id>` and `set <learner_id> free|pro` (the owner's tool until payment exists).
- The essay limit message names the plan ("…3 bài (gói Miễn phí)…").

## Not in this step
Login, payment (MoMo/ZaloPay/VNPay), showing plans in the web, a pro-only model, terms of service. The privacy review in
`SPEC.md` comes before anyone pays.

## Acceptance
Unit tests: plan resolution (owner by list, stored plan, unknown learner), limits per plan, the `.env` override only when
set, the YAML checked on load. With the database: the essay limit follows the plan (free blocked at 3, pro and owner not),
the model-call limit follows the plan, the CLI sets and shows a plan and refuses `owner` and unknown plans.
