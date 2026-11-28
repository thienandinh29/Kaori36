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
| [ ] **Phase 4, step 4.3d (new, 23 Nov): try a real test.** After pulling `main` and restarting the stack, take one Cambridge Reading passage under exam conditions, then open `/doc` → **Chấm bài bạn tự làm**, paste the passage, the questions (with their instructions), the official key and your answers. Check every question the app read back (fix or remove any it read wrongly), mark, and read the explanations of your wrong answers. Tell the agent: how many questions it read wrongly, whether any trap name or explanation was wrong (it is unchecked), and whether the three build choices in `step-4.3d.md` ("Part 1 built") suit you | 40 min | 4.3d part 2; whether the explanations are useful enough to keep | `specs/listening-reading/step-4.3d.md` |
| [x] **Phase 4, CP1, OpenStax:** licence read on each book's page (19 Nov, all three CC BY-NC-SA 4.0); `openstax-reading` verified, 10 texts in the bank, 49 questions generated and checked blind | done | | `data/english/reading-items/` |
| [ ] **Phase 4, review the bank's questions (optional since 22 Nov: only when you want more drills; feedback on your own Cambridge tests comes first, `step-4.3d.md`):** on your laptop, after pulling `main`: `uv run python -m app.reading.itemfile import` (from `apps/api`; adds new questions, brings newer blind checks into questions you have not decided, never touches your decisions; run it after each pull), then open `/duyet-doc` (opens on **Theo bài đọc**: one passage at a time, keys A approve, R reject then 1–5 and Enter, S skip) and approve or reject each of the 38 verified and 7 flagged; questions from the daily checking batches appear there as each batch merges. Five of the flagged are T/F/NG where the key says NOT GIVEN and the checker FALSE or TRUE: the classic hard case, worth a careful read. Then `uv run python -m app.reading.itemfile export` and commit, so your decisions are saved | 45 min | Questions on `/doc` (Silver: your approval plus the agreeing checks) | `specs/listening-reading/step-4.2d.md` |
| [ ] **Phase 4, Listening sources (new, 19 Nov):** listen to the sample dialogue sent with the study; read `docs/v2/listening-sources.md`; choose the first source (recommended: own scripts voiced by Piper, with an audio check) and read the male voice's licences (OpenSLR 83 and Piper's lessac base) | 20 min | CP5 Listening | `specs/listening-reading/plan.md` |
| [ ] **Phase 4, CP5 decision (new, 20 Nov):** once some Reading questions are approved, run with the voice (`COMPOSE_PROFILES=...,speech` and `TTS_URL=http://tts:8030`), open `/nghe` → **Nghe cả bài**, listen to 5 passages and answer; decide whether the machine voice is good enough to keep for whole passages (it is one British voice reading textbook prose, not exam audio) | 30 min | CP5 closes; CP6 report | `specs/listening-reading/step-4.4c.md` |
| [x] **Phase 5, speech recognition:** Whisper small.en chosen (27 Nov); built in step 5.1 | done | | `specs/speaking/step-5.1.md` |
| [ ] **Speaking 5.4b, try guided practice for a week (new, 28 Nov):** on `/noi/luyen`, practise a Part 3 question and a Part 2 cue card three times each and look at the numbers side by side. Tell the agent whether the idea shape, the three opening questions and the topic words help you start, whether 100%/75%/50% of the time feels right, and edit the topic words in `data/speaking/tests/` (each must stay in the word list). Whether repeating helps is for you to watch over weeks, not for the app to claim | 3 × 20 min | The shrink factors; the idea texts | `specs/speaking/step-5.4b.md` |
| [ ] **Speaking 5.3, decide the transcript consent wording (new, 28 Nov):** 5.3b would send an answer's transcript to a model provider (DeepSeek or Gemini, through the gateway) to write feedback with quoted evidence. Choose the wording a learner agrees to (what is sent, to whom, how long it is kept) and whether the owner's own tests may use it first; until then only 5.3a runs | 20 min | Speaking 5.3b | `specs/speaking/step-5.3.md` |
| [ ] **Speaking 5.3a, judge the hints (new, 28 Nov):** with LanguageTool on (`COMPOSE_PROFILES` has `writing`, `LANGUAGETOOL_URL` set), take a test and, for 20 hints, say whether each is a real error, a false alarm (spoken English that is fine) or a possible mishearing. The share of false alarms decides whether hints stay "có thể sai" | 40 min | The labels on the hints | `specs/speaking/step-5.3.md` |
| [ ] **Speaking 5.2, check the pauses on your own answers (new, 28 Nov):** after a test with the `asr` profile on, open `/noi/thi/{id}`, play five answers and count the pauses you hear (0.5 s or longer) against the app's count, and note whether "giữa mệnh đề" and "trong mệnh đề" agree with where you stopped. Tell the agent the mismatches; the thresholds (0.5 s, 2 s) and the clause rule are assumptions until then | 30 min | Whether the numbers can be trusted; the next tuning | `specs/speaking/step-5.2.md` |
| [ ] **Speaking 5.1, word error rate (new, 27 Nov):** start the stack with the recogniser (`COMPOSE_PROFILES=...,asr`, `ASR_URL=http://asr:8050`; the first start downloads about 490 MB), take a test on `/noi/thi`, then type what you said, word for word, for about 20 answers in `data/private/speaking/references.jsonl` (`{"answer_id": "…", "reference": "…"}`; the answer ids are in the result page's audio links). From `apps/api`: `uv run python -m app.speaking.wer --refs ../../data/private/speaking/references.jsonl --out ../../evals/speaking/wer.json`, and commit only the JSON. Also note the recogniser's speed and memory on your laptop (`docker stats`). Add `ASR_URL=` to `.env.example` (this session could not read that file) | 1 h | Whether grammar feedback on speech can be trusted (5.3) | `specs/speaking/step-5.1.md` |
| [ ] **Phase 3, L2-ARCTIC (new, 19 Nov):** open L2-ARCTIC's page; read its licence (believed CC BY-NC 4.0) and confirm it has Vietnamese speakers with phone-level error labels (believed 4). If both hold, tell the agent: it unblocks the real pronunciation benchmark (3.6b part 2) | 10 min | 3.6b part 2, 3.6c calibration | `specs/pronunciation/step-3.6b.md` |
| [ ] **Phase 4, CP1, Simple English Wikipedia:** read its licence page; if CC BY-SA 4.0, set `simple-wikipedia` to `verified` (with `checked_on`, `licence_page`) | 5 min | A2–B1 texts | `data/sources/english-candidates.yaml` |
| [ ] **Phase 4, CP1:** on your laptop, `uv run python -m app.texts.fetch simple-wiki` (OpenStax is done), then `uv run python -m app.texts.bank ../../data/private/english-texts`; move the texts to `data/english/texts/` and commit | 15 min | CP2b, the planted-error test | `specs/listening-reading/plan.md` (CP1 status) |
| [ ] **Phase 3:** record 50–100 sentences on `/phat-am` with "keep" ticked, and check that the pipeline works (quality check, analysis, deletion). The sound labels themselves go to a reviewer (section 3) | 2 h | The pronunciation gate | `specs/pronunciation/step-3.3.md` |
| [ ] **Phase 3, after the reviewer's labels:** `uv run python -m app.pronunciation.thresholds --out ../../evals/baselines/pronunciation-thresholds.json --apply ../../data/pronunciation/thresholds.json`, then `docker compose restart api worker`. **`--apply` is refused** unless the report rests on the reviewer's Gold labels from at least 50 recordings (V3); your own labels give a Bronze check of the pipeline only | 10 min | Marks on sounds, mastery on the pronunciation nodes | `specs/pronunciation/step-3.4.md` |
| [x] **Validation spec (`specs/validation/spec.md`):** approved 18 Nov; V1 built. When a reviewer agrees: `uv run python -m app.validation.cli add-reviewer --name "…" --role expert_teacher --expertise "…" --consented` (only after they agree to how their labels are used) | 5 min | Their labels count as Gold | `specs/validation/step-v1.md` |
| [ ] **Two maps (`specs/two-layer-map/spec.md`):** approve or change the design; set your target (band per skill, exam date). The links between competencies and foundations stay Bronze ("đề xuất") until a teacher checks a sample | 30 min | M1–M2, ideally before CP4 | same |
| [ ] **Phase 4, CP4b (new, 20 Nov), when it is built:** look over the planted test of explanations and confirm each planted fault is really a fault (the faults are planted by construction; your check is that each is unambiguous) | 30 min | CP4b's gate | `specs/listening-reading/spec.md` |
| [ ] **Research follow-up (new, 20 Nov):** in the next deep research, check in the primary sources the figures we act on: Vietnam's Speaking mean in IELTS's 2024–2025 test-taker data, Elder and O'Loughlin (2003), Kang et al. (2021), and whether IELTS One Skill Retake is offered in Vietnam; and ask whether naming the trap in Reading feedback raises later accuracy. **From the Speaking research (20 Nov):** check Ngo et al. 2023 (*ReCALL*, the meta-analysis), the HNUE study (no band gain), LearnerVoice (INTERSPEECH 2024), and the references dated 2026–2027 or cited only by arXiv number or a vendor blog; and read `openai/whisper-small.en`'s card for its licence (the report says MIT, the card we read says Apache-2.0) | 1 research run | Phase 5's priority; CP4b's claim | `PLAN.md` (Goal and order of priority; Risks) |
| [ ] **Writing 2.11a, feedback stability (new, 21 Nov):** collect about 20 Task 2 sample essays from the web (IELTS preparation sites; strong and weak ones), one JSON line each in `data/private/writing/stability/essays.jsonl`: `{"id": "web-01", "question": "…", "text": "…", "source": "<url>"}`. Then from `apps/api`: `uv run python -m app.evalkit.feedback_stability ../../data/private/writing/stability/essays.jsonl --runs 3 --max-cost 0.30 --out ../../evals/writing/feedback-stability.json` and commit only the report. No band labels needed | 1 h | Whether one feedback call is stable enough (step 2.11) | `specs/writing/step-2.11.md` |

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
| [ ] Speaking: rate your full mock test every 4 weeks (best: a mock done in NodeTrail, kept recordings sent through the portal), then record the band with `app.progress.cli` | Trained IELTS rater | 20 min a mock | Your real Speaking band; the check of SPK-001's estimate on you |
| [ ] Testers: try the app and report what breaks or confuses | 3–5 testers | 1 h each | Wider use |

Before asking anyone, send them `specs/validation/reviewer-brief.vi.md` (V5): fill in the [brackets] (your name,
contact, payment or thanks) and tick the jobs you want from that person. Add them only after they reply "Đồng ý".

## 4. Measurements (you run them; the truth behind them is Gold or published data)
- [ ] **Phase 1:** the level-test accuracy curve with intervals; explain one real decision trace in the decision log
  (`specs/level-test/tasks.md`).
- [ ] **Phase 2, Writing:**
  - collect 50–100 essays with examiner bands (in `data/private/`); set aside the 30% test split first; **prefer essays that
    show all four criterion bands** (Task Response, Coherence and Cohesion, Lexical Resource, Grammar), so each criterion's
    band can be measured too (`specs/writing/spec.md`, point 8b). One JSON line each in
    `data/private/writing/essays.jsonl`: `id`, `question`, `text`, `band`, and where given `tr`, `cc`, `lr`, `gra`,
    `marked_by` (`examiner` or `trained_rater`) and `source`. Good sources: the sample answers with examiner comments in
    the Cambridge IELTS books, the official sample scripts (IELTS, British Council, IDP), your own essays banded by a
    trained rater; a website's own marking is not an examiner band. Step 2.12 needs criterion bands on at least 40;
  - **then run the comparison** (step 2.12, from `apps/api`; the heavy services one at a time on the 4 GB VM: first
    `docker compose --profile scoring up -d` with `--scorer-url http://localhost:8020` so the raw scores are cached in
    `data/private/writing/raw-cache.json`, then stop it and start `--profile writing` for `--languagetool-url
    http://localhost:8010`; a second run reads the cache):
    `uv run python -m app.evalkit.writing_score develop ../../data/private/writing/essays.jsonl --scorer-url http://localhost:8020 --languagetool-url http://localhost:8010`
    then read `evals/writing/develop-report.json`: `methods` (QWK with intervals for the five methods), `descriptors.choice`
    (the recommendation and whether it clearly beats the feature baseline), `descriptors.descriptor_model` (which features
    were kept), `descriptors.per_criterion`, `descriptors.caps` (does each cap help where it fires) and `ranges`. **Without
    LanguageTool the grammar features are missing, so the model is not the one the app will use.** Your decision: add
    `--write-calibration` (the pinned scorer) and/or `--write-descriptors criteria|blend` to store a method in
    `data/writing/scorer.yaml`, then `test` once for the held-out essays. The app shows nothing until you do;
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
- [ ] **Speaking 5.4a, built 27 Nov:** edit the five draft examiner tests (`data/speaking/tests/`), then take two
  full tests on `/noi/thi` and say whether the timing and the cut-offs feel like the exam. When a rater bands a mock, record
  the four criterion bands too: `--criteria fc=..,lr=..,gra=..,p=..` (`specs/validation/step-v4.md`, T6).
- [ ] **From the Speaking scoring research (new, 27 Nov), to check before relying on them:** whether IELTS publishes the
  Speaking round-down rule (.75 → .5); Tavakoli 2011 and de Jong et al. on pauses inside clauses; the licences of MultiPA and
  GOPT on their own pages, and whether either fits the 4 GB machine; `OpenPronounce/wav2vec2-base-phones-en` is AGPL-3.0
  (source-sharing duties if served), so not planned.
- [ ] **Speaking level estimate, SPK-001 (new, 27 Nov; the band rule change is approved):** read the Speak & Improve Corpus
  2025 licence in full on Cambridge's ELiT site and sign it if it suits. Tell the agent: (a) may a model trained on it run
  inside NodeTrail for you, and later, free, for friends and family; (b) may the audio sit in a private free GPU notebook
  (Kaggle, Colab); (c) may results be published in your portfolio. Nothing is downloaded before that. The work starts after
  Speaking 5.1–5.2 (`research/experiments/SPK-001.yaml`).
- [ ] **Wiktionary for vocabulary (new, 26 Nov):** licence read by the owner (CC BY-SA 4.0, dual with GFDL); decide whether
  an enrichment step follows: British IPA for
  713 words that have none, Wiktionary's Vietnamese next to the model's, recordings later after a per-file licence check.
  Numbers: `specs/vocabulary-import/step-wiktionary.md`.
- [ ] **Reading diagnosis (new, 27 Nov):** (a) whether a question should ever update several skills in BKT once a teacher
  has checked the skill tags (`specs/listening-reading/step-4.3e.md`; today: one competency, tags in summaries only);
  (b) a public reading dataset with a Q-matrix for DIAG-001: read its licence; (c) when DIAG-001 starts (after KT-001,
  and only if it does not take study time). Check the citations listed in `research/experiments/DIAG-001.yaml` first.
- [ ] **Order of the next builds (new, 20 Nov):** CP4b (why the wrong answer tempted you) before or after the CP6 report; CP4c
  (exam details) now or later; phase 5 Speaking right after CP6 (the research says Speaking is Vietnam's lowest skill, to check).

## 6. Routine (keep doing)
- [ ] Before each batch of new lessons or Reading questions, rerun the checker's planted test, because Ernie is a
  preview model and can change: `app.evalkit.verifier_pick`. Switch to dots if Ernie fails the bar.
- [ ] One entry a week in `docs/v2/decision-log.md`, in your own words.
- [ ] Time split (master roadmap): about 65% product, 25% research, 10% writing up.
- [ ] After pulling a change that adds a migration or a service: `git pull`, then `docker compose up -d`. The heavy
  services (`pronunciation`, `writing`, `scoring`) are opt-in profiles; run one at a time on your 4 GB Docker VM.
