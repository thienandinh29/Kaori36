# MAP — where things are

Keep this file current when adding top-level folders or important modules.
Planned entries are marked _(planned)_ until they exist.

## Repository paths

| Path | Purpose |
|---|---|
| `CLAUDE.md` | Rules and working agreement for Claude, one-owner v2 project (auto-loaded; imports `MAP.md` and `SPEC.md`) |
| `dolater.md` | **The owner's to-do list**: everything that waits on the owner (licence checks, recordings, labels, reviews, measurements, decisions), with time and commands |
| `README.md` | Public introduction in Vietnamese: NodeTrail as an English (IELTS) learning app, skills and their status, the plan, honest status, how to run |
| `SPEC.md` | What NodeTrail must do: an English learning app for Vietnamese learners (IELTS); features per skill, engine, verification gate, non-goals; other subjects later |
| `docs/v2/plan-english-pack.md` | **Current plan: the English app in phases, with gates and status** (where the project is) |
| `docs/v2/english-pack-proposal.vi.md` | The owner's proposal for the English pack (Vietnamese): why, components, metrics, risks |
| `docs/v2/plan-to-tet-2027.md` | Superseded weekly plan (weeks 0–2 done); kept for history and the maths outline |
| `docs/v2/decision-log.md` | Owner's weekly decision log, in their own words |
| `docs/v2/plan-m0-m1.md` | Superseded any-subject plan (M0 source catalogue, built; M1 Deep Research), kept for history and for other subjects later |
| `docs/archive/contest-2026/` | Contest history: `TEAM.md` (lanes, API contract tables, timeline), `PLAN.md`, `team/`, run sheets and reviews, pitch and mock-demo plan. Code comments that cite `TEAM.md` refer to this copy |
| `specs/` | GitHub Spec Kit: one folder per feature (spec, plan, tasks); `engine/`, `next-item/`, `retrieval/`, `library/`, `remediation/`, `model-test/`, `guardrails/` (P1; includes the labelling protocol), `contracts/review.md` (open contract decisions), `contracts/mocks/` (generated mock JSON for P5, `tests/engine/mocks.py`) |
| `.specify/` | Spec Kit project memory: `memory/constitution.md`; templates planned |
| `docker/` | `LOCAL.md` runbook (one-command start, tests, TEI indexing), `TEI.md` |
| `context/product-brief.vi.md` | Original product brief (Vietnamese) |
| `context/` | Reference material: research, textbook notes, algorithm papers |
| `outputs/` | Generated deliverables, not source code |
| `.claude/settings.json` | Pre-approved commands for Claude Code |
| `.claude/skills/verify/` | `/verify` — run all lint, type checks, tests |
| `.env.example` | Every env var the project uses (copy to `.env`) |
| `docker-compose.yml` | The whole stack in one command: db, migrate, api, worker, sandbox, runner, web; TEI, LanguageTool (`writing`), the scorer (`scoring`) and the voice (`speech`) as opt-in profiles (`specs/one-command-start/`) |
| `apps/api/Dockerfile`, `apps/web/Dockerfile` | Images for the API/worker/migrations and the web app |
| `scripts/stack-smoke.sh` | End-to-end checks of a running stack (also the CI `stack` job) |
| `.github/workflows/ci.yml` | CI: ruff, mypy, pytest against a pgvector service, evaluation gates, sandbox escape tests, grader self-test, the full stack |
| `evals/` | Evaluation gates and their committed baselines (`app/evalkit/gates.py`); placement accuracy is the first |
| `runner/` | Code sandbox service: sandbox image and harness, one locked-down container per run, `POST /run`, escape tests (`specs/code-sandbox/`) |
| `apps/api/` | FastAPI backend (uv, Python 3.12): `app/main.py` app factory + `/health` |
| `apps/api/app/config.py` | Settings from repo-root `.env` (pydantic-settings) |
| `apps/api/app/migrate.py` | Applies `supabase/migrations/*.sql` once each (`uv run python -m app.migrate`) |
| `apps/api/tests/` | pytest; `conftest.py` makes a throwaway migrated DB per run |
| `apps/api/app/schemas.py` | Contracts (P1): Knowledge Graph + Items YAML models with validators, `Citation`, every API body |
| `apps/api/app/engine/` | Pure, tested decision logic: `bkt.py` (mastery), `srs.py` (FSRS review scheduling); traced wrappers `update_traced`/`review_traced`; `trace.py` (`DecisionTrace`) |
| `apps/api/app/engine/bkt_fit.py` | EM (Baum-Welch) fitting of BKT parameters from answer sequences, held-out scoring (log loss, Brier, AUC), simulation; data needs in `docs/v2/bkt-fit-eval.md` |
| `apps/api/app/engine/graph.py` | `Graph` (prerequisite DAG: topological order, depth, ancestors/descendants) + `root_cause` to the weakest prerequisite, traced |
| `apps/api/app/evalkit/` | Evaluation helpers (P1): exact intervals and kappa (`stats.py`), the labelled-sample format (`labels.py`), guardrail scoring with notes on what the sample cannot show (`guardrail.py`) |
| `apps/api/app/evalkit/model_checks.py` | Offline H8 G1–G4 screening against P1 contracts; mandatory review remains explicit (`specs/model-test/offline-checks.md`) |
| `apps/api/app/evalkit/model_metrics.py` | H8 receipt scoring: verifier catches/false alarms with intervals, p95 latency, task and combined topic cost; missing evidence remains explicit (`specs/model-test/receipts.md`) |
| `specs/model-test/run-procedure.md` | P1's run procedure for the H8 model test: US$2.00 run cap and US$0.50 per-topic cap (proposals), settings, order, evidence to keep, stop rules |
| `apps/api/tests/engine/test_learning_flow.py` | JSON-replayed placement/remediation/mastery/review flow; optional P3 real grader on an integration checkout; no live DB/worker claim |
| `apps/api/app/engine/path.py` | The next step when nothing just went wrong (`next_step`: resume, overdue review, continue, learn, confirm, done) with a target difficulty; traced |
| `apps/api/app/engine/remediation.py` | Remediation rules after a wrong answer (`remediate`: weakest prerequisite, repeated misconception, practise again) and `resume`; traced |
| `apps/api/app/engine/placement.py` | Graph-walk placement: `next_question`, `gap`, `seed_mastery`; stateless, traced; `verify` re-check on by default |
| `apps/api/app/graders/` | Deterministic grading: MCQ (`mcq.py`), typed answers exact after normalisation (`typed.py`, normaliser extended by the owner), code compared outside the sandbox (`code.py`), runner client, grader self-test |
| `apps/api/app/vocabulary/`, `apps/api/app/services/vocabulary.py`, `apps/api/app/api/vocab.py` | Vocabulary (spec `specs/vocabulary/`): word list models and checks, items built from a word by id (meaning, gap-fill, collocation, word form), FSRS cards per learner and word, routes `/vocab/session`, `/vocab/answers` |
| `apps/api/app/services/code_practice.py`, `apps/api/app/api/code.py` | Code practice routes `/code/exercise`, `/code/attempts` (mounted when `RUNNER_URL` is set) |
| `apps/api/app/tutor/` | P4 three-level Socratic hints with independent verification and safe release |
| `apps/api/app/research/` | Deep Research agent, allowlisted search/readers, library acquisition and pipeline |
| `apps/api/app/curriculum/` | Course specs (modalities and figure kinds per objective, rubrics, code tests, CEFR level per concept, hidden nodes under milestones via `part_of`), figures as structured data, ground truth computed from figures (`facts.py`), course checker CLI (`check.py`); specs in `specs/curriculum-modalities/`, `specs/english-course/` |
| `apps/api/app/sources/` | v2 structured sources: licence from metadata (`licence.py`), OpenStax collection/CNXML parsers (`openstax.py`), catalogue fetch CLI (`fetch.py`); spec in `specs/source-catalog/` |
| `apps/api/app/uploads/` | PDF/DOCX/link readers and upload metadata validation |
| `apps/api/app/content/` | P4 schemas, generation, P3 gateway adapter, canonical conversions and runtime repositories/ports |
| `apps/api/app/guardrails/` | Blind verification, current-hash release gate, human-label metrics; live model acceptance pending |
| `data/guardrails/` | 50 evaluation questions + 20 hints and human annotation templates; human labels pending |
| `data/eval/` | Labelled retrieval question sets (Vietnamese question → answer passage) + format README; scored by `app/rag/evaluate.py` |
| `data/golden/` | Three agent-reviewed topics, 45 pending MCQs and 15 chunks; model/human approval pending |
| `apps/api/app/jobs/` | Committed Postgres queue, durable progress/trail, configurable P3 pipeline factory and P4 runtime processor |
| `apps/api/app/observability/` | Logging setup; structlog/Langfuse integration planned |
| `apps/api/app/rag/` | `notebook.py` (ipynb → chunks), `store.py` (`build_vector_index` after bulk load), `embed.py` (`TeiEmbedder` sync + async, local bge-m3, `make_embedder`; managed-API fallback planned), `chunker.py` (`ParsedDocument` → size-safe `Chunk`s), `library.py` (index every book folder), `retrieve.py` (`Retriever.search` → `Citation`s), `evaluate.py` (retrieval metrics on a labelled question set), `ingest.py` CLI (`--embedder tei|local`, `--build-index`); optional `rerank.py` planned (P1) |
| `data/raw/thinkpython/` | Downloaded Think Python 3e notebooks + `SOURCE_SHA` (git-ignored; re-download to rebuild) |
| `apps/api/app/llm/` | LLM gateway (DeepSeek generation, Gemini verification; legacy Vertex AI, Bedrock and OpenRouter adapters), `routing.yaml`, smoke CLI and setup README |
| `data/courses/` | Course specs: `english-ielts.yaml` (first real course: grammar roadmap of milestones with hidden nodes, A1–C1, starter draft), Python basics, IELTS Academic Writing, introductory statistics |
| `data/sources/` | Open-education allowlist, library manifests and acquisition/index reports; `catalog.yaml` + `catalog-report.json` for v2 structured sources; `english-candidates.yaml` (English sources awaiting licence checks, rules in `app/sources/candidates.py`) |
| `data-sa/` | CC BY-SA 4.0 data (`LICENSE.md` with attribution): `vocabulary/core-seed.yaml` = 3,533 words imported from NGSL/NAWL 1.2 (merged with `data/vocabulary/core-seed.yaml` when loaded), `import-report.json`, `sources.json` (official files' SHA-256), later `review-sample.yaml` |
| `apps/api/app/vocabulary/importer.py`, `headwords.py`, `ipa.py` | The NGSL/NAWL import (`specs/vocabulary-import/`): official files → headwords and levels, model entries checked by code, IPA only where espeak-ng (`tts` `/phonemize`) agrees |
| `data/vocabulary/` | Word lists: `core-seed.yaml` (130 authored words A2–C1 in 11 IELTS topics, with British IPA; draft until the owner reviews it) |
| `data/kg/` _(planned)_ | Knowledge Graph YAML fixtures |
| `data/items/` | Authored grammar items per course: `english-ielts.yaml` (76 draft MCQs, 4 per hidden node, a misconception on every wrong option); `misconceptions.vi.yaml` (each misconception explained in Vietnamese, draft) |
| `apps/api/app/engine/milestones.py` | Milestones and hidden nodes: status, milestone-test outcome (pass, gap, fail), what to learn next, locks (locked until the milestones before are known; test to unlock), level test on milestones, level estimate; traced (`specs/level-test/`) |
| `apps/api/app/services/grammar.py`, `apps/api/app/api/grammar.py` | Grammar roadmap API: `/level-tests`, `/roadmap`, `/milestones/{slug}/tests`, `/nodes/{slug}/practice`, `/grammar-runs/{id}/answers`; draft items only for `DRAFT_ITEM_LEARNERS` |
| `apps/api/app/writing/`, `apps/api/app/services/writing.py`, `apps/api/app/api/writing.py` | Writing (`specs/writing/`): prompts, deterministic essay analysis, `/writing/prompts`, `/essays`; the worker analyses queued essays; `services/budget.py` daily model budget |
| `data/writing/` | Writing prompts (authored, draft until reviewed), linking words by function, `error-map.yaml` (ERRANT type → hidden node, draft, with the writing observation model) |
| `apps/api/app/writing/languagetool.py`, `grammar.py`, `error_map.py`, `export_errors.py`; `apps/api/app/evalkit/writing_map.py` | Step 2.2: LanguageTool client and filter, minimal correction, ERRANT typing, mapping, evidence choice; the owner's mapping-check sheet and its score |
| `languagetool/` | LanguageTool 6.8 image (compose profile `writing`): Maven Central artifacts, every jar pinned by SHA-256 |
| `scorer/` | Band model service (compose profile `scoring`, PyTorch CPU): pinned model, revision and weights SHA-256; `POST /score` returns raw outputs only (`specs/writing/step-2.3.md`) |
| `apps/api/app/writing/scoring.py`, `scorer_client.py`; `apps/api/app/evalkit/writing_score.py`; `data/writing/scorer.yaml` | Step 2.3: calibration, band range, QWK, baselines and splits; the service client; the owner's evaluation (`develop`, then `test` once); the pin and calibration |
| `apps/api/app/writing/feedback.py`, `llm_corrections.py`, `model_calls.py`, `rewrite.py`; `apps/api/app/services/rewrites.py` | Step 2.4: feedback with checked quotes and the disagreement rule; AI corrections (minimal, typed, never evidence); budgeted model calls with one `llm_calls` row per attempt; paragraph rewrites (worker job, code diff, checks) and saved phrases as FSRS cards |
| `apps/api/app/texts/`; `data/english/texts/` | Step 4.1: the text bank. Texts tied to a verified source (licence copied from the source), measured level features, CLI `python -m app.texts.bank`; ships no texts. CP1 (`specs/listening-reading/plan.md`): `fetch.py` (Simple English Wikipedia on the owner's laptop, OpenStax from GitHub, picks in `data/english/text-picks.yaml`, output to git-ignored `data/private/english-texts/` until the sources are verified) and `levels.py` (CEFR labelling sheet, Spearman of each feature with the owner's labels) |
| `docs/research/openmaic-study.md`, `docs/research/grammar-teaching-study.md` | What NodeTrail takes from OpenMAIC's code; how to teach grammar (method, order, subtitles, Vietnamese learners) and the open grammar sources found, with what was and was not read |
| `specs/grammar-lessons/` | The lesson player (spec, not built): OpenMAIC-style scenes and actions, English voice with English and Vietnamese subtitles (by level), lessons generated offline from licence-checked sources through RAG, engine-chosen scenes; `path.md` + `english-ielts-path.yaml` = the proposed grammar path (28 milestones, 51 nodes, machine-checked, not live) with source chapters and gaps |
| `apps/api/app/lessons/`, `apps/api/app/api/lessons.py`; `data/lessons/`; `data-sa/vocabulary/forms.yaml` | Lessons before practice (`specs/grammar-lessons/`): the format (scenes of typed actions, checkpoints), every code check (graded narration through the NGSL/NAWL form index, no test overlap, citations, length), the store and `/lessons` routes (keys never sent; sample and draft lessons for `DRAFT_ITEM_LEARNERS` only); one sample lesson; web player `/hoc/{node}` (`components/lesson/`, `lib/lesson/`: pure playback reducer, board, subtitles by level, server voice with cancellation), "Học bài" on the milestone panel; `blind_check.py`: another model family answers each checkpoint blind from the lesson's teaching (and cited chunks), any disagreement makes it `needs_review` (`evals/lessons/`) |
| `docs/v2/web-handoff.md` | Handoff for redesigning the web app: pages and their API calls, the rules to keep, how to run and test |
| `apps/api/app/reading/items.py` | Step 4.2a: Reading question types (T/F/NG, multiple choice, completion, headings), checks against the passage, answer-key grading; only approved items are served |
| `apps/api/app/reading/generate.py`, `blind.py`, `pipeline.py`; `supabase/migrations/0024_reading_items.sql` | Step 4.2b (plan CP2a): DeepSeek writes questions (`reading_items`), code builds and checks them, free Ernie answers each blind from the passage only (`reading_check`), stored with status (`generated`, `dropped`, `needs_review`, `verified`, later `approved` or `rejected` by the owner); offline CLI with a daily check budget |
| `docs/v2/tts-candidates.md` | Text-to-speech candidates for the self-hosted voice (speech S2): licences of weights, voices, training data and code; Kokoro vs Piper; the owner's decisions |
| `specs/speech/`; `apps/web/lib/english/speech.ts`, `components/english/speak-button.tsx`; `apps/api/app/api/speech.py`; `tts/` | Hearing English: listen and slow buttons on word cards and saved phrases. S2 (preferred): the self-hosted Piper voice `en_GB-cori-high` (`tts/`, compose profile `speech`, GPL-3.0, pinned by SHA-256) through `/speech`; S1 fallback: the browser's voice (on-device only for the learner's own text) |
| `specs/plans/`; `apps/api/app/services/plans.py`, `apps/api/app/plans.yaml`; `supabase/migrations/0019_learner_plans.sql` | Plans (free, pro, owner) and their daily limits (essays, model calls), decided by the server; owner = the ids in `DRAFT_ITEM_LEARNERS`; `python -m app.services.plans show|set`; payment and login not built |
| `specs/pronunciation/`; `apps/api/app/pronunciation/`, `apps/api/app/services/recordings.py`, `apps/api/app/api/pronunciation.py`; `data/pronunciation/`; web `/phat-am` | Phase 3, decisions made 17 Nov; step 3.1 built: recordings (quality check, consent `voice-v1`, owner only, 24-hour deletion unless kept, migration `0021`), 14 target sounds and 12 draft sentences; step 3.3a built: canonical British phones per prompt (`canonical.yaml`, draft), target positions by rule (`canonical.py`), worker analysis through the service with audio cleared afterwards unless kept (`analysis.py`, migration `0022`), raw scores per sound on `/phat-am`; step 3.3b built: the owner labels kept recordings by ear (migration `0023`), thresholds per sound group chosen on one half and checked on the other (`thresholds.py`); step 3.4a built: marks only for groups the owner applied (`marks.py`, `data/pronunciation/thresholds.json`, absent until the gate), slip and guess from the measured rates; step 3.4b built: the course `data/courses/english-pronunciation.yaml` (one milestone, one hidden node per sound group, modality `speech`), one BKT observation per group per recording, progress on `/phat-am`; earlier spec: pipeline, target sounds, voice policy, evaluation on speechocean762 and on the owner's own recordings, the gate |
| `pronunciation/` | Phone recognition service (compose profile `pronunciation`, step 3.2): `facebook/wav2vec2-xlsr-53-espeak-cv-ft` pinned by SHA-256, `POST /recognise`, `POST /score` (CTC forced alignment and GOP in plain code, `nodetrail_pron/align.py`); measured about 1.9 GB and 0.4 s per sentence; `nodetrail_pron/evaluate.py` scores it on speechocean762 (test half: sentence r 0.593, phone AUC 0.855, `evals/baselines/pronunciation-speechocean762.json`); step 3.5a: `features.py` and `learn.py`, a logistic-regression detector on frozen-model features, trained on the train half and compared with GOP on the test half |
| `apps/api/app/writing/export_review.py`; `apps/api/app/evalkit/writing_review.py`; `docs/v2/writing-eval.md` | The owner's hand ratings: export feedback points and AI corrections to a private sheet, score them with exact intervals; the phase 2 gate report with every number to fill and the commands |
| `apps/api/app/writing/task1.py`; `apps/web/components/english/chart-figure.tsx`, `task1-checks.tsx`, `lib/english/chart.ts` | Step 2.5: Task 1 checks against the chart's data (numbers, key features, overview), the SVG chart and the checks section |
| `specs/two-layer-map/` | Design (not built): layer 1 CEFR Knowledge Map (grammar, vocabulary bands, pronunciation, usage), layer 2 IELTS Competency Map (Reading, Listening, Writing and Speaking criteria), the links between them, and a pure, traced Learning Recommendation Engine with a simulation gate |
| `specs/listening-reading/plan.md` | Phase 4 plan with six checkpoints (approved 18 Nov): texts, generation and blind check, review queue, Reading practice, Listening, gate report |
| `specs/listening-reading/`, `specs/speaking/` | Phases 4 and 5 specs and the owner's decision lists (not built): levelled open texts, blind-verified reviewed questions, audio sources; speech recognition, fluency measures, transcript feedback, and why no band without ratings |
| `docs/v2/writing-scorer-candidates.md` | Candidate band models read from Hugging Face: licences, data rights, loadability, the owner's choice |
| `apps/api/app/evalkit/verifier_pick.py`, `evals/verifier/planted-grammar.yaml`, `evals/baselines/verifier-pick-*.json` | Choosing the lesson checker: 20 planted grammar errors and 20 correct checkpoints, caught and false-alarm rates with intervals; free OpenRouter models paced to their limits. Chosen: Ernie (20/20 caught, 0/20 false alarms), dots as backup; the gateway allows `:free` models only for the `lesson_check` task |
| `apps/api/app/evalkit/english_gate.py`, `evals/baselines/english-placement.json` | Gate: simulated level-test accuracy on the English roadmap (gap and level), checked in CI |
| `apps/web/` | Next.js web app. English pack (`specs/web-english/`): `/` today, `/kiem-tra` level test, `/lo-trinh` roadmap, `/on-tap/{cot-moc|phan}/{slug}` milestone tests and practice, `/tu-vung` vocabulary, `/viet` writing prompts and essays, `/viet/{prompt}` editor, `/bai-viet/{id}` result, `/gioi-thieu` about (`components/english/`, `lib/english/`, Playwright tests in `e2e/`); the contest's topic research at `/kham-pha` (some steps still use sample data) |
| `specs/ui-v2/`, `outputs/design/ui-v2/` | UI v2: the owner's chosen design (trail map + skyline + Sena), its prototypes and screenshots; in the app as `app/theme.css` (tokens), `components/sena/` + `lib/sena.ts` (Sena, 7 poses), `lib/english/trail.ts` (map layout, rings, bands), `components/english/trail-map.tsx`, `skyline.tsx`, `milestone-panel.tsx` |
| `apps/web/messages/` | i18n strings (`vi` default, `en`) |
| `supabase/migrations/` | Database schema (Postgres + pgvector); `0001_init.sql` = schema v1, `0002` = chunk provenance (chapter, section, kind, url), `0003` = `halfvec(1024)`, `url` → `source_uri`, HNSW dropped (rebuilt after load), `0004` = `decision_traces` (the "Vì sao?" audit trail), `0014` = `vocab_cards` + `vocab_reviews` (vocabulary state), `0015` = `level_tests`, `grammar_runs`, `grammar_answers`, `0016` = `essays` + `llm_calls.learner_id`, `0017` = `llm_calls` tokens and task + `essay_corrections`, `0018` = `essay_rewrites` + `learner_phrases`, `0019` = `learners.plan`, `0020` = `recall` vocabulary kind, `0021` = `speech_recordings`, `0022` = recording analysis, `0023` = `speech_labels`, `0024` = `reading_items` |

| `apps/api/app/research/pipeline.py` | P3 topic orchestration; optional async Retriever with explicit indexed subject, citation identity checks and original reading order; validates P1 KnowledgeGraph before publication |

| `apps/api/app/research/smoke.py` | Explicit live canonical graph/items and blind verification route smoke; preflight reads a small public book chapter without model calls |
| `specs/p3-integration/p3-follow-up.md` | P3 follow-up, validated checks, live blockers and P2/P4 integration instructions |

| `specs/p3-integration/h7-results.md` | Current P3 H7 results after main/P4 integration; audited clean library, mandatory worker retrieval, canonical schemas, model configuration, live prerequisites |
| `data/sources/p3-python-library-audit.json`, `data/sources/p3-h7-readiness.json` | Reproducible local export audit and honest environment/model-call readiness receipts |

| `data/sources/p3-python-query-label-audit.json` | Confirms all 10 P1 query label snippets in the intended book sections, with exact page URLs; no ranked retrieval or held-out tuning |
