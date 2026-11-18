# Plan: Listening and Reading (phase 4), with checkpoints

Written 18 Nov 2026, before any phase 4 code beyond 4.1 and 4.2a. **Nothing moves past a checkpoint until the owner says so.**
Each checkpoint lists what is built and what is measured, the owner's part, and what it costs. The spec (`spec.md`) stays the
"what"; this file is the "how and in what order".

**Owner's decisions (18 Nov 2026):** the plan is approved as written. The text sources are Simple English Wikipedia
(A2–B1) and OpenStax (B2–C1). The reuse of the NGSL word list, free Ernie as checker (`reading_check`), the Piper
voice and DeepSeek as generator is approved with the plan.

## Where things stand
- **Built:**
  - 4.1, the text bank (`app/texts/`): texts tied to a verified source, with level features. It ships no texts.
  - 4.2a, the question types (`app/reading/items.py`): T/F/NG, multiple choice, completion and headings; code checks
    against the passage; grading from the key; only `approved` items are served.
- **No text source is verified yet.** `simple-wikipedia` is "to check". VOA Learning English, Wikinews and OpenStax are
  not in the candidates file yet.

## Decisions already made elsewhere (proposed for reuse, so they are not asked again)
| Open question in `tasks.md` | Proposed answer | Why |
|---|---|---|
| Licensed word list for text levels | NGSL/NAWL import (`data-sa/`, CC BY-SA 4.0, 3,533 words, levels from frequency) | Already verified and loaded. The A1–B1 set is the "known words" for the feature. No CEFR claim beyond the owner's 30 labels |
| Verifier of a different family | Free Ernie, dots as backup, through a new gateway task `reading_check` (public texts only, like `lesson_check`) | Passed the 40-item planted test (20/20, 0/20). Reading texts and questions are public, never learner data. Its own planted test on reading items comes first (CP2) |
| Audio | The self-hosted Piper voice already running (`en_GB-cori-high`, the owner's S2 choice), labelled "giọng đọc máy" | No new dependency or licence. Real recordings later, if an open source fits |
| Generator | DeepSeek through the gateway (key already set), budgeted per day | As in vocabulary and writing |

## Checkpoints
| CP | Step | What is built | What is measured | Owner's part | Cost |
|---|---|---|---|---|---|
| **CP0** | Decisions | This plan | — | Approve the plan; choose the text sources (see below) | — |
| **CP1** | 4.1b: first texts | A fetch script for the chosen source (licence and URL recorded per text); 30 texts, A2–B2, 150–600 words, in `data/english/texts/` | Level features per text; refusals | Read the source's licence page and mark it `verified`; label the 30 texts with a CEFR level (about 1 h) | Free |
| **CP2** | 4.2b: generation and blind check | Migration (reading items, status, review); worker job that generates 4–6 items per text, runs code checks, then the blind check (`reading_check`); items stay `needs_review` until the owner approves | **Planted-error test**: 50 items with planted faults (wrong key, answer not in the passage, two defensible answers) plus 50 good ones, caught and false-alarm rates with exact intervals. Bar: caught ≥ 45/50, false alarms ≤ 5/50 | Look over the planted set (I draft it from real generated items; you confirm each fault is real, about 1 h) | DeepSeek under US$1; about 100 free checks (2 days of the free limit) |
| **CP3** | 4.2c: review queue | An owner-only page: each item with its passage, the deciding sentence highlighted, the checker's answer; approve, reject or edit (an edit sends it back through the checks) | Share approved without edits; **agreement with the checker on 50 items, Cohen's kappa** (gate 2) | Review at least 50 items (about 5 h at 10 an hour) | Free |
| **CP4** | 4.3: Reading practice | Learner page `/doc`: a text, then questions one type at a time; right or wrong from the key; the deciding sentence highlighted; a Vietnamese explanation from that sentence (generated, checked). A course `english-reading` (one milestone, one node per skill: detail, main idea, inference, writer's view, skimming), like pronunciation's own course; BKT evidence per answer | End-to-end browser test; evidence moves only the answered skill's node | Try it; say what feels wrong | DeepSeek explanations under US$1 |
| **CP5** | 4.4: Listening | Audio per text from the Piper service, cached; the same approved items on audio (played once or twice); dictation and gap-fill from the text's own sentences, graded exactly after normalisation; course `english-listening` | Browser test; audio size and time per text | Listen to 5 texts; decide whether the machine voice is good enough to keep | Free |
| **CP6** | 4.5: gate report | `docs/v2/reading-listening-eval.md` with every number: catch rate, false alarms, kappa, bank size per type and level, how the features track your CEFR labels | — | Read and accept, or say what is missing | — |

Each checkpoint is one PR (CP2 may be two: the migration and job, then the test), merged only when its CI is green and you
approve. A checkpoint that misses its bar stops the plan there and comes back to you with the numbers and options.

## The text source (the one decision for CP0)
| Source | Licence (to be read on its own page) | Fit |
|---|---|---|
| Simple English Wikipedia | CC BY-SA 4.0 (and GFDL) | Plain English at A2–B1, any topic. ShareAlike: the bank must be shared alike (fine for a free tool) |
| Wikinews | CC BY 2.5 | News style, closer to IELTS passages; fewer texts, uneven quality |
| VOA Learning English | US government work, mostly public domain, but some content is credited to others (wire photos, AP) | Graded news written for learners (levels 1–2), with real audio. Terms must be read and each text checked for third-party credits |
| OpenStax (textbooks) | **CC BY-NC-SA 4.0** in each book's own metadata (checked 18 Nov on 17 collections: biology, psychology, sociology, astronomy, US and world history, economics, philosophy, government, anatomy, college success, writing guide). Not CC BY, as first written here | Academic, B2–C1, close to IELTS Academic Reading. NonCommercial and ShareAlike: flagged per text, and blocks a paid tier for these texts |

**My first recommendation was Simple English Wikipedia for A2–B1 and OpenStax for B2–C1.** Two corrections found when CP1
started (18 Nov):
- OpenStax's IELTS-like books are NonCommercial and ShareAlike, not CC BY.
- Simple English Wikipedia answers this cloud sandbox with HTTP 429 (Wikimedia rate-limits its shared address), so its
  fetch must run on the owner's laptop. VOA is attractive for its real audio, but
its terms need the most care; it can come in at CP5 if you want real recordings.

## Risks and how the plan handles them
- **The free checker's limits** (50 requests a day, a preview model). The planted test runs first (CP2); the job paces itself
  and stops for the day at the limit. If Ernie fails the bar on reading items, dots is tried; if both fail, we stop at CP2.
- **Questions answerable without the text.** The checker sees only the passage. A second check without the passage is
  possible later if the planted test shows outside knowledge leaking through.
- **Owner time:** about 1 h at CP1, 1 h at CP2, 5 h at CP3, then about 10 items an hour for a larger bank (200 items is about
  20 h).
- **ShareAlike:** a bank built on Simple English Wikipedia is CC BY-SA. That matters only before a paid tier, and it is
  recorded per text.
- **Not in this phase:** Speaking, a Reading or Listening band, real exam passages, map and diagram labelling.

## CP1 status (18 Nov 2026): built, waiting on the owner
- **Built:**
  - `data/english/text-picks.yaml`: 20 Simple English Wikipedia titles on IELTS themes, plus 3 OpenStax books for 10
    texts.
  - `app/texts/fetch.py`: whole prose paragraphs, 150–600 words; figure captions and empty "()" references removed.
    - Simple Wikipedia: the exact revision is recorded, one request a second, a generic User-Agent.
    - OpenStax: one section per chapter, pinned to the commit.
  - `app/texts/levels.py`: a labelling sheet, and the Spearman correlation of each feature with the owner's labels.
  - The candidate `openstax-reading`, as `to_check`.
- **Fetched here:** the 10 OpenStax texts, into git-ignored `data/private/english-texts/`. Their features: mean
  sentence 15–27 words, 12–19% of words outside the A1–B1 forms.
- **Owner's steps** (all from `apps/api`):
  1. Read each licence page:
     - Simple English Wikipedia's licence page;
     - each OpenStax book's page on openstax.org.

     If they match, set `simple-wikipedia` and `openstax-reading` to `verified` in
     `data/sources/english-candidates.yaml`, with `checked_on` and `licence_page`.
  2. On the laptop (Wikimedia refuses the cloud sandbox): `uv run python -m app.texts.fetch simple-wiki`, then
     `uv run python -m app.texts.fetch openstax`.
  3. Check that the bank admits them: `uv run python -m app.texts.bank ../../data/private/english-texts`. Then move
     them to `data/english/texts/` and commit.
  4. Label them: `uv run python -m app.texts.levels sheet --out ../../data/private/levels.csv`. Fill the `level`
     column (A1–C1, about 1 h for 30 texts), then
     `uv run python -m app.texts.levels score ../../data/private/levels.csv --out ../../evals/baselines/text-levels.json`.
- **CP1 is passed when** 30 texts are in the bank with verified sources and the level report is committed. CP2 starts
  after that.

