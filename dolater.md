# Do later: the owner's list

Everything that waits on you, the owner, in one place. Last updated 18 Nov 2026. Tick items here as you do them; the
detail lives in each spec's `tasks.md`. Commands run from `apps/api` unless noted. Private data (recordings, essays,
labels) stays in git-ignored `data/private/`; only scores and metrics are committed.

**Since 18 Nov the list is split by role** (`specs/validation/spec.md`): **the developer is not the ground truth.** You
do the work of a developer, tester and learner. Deciding whether English is *correct* (answer keys, examples, sounds,
levels, bands) goes to a reviewer you find; your own judgement on those is kept as learner feedback or Bronze, never as
a gate's truth.

## 1. As developer and tester (unblocks the next build step; do these first)
| What | Time | Unblocks | Where |
|---|---|---|---|
| [ ] **Phase 4, CP1:** read the licence of Simple English Wikipedia and of each OpenStax book (Sociology 3e, Astronomy 2e, World History vol. 1) on its own page; if they match, set `simple-wikipedia` and `openstax-reading` to `verified` (with `checked_on`, `licence_page`) | 15 min | Every Reading question | `data/sources/english-candidates.yaml` |
| [ ] **Phase 4, CP1:** on your laptop, `uv run python -m app.texts.fetch simple-wiki`, then `... fetch openstax`, then `uv run python -m app.texts.bank ../../data/private/english-texts`; move the texts to `data/english/texts/` and commit | 15 min | CP2b, the planted-error test | `specs/listening-reading/plan.md` (CP1 status) |
| [ ] **Phase 3:** record 50–100 sentences on `/phat-am` with "keep" ticked, and check that the pipeline works (quality check, analysis, deletion). The sound labels themselves go to a reviewer (section 3) | 2 h | The pronunciation gate | `specs/pronunciation/step-3.3.md` |
| [ ] **Phase 3, after the reviewer's labels:** `uv run python -m app.pronunciation.thresholds --out ../../evals/baselines/pronunciation-thresholds.json --apply ../../data/pronunciation/thresholds.json`, then `docker compose restart api worker`. **`--apply` is refused** unless the report rests on the reviewer's Gold labels from at least 50 recordings (V3); your own labels give a Bronze check of the pipeline only | 10 min | Marks on sounds, mastery on the pronunciation nodes | `specs/pronunciation/step-3.4.md` |
| [x] **Validation spec (`specs/validation/spec.md`):** approved 18 Nov; V1 built. When a reviewer agrees: `uv run python -m app.validation.cli add-reviewer --name "…" --role expert_teacher --expertise "…" --consented` (only after they agree to how their labels are used) | 5 min | Their labels count as Gold | `specs/validation/step-v1.md` |
| [ ] **Two maps (`specs/two-layer-map/spec.md`):** approve or change the design; set your target (band per skill, exam date). The links between competencies and foundations stay Bronze ("đề xuất") until a teacher checks a sample | 30 min | M1–M2, ideally before CP4 | same |

## 2. As learner (your own signal, never a correctness label)
- [ ] Use the app most days. When something is unclear, too hard, or assumes what you were not taught, say so: that is
  learner feedback, and it is valuable.
- [ ] **Text levels (CP1), as feedback:** `uv run python -m app.texts.levels sheet --out ../../data/private/levels.csv`;
  fill `level` with how hard each text *felt* to you (about 1 h). The CEFR level itself comes from a teacher
  (section 3).
- [ ] **Phase 3:** listen to the 12 sentences with the Piper voice and flag any that sound wrong to you in
  `data/pronunciation/canonical.yaml`, starting with "really" in p12 (the model heard /l/ as /d/). A reviewer
  confirms the fix.
- [ ] **Progress study:** take an independent test every 4 weeks (official sample papers under exam conditions, or a
  mock with a trained rater). A baseline first, before more learning. NodeTrail's own estimates are compared against
  these, never used as proof (`research/`, the validation spec).

## 3. Find a reviewer for… (correctness; the one job only you can do)
**How to give a reviewer access (V2 portal):** once they reply "Đồng ý", run `add-reviewer` (section 1), then
`uv run python -m app.validation.cli issue-token --reviewer <id> --base-url <your web address>` and send the link
privately (it is shown once; `revoke-token` ends it). Make their batch with
`uv run python -m app.validation.cli make-batch --content reading_item --name "Đọc đợt 1" --size 100` (or `--content text_level`;
100 so the checker-verified part can reach the 72 items the 5% process bar needs with no escapes)
after CP1, when the texts are in the bank.

Find: **one English teacher** (grammar, vocabulary, Reading, text levels), **one person with IELTS rating experience**
(Writing and Speaking bands), optionally **a phonetics-trained teacher** (pronunciation), and **3–5 testers**.
Friends, lecturers or English-major students are fine for teacher-level checks; bands need trained raters. Until the
reviewer portal (V2) exists, they can work from the same sheets and pages.

