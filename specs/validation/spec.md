# Spec: the validation system (who decides what is true)

Status: approved by the owner 18 Nov 2026. **V1 built** (`step-v1.md`: labels, reviewers, tiers, backfill); **V2 built** (`step-v2.md`: the portal `/kiem-duyet` with Reading and text-level queues; pronunciation, vocabulary, grammar and bands in V2b); **V5 written** (`reviewer-brief.vi.md`); **V3 built** (`step-v3.md`: every gate report states its basis; Gold or construction needed); V4 not built. The owner agreed to the direction: NodeTrail is a learning system
and a validation system side by side. This page says how truth is established, which gates change, and what is
built. It is part of the master roadmap (`docs/v2/plan-english-pack.md`, "Principles").

## The principle
**The developer is not the ground truth.** The owner has three roles, and they need different expertise:

| Role | The owner does | The owner does not |
|---|---|---|
| Learner | Uses the app daily, makes mistakes, takes the independent tests | |
| Developer and tester | Builds, tests that things work, analyses the results, runs the experiments | |
| Reviewer of correct English | | Decide alone whether an answer key, an example sentence, a pronunciation or a band is correct |

As a learner, the owner gives a different, valuable signal: whether an explanation was clear, too hard, or assumed
something not yet taught. That is recorded as **learner feedback**, never as a correctness label.

## Tiers of trust
Every label, item and gate result records where its truth comes from:

| Tier | Comes from | May be used for |
|---|---|---|
| **Gold** | An expert: an English teacher, a trained IELTS rater, a phonetics expert. Or a dataset labelled by experts (speechocean762; candidates such as learner essays with CEFR and error annotations, to check licence first) | Benchmarks and gates; it decides |
| **Silver** | At least two independent checks agree: a licence-checked source or dictionary, code checks, a blind checker of another model family. Or a Gold reviewer's sample shows the process is reliable | Learner-facing content |
| **Bronze** | One source only: AI-generated, the owner's own judgement, automatic extraction | Development only; never a gate, never shown as fact |

A label only moves up with evidence. For example, Bronze becomes Silver when an independent check agrees, and Silver
becomes Gold when an expert confirms it. **Nothing is ever promoted by the owner's approval alone.**

## Storage (proposed migration)
One table, `labels`, so every kind of content uses the same rules:
- what is labelled: content type (reading item, grammar item, vocabulary entry, lesson, recording target, essay,
  text level) and its id;
- the label: right or wrong, a level, a band, a phone;
- the tier, and who gave it: their role (`expert_teacher`, `ielts_rater`, `phonetics_expert`, `owner_learner`,
  `owner_developer`, `model:<name>`, `source:<slug>`, `code_check`) and a reviewer id;
- the time, and an optional note.

A reviewer is stored with their role and the expertise they declare: for example, years teaching, or IELTS rater
training. No personal data beyond a display name, and they consent to how their labels are used. A content item's
effective tier is computed from its labels (the rules above). The existing status fields stay as they are.

## The reviewer portal
For outside reviewers who never see the code:
- **Access:** a link with a personal reviewer token. No account is needed. Each reviewer sees only the content types
  of their role, in Vietnamese or English.
- **What they see:** one item at a time, with what a reviewer needs (the passage and question, the sentence and
  error, the audio segment) and a few clear choices, plus "not sure".
- **No scores and no other labels are shown while labelling,** so they cannot sway the reviewer.
- **Sampling:** the portal serves stratified samples, not everything. For example, 50 Reading items: all the checker
  disagreed on, plus a random share of the ones it agreed on. That measures the process without reviewing every item.
- `/duyet-doc` (CP3) becomes one view of the portal. The owner's decisions there are recorded as `owner_developer`,
  Bronze.

## Which gates change
| Gate | Before (owner as truth) | Now |
|---|---|---|
| Pronunciation ≤ 10% false alarms (3.3b) | The owner labels own recordings by ear | A phonetics-trained reviewer, or an English teacher, labels the target sounds (Gold). The owner records and checks that the recording pipeline works. speechocean762 (Gold) stays the public benchmark |
| Reading checker agreement, kappa (CP3) | Owner against the checker | An expert against the checker, on a stratified 50 (VER-001) |
| Reading planted-error test (CP2b) | The owner confirms the faults | The faults are planted by construction (wrong key: Gold by design); "two defensible answers" faults need an expert's confirmation |
| Text CEFR levels (CP1) | The owner labels 30 texts | A teacher labels them (Gold). The owner's labels are kept as learner feedback ("how hard did it feel") |
| Grammar items, lessons, vocabulary sample | "The owner reviews" | A teacher reviews a stratified sample. Items pass as Silver through source, code checks and the blind checker. The owner flags anything unclear |
| Writing band and error mapping | Already examiner-banded essays (Gold) for the scorer; owner-checked error mapping | Bands unchanged (Gold). The 100-error mapping check goes to a teacher |
| Two-map links | The owner checks the links | A teacher checks a sample of links; until then the links are Bronze and the engine labels them "đề xuất" |
| Progress | NodeTrail's own BKT | Independent tests every 4 weeks: official sample papers under exam conditions, or a mock with a trained rater (Gold). BKT is compared against them, never used as proof |

## What the owner does
- Finds the reviewers. This is the one job only the owner can do:
  - one English teacher (grammar, vocabulary, Reading, text levels);
  - one person with IELTS rating experience (Writing and Speaking bands);
  - optionally a phonetics-trained teacher (pronunciation);
  - 3–5 testers.

  Friends, lecturers or English-major students are fine for teacher-level checks. Bands need trained raters.
- Learns with the app, tests it, and records learner feedback.
- Takes the independent tests on schedule.

## What is built (steps, each a PR, after approval)
| Step | Work |
|---|---|
| V1 | The `labels` table and reviewers (migration), tier computation (pure, tested); existing owner decisions back-filled as `owner_developer` Bronze |
| V2 | The reviewer portal: token links, role-based queues, stratified sampling, "not sure", Vietnamese/English; `/duyet-doc` becomes a view of it |
| V3 | Gates read tiers: each gate report states its tier, and refuses to report a Gold gate without enough Gold labels |
| V4 | The progress study: a schedule of independent tests, result entry, comparison with NodeTrail's own estimates |
| V5 | A one-page brief for reviewers in Vietnamese: what NodeTrail is, what they label, how long it takes, how their labels are used |

## Not in this spec
Paying reviewers (a decision for the owner), accounts and logins for learners, exam-board data of any kind.
