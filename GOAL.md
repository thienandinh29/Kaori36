# GOAL — NodeTrail

The overall goal and the mission, in one page. It changes rarely. The detail lives elsewhere and wins if this page drifts:
the plan and its gates in `PLAN.md`, the product and its rules in `SPEC.md`, how we work in `AGENTS.md`.

## Mission
An English (IELTS) learning app for Vietnamese learners, A1–C1, all four skills: *knows where you are, and leads you onward.*
One owner builds it with an AI coding agent, and is also its first learner.

## The goal, in a fixed order of priority
1. **Learning.** The owner reaches **IELTS 7.0 overall** in summer 2027 (exam assumed 1 Jul 2027 until the owner sets a date).
   Then friends and family use it free.
2. **Measured independently.** Progress comes from independent tests every 4 weeks (`app.progress.cli`), never from
   NodeTrail's own estimates.
3. **Better algorithms from the data.** Knowledge tracing (KT-001), forgetting (FORGET-001), reliable generated content
   (VER-001), pronunciation (PRON-001), in `research/`.
4. **A portfolio** for ML engineer, AI engineer and data science roles: case studies with hypothesis, method, results and
   limits, negative results kept.

When two of these conflict, the higher one wins. The exam comes first: if building eats study time, stop at the nearest gate.

## What "done" means
| By | Done when |
|---|---|
| 31 Dec 2026 | NodeTrail is the owner's daily study tool; a baseline on four skills is recorded from an independent test |
| Feb 2027 | A first ML case study with real data (KT-001 or FORGET-001) |
| Apr 2027 | Two more case studies with evidence; Speaking (phase 5) built |
| Jun 2027 | Exam readiness measured by independent mock tests, not guessed |
| Summer 2027 | The exam taken and its result recorded; the portfolio published, gaps and negative results included |

Each product phase ends only when its gate is measured with labels of the tier the gate names (`PLAN.md`, "Product phases").

## Constraints
- **Time:** 30–40 hours a week; about 65% learning with NodeTrail, 25% building and research, 10% writing up.
- **Machine:** the owner's laptop (8 GB, a 4 GB Docker VM); heavy work on free GPU notebooks.
- **Money:** model calls under per-run and daily caps; free checker models where they are good enough.
- **Truth:** the developer is not the ground truth. Gates need Gold labels (a teacher, a trained rater, an expert dataset).

## Not the goal (before the exam)
- Anything outside the English app: the contest's any-subject engine is frozen (`AGENTS.md`, "English only").
- A Speaking band; a band shown as a point or from an LLM alone.
- Streaks or speed rewards, payment, login, a mobile app, real exam passages in the shared bank.
- Deep knowledge tracing, a home-made LLM or a band model trained from scratch: there is not enough data.