| Find a reviewer for… | Who | Their time | Unblocks |
|---|---|---|---|
| [ ] Pronunciation labels on your kept recordings (Đúng / Sai / Không chắc per target sound) and the canonical phones | Phonetics-trained teacher, or an English teacher | 3–4 h | The pronunciation gate (false alarms ≤ 10%) |
| [ ] CEFR levels of the 30 texts | English teacher | 1 h | CP1 sign-off |
| [ ] Phase 4, CP2b: confirm the "two defensible answers" planted faults (wrong-key faults are Gold by construction) | English teacher | 1 h | The planted-error test |
| [ ] Phase 4, CP3: a stratified batch of Reading questions on the portal `/kiem-duyet` (at least 50 for the gate; about 100 for the process rule), then `uv run python -m app.reading.agreement --out ../../evals/baselines/reading-agreement.json` (kappa, defect escape and false rejection against the expert, VER-001) | English teacher | 5–10 h | Gate 2 |
| [ ] Text levels: the 30 texts on the portal (`make-batch --content text_level`), then `uv run python -m app.texts.levels score-gold --out ../../evals/baselines/text-levels.json` | English teacher | 1 h | CP1's level report |
| [ ] Writing sheets: the same sheets you would fill, then score with `--rated-by teacher` (`app.evalkit.writing_map`, `app.evalkit.writing_review`); filled by you they are Bronze and never meet the gate | English teacher | 2 h | Phase 2 gate |
| [ ] Vocabulary: the 50-entry sample right or wrong, then `score`; the seed list's definitions, examples, collocations and glosses (`data/vocabulary/core-seed.yaml`) | English teacher | 3 h | The imported list leaves draft |
| [ ] Grammar: a stratified sample of the 76 draft MCQs and their misconception texts (`data/items/`) | English teacher | 2–3 h | Items served beyond you |
| [ ] Writing: the error-type → node table (`data/writing/error-map.yaml`) and the 100-error mapping check | English teacher | 2 h | Writing evidence on grammar nodes |
| [ ] Lessons: the sample lesson; the source gaps (there is/are, used to, nominalisation, participle clauses, cleft sentences, hedging, impersonal passive) | English teacher | 1–2 h | New milestones' lessons |
| [ ] Pronunciation tips: a Vietnamese `tip_vi` for each of the 14 sounds (`data/pronunciation/sounds.yaml`) | English or phonetics teacher | 1 h | Tips on `/phat-am` |
| [ ] Speaking (phase 5): ratings of 30+ recordings | IELTS rater | 3 h | Any Speaking band |
| [ ] Testers: try the app and report what breaks or confuses | 3–5 testers | 1 h each | Wider use |

Before asking anyone, send them `specs/validation/reviewer-brief.vi.md` (V5): fill in the [brackets] (your name,
contact, payment or thanks) and tick the jobs you want from that person. Add them only after they reply "Đồng ý".

## 4. Measurements (you run them; the truth behind them is Gold or published data)
- [ ] **Phase 1:** the level-test accuracy curve with intervals; explain one real decision trace in the decision log
  (`specs/level-test/tasks.md`).
- [ ] **Phase 2, Writing:**
  - collect 50–100 essays with examiner bands (in `data/private/`); set aside the 30% test split first;
  - LanguageTool's misses and the feedback/correction ratings: by the teacher, on 10 essays (`docs/v2/writing-eval.md`
    has every number to fill).
- [ ] **Phase 3:** write the pronunciation gate report, `docs/v2/pronunciation-eval.md`.
- [ ] **Phase 4:** the gate report (CP6).
- [ ] **Research (`research/`):** KT-001 needs a public dataset's licence checked; FORGET-001 needs about 4 weeks of
  reviews (at least 200); VER-001 needs the teacher's 50 labels above.
- [ ] **One-command start:** run the stack and TEI indexing on your machine; record the time, chunk count and peak
  memory (`specs/one-command-start/tasks.md`).

## 5. Decisions waiting on you
- [ ] **Paying reviewers or not**, and how much of their time to ask for.
- [ ] **Paid checker or not.** Free OpenRouter models give 50 requests a day: about 40 Reading questions a day, so a
  200-question bank takes about 5 days. US$10 of credit raises this to 1,000 a day. It's optional, and nothing is
  blocked without it.
- [ ] **Before anyone but you records their voice:** a privacy review of the voice policy (consent, retention, where
  audio goes). Recording is owner-only until then; a reviewer only *listens* to your kept recordings.
- [ ] **Before any paid tier:**
  - replace or relicense the NonCommercial sources (OpenStax reading texts; the Bissonnette, Explorations and Hall &
    Wallace grammar books);
  - the ShareAlike sources (Simple Wikipedia, NGSL/NAWL) oblige the derived banks to stay shared alike;
  - `data/` as a whole is CC BY-NC-SA, because it includes Think Python material.
- [ ] **Phase 3.5b:** fine-tuning the recogniser on a GPU notebook. Only worth it if the reviewer's labels show the
  frozen model is the limit (it needs GPU time, and replaces the pinned model).
- [ ] **Phase 5, Speaking:** the recognition model; the transcript consent wording; accounts for testers.

## 6. Routine (keep doing)
- [ ] Before each batch of new lessons or Reading questions, rerun the checker's planted test, because Ernie is a
  preview model and can change: `app.evalkit.verifier_pick`. Switch to dots if Ernie fails the bar.
- [ ] One entry a week in `docs/v2/decision-log.md`, in your own words.
- [ ] Time split (master roadmap): about 65% product, 25% research, 10% writing up.
- [ ] After pulling a change that adds a migration or a service: `git pull`, then `docker compose up -d`. The heavy
  services (`pronunciation`, `writing`, `scoring`) are opt-in profiles; run one at a time on your 4 GB Docker VM.
