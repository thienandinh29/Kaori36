# Research: experiments on NodeTrail

Part of the master roadmap (`docs/v2/plan-english-pack.md`, "Research tracks"). One YAML file per experiment in
`experiments/`. Results and baselines go in `evals/baselines/`, and reports in `research/reports/` once there is
something to report. The code lives in the app (`apps/api/app/evalkit/`, `app/engine/`), so an experiment is
reproducible from the repository and a data version.

## Rules
- **Hypothesis first.** Each experiment states what would count as support, and what would not, before looking at the
  test data.
- **Split by time** for anything learned from a learner's history: train on earlier answers, test on later ones,
  never the reverse.
- **Separate data.** `learner_data` is the owner's own learning; `evaluation_data` is benchmarks. A held-out benchmark
  is never used for tuning.
- **Tier of the labels.** Every result names the tier its labels come from (Gold, Silver, Bronze; see
  `specs/validation/spec.md`). A Bronze-labelled result is a development check, not evidence.
- **N-of-1.** Results from the owner's own data are a single-learner case study, and the report says so.
- **Negative results are kept.** An experiment that fails its hypothesis stays in the registry with the numbers.

## Status values
`planned` → `collecting` (data accruing) → `running` → `done` (report written) or `stopped` (with the reason).

## Registry
| Id | Question | Status |
|---|---|---|
| KT-001 | Does BKT predict the next answer better than simple baselines? | planned |
| FORGET-001 | What is forgotten after about a week, and does the model know? | planned |
| VER-001 | How reliable and costly is the generated-content pipeline? | planned |
