# Do later: the owner's list

Everything that waits on you, the owner, in one place (the plan: `PLAN.md`). Last updated 20 Nov 2026. Tick items here as you do them; the
detail lives in each spec's `tasks.md`. Commands run from `apps/api` unless noted. Private data (recordings, essays,
labels) stays in git-ignored `data/private/`; only scores and metrics are committed.

**Since 18 Nov the list is split by role** (`specs/validation/spec.md`): **the developer is not the ground truth.** You
do the work of a developer, tester and learner. Deciding whether English is *correct* (answer keys, examples, sounds,
levels, bands) goes to a reviewer you find; your own judgement on those is kept as learner feedback or Bronze, never as
a gate's truth.

## 1. As developer and tester (unblocks the next build step; do these first)
| What | Time | Unblocks | Where |
|---|---|---|---|
| [x] **Phase 4, CP1, OpenStax:** licence read on each book's page (19 Nov, all three CC BY-NC-SA 4.0); `openstax-reading` verified, 10 texts in the bank, 49 questions generated and checked blind | done | | `data/english/reading-items/` |
| [ ] **Phase 4, review the first questions (new):** on your laptop, after pulling `main`: `uv run python -m app.reading.itemfile import` (from `apps/api`; adds new questions, brings newer blind checks into questions you have not decided, never touches your decisions; run it after each pull), then open `/duyet-doc` (opens on **Theo bài đọc**: one passage at a time, keys A approve, R reject then 1–5 and Enter, S skip) and approve or reject each of the 38 verified and 7 flagged; questions from the daily checking batches appear there as each batch merges. Five of the flagged are T/F/NG where the key says NOT GIVEN and the checker FALSE or TRUE: the classic hard case, worth a careful read. Then `uv run python -m app.reading.itemfile export` and commit, so your decisions are saved | 45 min | Questions on `/doc` (Silver: your approval plus the agreeing checks) | `specs/listening-reading/step-4.2d.md` |
| [ ] **Phase 4, Listening sources (new, 19 Nov):** listen to the sample dialogue sent with the study; read `docs/v2/listening-sources.md`; choose the first source (recommended: own scripts voiced by Piper, with an audio check) and read the male voice's licences (OpenSLR 83 and Piper's lessac base) | 20 min | CP5 Listening | `specs/listening-reading/plan.md` |
| [ ] **Phase 4, CP5 decision (new, 20 Nov):** once some Reading questions are approved, run with the voice (`COMPOSE_PROFILES=...,speech` and `TTS_URL=http://tts:8030`), open `/nghe` → **Nghe cả bài**, listen to 5 passages and answer; decide whether the machine voice is good enough to keep for whole passages (it is one British voice reading textbook prose, not exam audio) | 30 min | CP5 closes; CP6 report | `specs/listening-reading/step-4.4c.md` |
| [ ] **Phase 5, speech recognition (new, 19 Nov):** read `docs/v2/asr-candidates.md` and the two model cards it names; choose the recogniser (recommended: Whisper small.en with a verbatim prompt) and whether grammar flags on speech stay hints until measured | 20 min | Speaking step 5.1 | `specs/speaking/tasks.md` |
| [ ] **Phase 3, L2-ARCTIC (new, 19 Nov):** open L2-ARCTIC's page; read its licence (believed CC BY-NC 4.0) and confirm it has Vietnamese speakers with phone-level error labels (believed 4). If both hold, tell the agent: it unblocks the real pronunciation benchmark (3.6b part 2) | 10 min | 3.6b part 2, 3.6c calibration | `specs/pronunciation/step-3.6b.md` |
| [ ] **Phase 4, CP1, Simple English Wikipedia:** read its licence page; if CC BY-SA 4.0, set `simple-wikipedia` to `verified` (with `checked_on`, `licence_page`) | 5 min | A2–B1 texts | `data/sources/english-candidates.yaml` |
| [ ] **Phase 4, CP1:** on your laptop, `uv run python -m app.texts.fetch simple-wiki` (OpenStax is done), then `uv run python -m app.texts.bank ../../data/private/english-texts`; move the texts to `data/english/texts/` and commit | 15 min | CP2b, the planted-error test | `specs/listening-reading/plan.md` (CP1 status) |
| [ ] **Phase 3:** record 50–100 sentences on `/phat-am` with "keep" ticked, and check that the pipeline works (quality check, analysis, deletion). The sound labels themselves go to a reviewer (section 3) | 2 h | The pronunciation gate | `specs/pronunciation/step-3.3.md` |
| [ ] **Phase 3, after the reviewer's labels:** `uv run python -m app.pronunciation.thresholds --out ../../evals/baselines/pronunciation-thresholds.json --apply ../../data/pronunciation/thresholds.json`, then `docker compose restart api worker`. **`--apply` is refused** unless the report rests on the reviewer's Gold labels from at least 50 recordings (V3); your own labels give a Bronze check of the pipeline only | 10 min | Marks on sounds, mastery on the pronunciation nodes | `specs/pronunciation/step-3.4.md` |
| [x] **Validation spec (`specs/validation/spec.md`):** approved 18 Nov; V1 built. When a reviewer agrees: `uv run python -m app.validation.cli add-reviewer --name "…" --role expert_teacher --expertise "…" --consented` (only after they agree to how their labels are used) | 5 min | Their labels count as Gold | `specs/validation/step-v1.md` |
| [ ] **Two maps (`specs/two-layer-map/spec.md`):** approve or change the design; set your target (band per skill, exam date). The links between competencies and foundations stay Bronze ("đề xuất") until a teacher checks a sample | 30 min | M1–M2, ideally before CP4 | same |
| [ ] **Phase 4, CP4b (new, 20 Nov), when it is built:** look over the planted test of explanations and confirm each planted fault is really a fault (the faults are planted by construction; your check is that each is unambiguous) | 30 min | CP4b's gate | `specs/listening-reading/spec.md` |
| [ ] **Research follow-up (new, 20 Nov):** in the next deep research, check in the primary sources the figures we act on: Vietnam's Speaking mean in IELTS's 2024–2025 test-taker data, Elder and O'Loughlin (2003), Kang et al. (2021), and whether IELTS One Skill Retake is offered in Vietnam; and ask whether naming the trap in Reading feedback raises later accuracy | 1 research run | Phase 5's priority; CP4b's claim | `PLAN.md` (Goal and order of priority; Risks) |

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
  these, never used as proof (`research/`, the validation spec). Record each skill's result (scores only, never the
  paper's content); NodeTrail's own estimate is snapshotted automatically:
  `uv run python -m app.progress.cli add --learner <your id> --skill reading --paper "<which paper>" --timed --raw 31/40 --band 7.0 --marked-by answer_key --baseline`
  (Writing and Speaking: `--marked-by trained_rater` if a rater banded it; `self` is kept as Bronze). Then
  `... schedule --learner <your id>` for the next date and `... report --learner <your id>` (written to the private
  `data/private/progress-report.json`). **The baseline is the most time-critical item on this list**: every week of
  learning before it is a week the study cannot see.

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
| [ ] Pronunciation labels on your kept recordings, on the portal: `make-batch --content speech_target --learner <your id>` (add `--role expert_teacher` for a teacher). Only your own kept recordings can be sent, and only by this command | Phonetics-trained teacher, or an English teacher | 3–4 h | The pronunciation gate (false alarms ≤ 10%) |
| [ ] CEFR levels of the 30 texts | English teacher | 1 h | CP1 sign-off |
| [ ] Phase 4, CP2b: confirm the "two defensible answers" planted faults (wrong-key faults are Gold by construction) | English teacher | 1 h | The planted-error test |
| [ ] Phase 4, CP3: a stratified batch of Reading questions on the portal `/kiem-duyet` (at least 50 for the gate; about 100 for the process rule), then `uv run python -m app.reading.agreement --out ../../evals/baselines/reading-agreement.json` (kappa, defect escape and false rejection against the expert, VER-001) | English teacher | 5–10 h | Gate 2 |
| [ ] Text levels: the 30 texts on the portal (`make-batch --content text_level`), then `uv run python -m app.texts.levels score-gold --out ../../evals/baselines/text-levels.json` | English teacher | 1 h | CP1's level report |
| [ ] Writing sheets: the same sheets you would fill, then score with `--rated-by teacher` (`app.evalkit.writing_map`, `app.evalkit.writing_review`); filled by you they are Bronze and never meet the gate | English teacher | 2 h | Phase 2 gate |
| [ ] Vocabulary: entries on the portal (`make-batch --content vocab_entry --size 50`): definitions, examples, collocations, forms and glosses | English teacher | 3 h | The imported list leaves draft |
| [ ] Grammar: items on the portal (`make-batch --content grammar_item --size 40`), answered blind then the key judged; the misconception texts (`data/items/misconceptions.vi.yaml`) still by sheet | English teacher | 2–3 h | Items served beyond you |
| [ ] Writing: the error-type → node table (`data/writing/error-map.yaml`) and the 100-error mapping check | English teacher | 2 h | Writing evidence on grammar nodes |
| [ ] Lessons: the sample lesson; the source gaps (there is/are, used to, nominalisation, participle clauses, cleft sentences, hedging, impersonal passive) | English teacher | 1–2 h | New milestones' lessons |
| [ ] Pronunciation tips: a Vietnamese `tip_vi` for each of the 14 sounds (`data/pronunciation/sounds.yaml`), and review the draft `data/pronunciation/phone-tips.yaml` (how to say 46 sounds, 25 common confusions with minimal pairs; shown as guides when a word's sound stays low) | English or phonetics teacher | 2 h | Tips on `/phat-am` and the word guides |
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
- [ ] **Research (`research/`):** KT-001 needs a public dataset's licence checked; FORGET-001 is collecting: review vocabulary
  most days and answer the "Kiểm tra lại sau một tuần" card on the home page when it appears (up to 3 a week); after
  about 4 weeks run `uv run python -m app.studies.forget --learner <your id>` (private report; it says whether the
  minimum of 200 delayed reviews is met); VER-001 needs the teacher's 50 labels above.
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
- [ ] **Order of the next builds (new, 20 Nov):** CP4b (why the wrong answer tempted you) before or after the CP6 report; CP4c
  (exam details) now or later; phase 5 Speaking right after CP6 (the research says Speaking is Vietnam's lowest skill, to check).

## 6. Routine (keep doing)
- [ ] Before each batch of new lessons or Reading questions, rerun the checker's planted test, because Ernie is a
  preview model and can change: `app.evalkit.verifier_pick`. Switch to dots if Ernie fails the bar.
- [ ] One entry a week in `docs/v2/decision-log.md`, in your own words.
- [ ] Time split (master roadmap): about 65% product, 25% research, 10% writing up.
- [ ] After pulling a change that adds a migration or a service: `git pull`, then `docker compose up -d`. The heavy
  services (`pronunciation`, `writing`, `scoring`) are opt-in profiles; run one at a time on your 4 GB Docker VM.
