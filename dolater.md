# Do later: the owner's list

Everything that waits on you, the owner, in one place. Last updated 18 Nov 2026. Tick items here as you do them; the
detail lives in each spec's `tasks.md`. Commands run from `apps/api` unless noted. Private data (recordings, essays,
labels) stays in git-ignored `data/private/`; only scores and metrics are committed.

## 1. Unblocks the next build step (do these first)
| What | Time | Unblocks | Where |
|---|---|---|---|
| [ ] **Phase 4, CP1:** read the licence of Simple English Wikipedia and of each OpenStax book (Sociology 3e, Astronomy 2e, World History vol. 1) on its own page; if they match, set `simple-wikipedia` and `openstax-reading` to `verified` (with `checked_on`, `licence_page`) | 15 min | Every Reading question | `data/sources/english-candidates.yaml` |
| [ ] **Phase 4, CP1:** on your laptop, `uv run python -m app.texts.fetch simple-wiki`, then `... fetch openstax`, then `uv run python -m app.texts.bank ../../data/private/english-texts`; move the texts to `data/english/texts/` and commit | 15 min | CP2b, the planted-error test | `specs/listening-reading/plan.md` (CP1 status) |
| [ ] **Phase 4, CP1:** `uv run python -m app.texts.levels sheet --out ../../data/private/levels.csv`; fill `level` (A1–C1) for all 30 texts; `... levels score ../../data/private/levels.csv --out ../../evals/baselines/text-levels.json` | 1 h | CP1 sign-off | same |
| [ ] **Phase 3:** listen to the 12 sentences with the Piper voice and check `data/pronunciation/canonical.yaml`, starting with "really" in p12 (the model heard /l/ as /d/) | 30 min | Pronunciation labels | `specs/pronunciation/step-3.3.md` |
| [ ] **Phase 3:** record 50–100 sentences on `/phat-am` with "keep" ticked; label every sound Đúng / Sai / Không chắc | 3–4 h | The pronunciation gate (false alarms ≤ 10%) | `specs/pronunciation/step-3.3.md` |
| [ ] **Phase 3:** `uv run python -m app.pronunciation.thresholds --out ../../evals/baselines/pronunciation-thresholds.json --apply ../../data/pronunciation/thresholds.json`, then `docker compose restart api worker` | 10 min | Marks on sounds, mastery on the pronunciation nodes | `specs/pronunciation/step-3.4.md` |
| [ ] **Vocabulary:** mark the 50-entry sample right or wrong, then run `score`; until then the imported list stays a draft | 1 h | The imported word list leaves draft | `specs/vocabulary-import/tasks.md` (T8) |

## 2. Reviews only you can do (quality)
- [ ] **Grammar items:** review the 76 draft MCQs (`data/items/english-ielts.yaml`, `draft` → `reviewed`) and the
  misconception texts (`data/items/misconceptions.vi.yaml`). Until then only you see them. About 3 h.
- [ ] **Vocabulary seed list:** definitions, examples, collocations and Vietnamese glosses in
  `data/vocabulary/core-seed.yaml`. About 2 h.
- [ ] **Writing:**
  - the error-type → node table, `data/writing/error-map.yaml`;
  - the consent wording and essay retention (`apps/web/messages/vi.ts`);
  - 10 Task 2 prompts of your own.
- [ ] **Lessons:** accept or fix the sample lesson. Choose which new milestones of the grammar path go live first
  (`specs/grammar-lessons/path.md`). Decide the source gaps (there is/are, used to, nominalisation, participle clauses,
  cleft sentences, hedging, impersonal passive): find a source, write the lessons yourself labelled "tự soạn", or leave
  those nodes without a lesson.
- [ ] **Pronunciation tips:** a Vietnamese `tip_vi` for each of the 14 sounds in `data/pronunciation/sounds.yaml`. Also
  record a model pronunciation of each prompt, if you want your own voice next to Piper's.
- [ ] **Phase 4, CP2b:** confirm that each planted fault in the planted set is a real fault (about 1 h, once I have
  drafted it).
- [ ] **Phase 4, CP3:** review at least 50 generated Reading questions on the review page (about 5 h, at 10 an hour).

## 3. Measurements for the gates
- [ ] **Phase 1:** the level-test accuracy curve with intervals; explain one real decision trace in the decision log
  (`specs/level-test/tasks.md`).
- [ ] **Phase 2, Writing:**
  - collect 50–100 essays with examiner bands (in `data/private/`);
  - set aside the 30% test split first;
  - mark LanguageTool's misses in 10 of your own essays;
  - rate the feedback points and AI corrections (`docs/v2/writing-eval.md` has every number to fill).
- [ ] **Phase 3:** write the pronunciation gate report, `docs/v2/pronunciation-eval.md`.
- [ ] **Phase 4:** agreement with the checker on 50 items, with kappa (CP3); the gate report (CP6).
- [ ] **One-command start:** run the stack and TEI indexing on your machine; record the time, chunk count and peak
  memory (`specs/one-command-start/tasks.md`).

## 4. Decisions waiting on you
- [ ] **Paid checker or not.** Free OpenRouter models give 50 requests a day: about 40 Reading questions a day, so a
  200-question bank takes about 5 days. US$10 of credit raises this to 1,000 a day. It's optional, and nothing is
  blocked without it.
- [ ] **Before anyone but you records their voice:** a privacy review of the voice policy (consent, retention, where
  audio goes). Recording is owner-only until then.
- [ ] **Before any paid tier:**
  - replace or relicense the NonCommercial sources (OpenStax reading texts; the Bissonnette, Explorations and Hall &
    Wallace grammar books);
  - the ShareAlike sources (Simple Wikipedia, NGSL/NAWL) oblige the derived banks to stay shared alike;
  - `data/` as a whole is CC BY-NC-SA, because it includes Think Python material.
- [ ] **Phase 3.5b:** fine-tuning the recogniser on a GPU notebook. Only worth it if your labels show the frozen
  model is the limit (it needs GPU time, and replaces the pinned model).
- [ ] **Phase 5, Speaking:**
  - the recognition model;
  - the transcript consent wording;
  - whether to find a teacher to rate 30+ recordings (without one, no band);
  - accounts for testers.

## 5. Routine (keep doing)
- [ ] Before each batch of new lessons or Reading questions, rerun the checker's planted test, because Ernie is a
  preview model and can change: `app.evalkit.verifier_pick`. Switch to dots if Ernie fails the bar.
- [ ] One entry a week in `docs/v2/decision-log.md`, in your own words.
- [ ] After pulling a change that adds a migration or a service: `git pull`, then `docker compose up -d`. The heavy
  services (`pronunciation`, `writing`, `scoring`) are opt-in profiles; run one at a time on your 4 GB Docker VM.
