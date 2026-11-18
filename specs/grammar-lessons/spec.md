# Spec: a teacher before the exercises and the test (lesson player, grammar map first)

The owner's requests (16–17 Nov 2026):
- on the grammar map, "a teacher teaches me first, then gives me exercises and a test";
- teach like OpenMAIC (`THU-MAIC/OpenMAIC`, MIT), taking what fits and improving on it;
- build the lessons from licence-checked sources through RAG;
- base the way of teaching and the grammar path on good curricula.

Research: `docs/research/grammar-teaching-study.md` (teaching method, grammar order, subtitles, sources) and
`docs/research/openmaic-study.md` (OpenMAIC's code at `6e51916`).

## The owner's decisions (17 Nov 2026)
1. OpenMAIC's ideas that fit, improved where we can; **none of its code**.
2. Keep **"Tôi đã biết, kiểm tra luôn"** (skip the lesson, take the test).
3. **The learner hears English**, with **English and Vietnamese subtitles**.
4. Lessons come from **licence-checked sources, read through RAG**, and cite them.
5. The method and the grammar path come from research on good curricula, adapted (the study above).

## The lesson shape (test → teach → test)
- **First test.** The level test or the milestone test. "Tôi đã biết, kiểm tra luôn" is this step for a learner who
  already knows the grammar.
- **Teach.** The lesson, 2–3 minutes, in four parts:
  1. **Engage: vì sao cần?** An IELTS situation where you need this grammar. One English example the learner hears.
  2. **Study: meaning, by noticing.** Two or three examples that contrast (spotlight the difference). Sena asks
     "What's different?" and pauses, then says the rule plainly. A timeline on the board for tenses. Two or three
     concept-checking yes/no questions (aided checkpoints).
  3. **Study: form.** A table (+ / − / ?), the spoken form (weak "have", the /t/ /d/ /ɪd/ of -ed) read by the voice,
     time words. Then **"So với tiếng Việt"**: why Vietnamese speakers slip here, linked to the misconceptions the
     questions test. Plus a one-line reminder of earlier endings or articles where this lesson uses them (the spiral).
  4. **Activate.** Two short checkpoints graded by key, then a one-line summary and "Luyện tập".
- **Second test.** The node's practice (unaided), then the milestone test. Grammar nodes that reach mastery get spaced
  reviews (FSRS), mixed with earlier grammar.

## Hearing and reading
- **Sena speaks English**, read by our voice (Piper `en_GB-cori-high`, `/speech`). Every sentence also has a slow
  version.
- **Subtitles under the board**: English (the target form highlighted) and Vietnamese. Each can be switched on or off.
  **Default by level** (review, 17 Nov): at **A1 the Vietnamese subtitle only**, so a beginner is not overloaded (the
  study's section 7: captions do not help learners without spare capacity); **from A2, both**. The target form stays
  highlighted on the example card at every level, so a beginner still sees it.
- **The narration is graded English, checked by code.** Each word is reduced to its headword through the NGSL/NAWL
  **form lists** we already downloaded (`go, goes, went, going, gone`; `child, children`), so no lemmatizer (and no new
  dependency) is needed. A word passes when its headword is in the **full** NGSL/NAWL headword list at or below the
  lesson's level (function words included: the learner list leaves them out, the narration needs them), or in the
  authored list, or in an allowlist (names such as Sena, Hanoi, IELTS; numbers; the grammar terms the lesson
  introduces). Sentences are short: at most 15 words for A1–A2 lessons, 20 for B1 and above. If the form lists miss
  too much, spaCy is the fallback; it would be proposed as a dependency first.
- With sound off, the subtitles carry the whole lesson.

## The action language (from OpenMAIC, closed list)
A lesson is a few scenes; a scene is an ordered list of actions. Each action is checked against a schema, so a model
cannot invent new ones.

| Action | What it does | Waits until done |
|---|---|---|
| `say` | Sena says English narration, with its Vietnamese subtitle | yes |
| `show_example` | Shows an example card: English, Vietnamese, target phrase | no |
| `spotlight` | Highlights the target phrase in an example | no |
| `board_table` | Writes a form table on the board | no |
| `board_timeline` | Draws past, now and future with points or spans | no |
| `board_write` | Writes a line on the board | no |
| `board_arrow` | Draws an arrow on the board | no |
| `board_clear` | Clears the board | no |
| `ask` | A checkpoint, graded by key, aided | yes |
| `pause` | Waits for the learner ("What's different?") | yes |

```yaml
node: present-perfect-vs-past
level: B1
scenes:
  - id: engage
    cites: [chunk:al-haider-ch3-012]
    actions:
      - {do: say, en: "In IELTS Speaking, the examiner asks: How long have you lived in your city?", vi: "Trong IELTS Speaking, giám khảo hỏi: Bạn sống ở thành phố của mình bao lâu rồi?"}
  - id: notice
    cites: [chunk:al-haider-ch3-014]
    actions:
      - {do: show_example, id: a, en: "I lived in Hue for two years.", vi: "Tôi đã sống ở Huế hai năm (giờ không còn sống ở đó).", target: "lived"}
      - {do: show_example, id: b, en: "I have lived in Hanoi for two years.", vi: "Tôi sống ở Hà Nội được hai năm (và vẫn đang sống).", target: "have lived"}
      - {do: say, en: "Look at the two sentences. Does she still live in Hue? Does she still live in Hanoi?", vi: "Nhìn hai câu. Cô ấy còn sống ở Huế không? Còn ở Hà Nội không?"}
      - {do: pause}
      - {do: board_timeline, spans: [{label: "Hue", from: -4, to: -2}, {label: "Hanoi", from: -2, to: 0, open: true}]}
  - id: check
    misconceptions: [past-simple-for-unfinished]
    actions:
      - {do: ask, checkpoint: ppvp-ccq-1}
```

## Playback
- **States:** `idle → playing → paused → live`. "Live" is reached through "Hỏi Sena" (phase D).
- **Controls:** Tạm dừng, Nghe lại, Nghe chậm, Câu trước, Câu sau, Phụ đề EN/VI, Hỏi Sena, Bỏ qua bài học.
- **Layout:** phone first, with Sena beside the board and the subtitles below.
- **Map order:** Bài học → Luyện tập → Kiểm tra. After a wrong answer, "Xem lại cảnh này" opens the scene tagged with
  that misconception.

## How the engine and the teacher fit together
- **Reading is not evidence.** A lesson never changes mastery and never unlocks anything. Sena praises mastery only.
- **Checkpoints are aided evidence.** They are graded by key and weighted like answers after help, under the mastery
  gate in `specs/mastery-gate/`. Practice and tests are the unaided evidence.
- **The engine chooses the scene to replay.** The "Vì sao?" trace says why: "Sena cho xem lại cảnh X vì bạn chọn Y".
- **No lesson sentence is a test sentence.** Code checks that no example or checkpoint repeats a question or contains
  its answer.

## Where the content comes from: RAG over licence-checked sources
1. **Sources.** Read on their own pages on 17 Nov 2026, by the agent at the owner's request (`checked_by: agent` in
   `data/sources/english-candidates.yaml`):
   - Bissonnette: CC BY-NC 4.0, A1–C1, the backbone.
   - Al Haider High-Intermediate: CC BY 4.0, B1–B2.
   - Explorations 1: CC BY-NC-SA 4.0, the first A1 nodes.
   - Wikibooks English Grammar: CC BY-SA 4.0, terms only.

   NoDerivatives sources are never used. NonCommercial sources are flagged. CC BY-SA material goes in `data-sa/`.
   Which node each source covers, and the gaps (articles above all), are in `path.md`.
2. **Licence on every chunk and every lesson** (review, 17 Nov).
   - Each chunk stores its licence as a fixed value with an `is_noncommercial` flag. Today `sources.license` is free
     text.
   - A lesson stores the licences of the chunks it cites, and is NonCommercial if any of them is.
   - If NodeTrail ever charges money or partners with a company, one query lists every NC chunk and every lesson built
     on one.
   - Note: `data/` as a whole is CC BY-NC-SA, because it holds Think Python material. Going commercial also means
     cleaning or relicensing `data/`, not only the chunks.
3. **Library.**
   - Fetch only from the source's own site, with the licence and URL recorded per chapter (`app/sources/`).
   - Chunk with chapter and section kept, then embed with bge-m3. Embedding runs where it can: the GPU notebook route
     in `specs/cited-items/`, or TEI on a machine that can run it.
   - The library is indexed per source.
4. **Our own notes as chunks** (review, 17 Nov).
   - One chunk per Vietnamese learner error type (agreement, plural -s, articles, tense), written in our own words
     from the studies in the study's section 4.
   - Each is linked to its misconception tags in `data/items/misconceptions.vi.yaml`, so retrieval finds them for the
     "So với tiếng Việt" scene.
   - They are labelled **authored (references: the studies)** and are never shown as "Nguồn: <textbook>".
5. **Generation (offline, through the gateway).** For each node, retrieve the chunks that explain it. The generator
   (DeepSeek) writes the scenes, and every study scene cites the chunk ids that support its rule. The output is
   JSON-validated and repaired, and retried with a delay ceiling.
6. **Checks by code:**
   - actions come from the closed list;
   - spotlight targets exist in their examples;
   - examples contain the form taught;
   - narration is graded English (word list, sentence length);
   - Vietnamese is NFC;
   - misconception references exist;
   - every study scene has a citation to a verified source;
   - no overlap with test items;
   - the length estimate is 90–240 s.
7. **Blind check by a different model family.** The checker answers each scene's concept questions from the cited
   chunks only; a mismatch makes the lesson `needs_review`.
   - **Who checks.** The owner chose free OpenRouter models (17 Nov): Baidu's Ernie
     (`baidu/ernie-5.5-flash-preview:free`), with `dots-studio/dots-3-note-preview:free` as backup. They are routed
     only for the gateway's `lesson_check` task, and never from DeepSeek, the generator's family.
   - **Why it is allowed.** Free models may use what they are sent, so they only ever see our lesson drafts and source
     chunks, never learner data. The gateway allows `:free` models for `lesson_check` only.
   - **How it was chosen.** `app/evalkit/verifier_pick.py` ran on `evals/verifier/planted-grammar.yaml`: 20 planted
     grammar errors and 20 correct checkpoints.
     - Round 1 (12 items, 4 models): Ernie and dots both caught 6/6, with no false alarms.
     - Round 2 (all 40, 18 Nov): Ernie caught **20/20** (95% interval 83–100%), with **0/20** false alarms (0–17%) and
       0 unusable answers.
     - The bar was at least 18/20 caught, at most 2/20 false alarms and at most 1 unusable. Reports:
       `evals/baselines/verifier-pick-screen.json` and `verifier-pick-ernie.json`.
   - **Built (18 Nov): `app/lessons/blind_check.py`.**
     - **What the checker sees:** the lesson's teaching text (narration, examples, board) and the text of the
       chunks it cites. It never sees checkpoints' keys or explanations.
     - **How it answers:** each checkpoint in turn, with the options sorted. An answer that differs from the key,
       or no usable answer, makes the lesson `needs_review`.
     - **Who it may be:** it goes through the gateway's `lesson_check` route. A `verification_scope` names the
       lesson's generator family, so the checker can never be the writer's family.
     - **Its report** names the checker model and what the check was grounded on.
     - **First run, on the sample lesson** (written by Claude, so not grounded on cited chunks): Ernie agreed with
       both keys, so the lesson passed (`evals/lessons/present-perfect-vs-past.json`).
     - **Planted wrong key:** with "last January" marked correct in a copy of the lesson, Ernie chose "since
       January", and the lesson went to `needs_review`.
     - **Not done yet:** lessons with cited chunks wait for the library (phase B2), so the CLI refuses them for now.
       The check is not yet run automatically when lessons are generated (B3).
     - Run it with:
       `uv run python -m app.lessons.blind_check <lesson.yaml> --generator-family deepseek --out <json>`
   - **Limits.** With no credit on the account, OpenRouter allows 50 free requests a day and 20 a minute. A preview
     model can change or disappear: rerun the 40-item test before each batch of lessons, and switch to dots if Ernie
     fails the bar. The check reduces errors, it does not remove them, so owner review (step 8) stays.
8. **Owner review.** Lessons stay labelled "Bản nháp — chưa được giáo viên duyệt" until the owner accepts them.
9. **On the page:** "Nguồn: <book>, chương <n> (<licence>)" under each study scene.

## The grammar path
The path is written in `path.md` and machine-checked in `english-ielts-path.yaml` (28 milestones, 51 nodes; not live).
The list below is the first proposal; `path.md` is the current one.

### First proposal (from the study's section 5)
The present roadmap has 10 milestones. Proposed additions are marked **+**. None is added without the owner's OK, and
each new node needs items before it is live.
- **A1–A2:**
  - present tenses;
  - nouns and articles **+ countable/uncountable, quantifiers**;
  - **+ pronouns and possessives**;
  - past simple and the future;
  - **+ modals: can, must, have to**;
  - comparison;
  - **+ prepositions of time and place**.
- **B1:**
  - present perfect;
  - conditionals 0/1/2;
  - passive (present and past);
  - **+ gerund or infinitive**;
  - **+ defining relative clauses**;
  - **+ modals: should, might, may**;
  - **+ used to**;
  - **+ linking words: because, although, however** (IELTS coherence).
- **B2:**
  - narrative tenses;
  - conditional 3;
  - **+ passive in all tenses, "it is said that"**;
  - **+ reported speech**;
  - **+ non-defining relative clauses**;
  - **+ modals of deduction**;
  - **+ articles, advanced** (generic and zero article; the spiral for Vietnamese learners);
  - **+ agreement with long subjects**;
  - **+ noun phrases and nominalisation** (academic writing).
- **C1:**
  - mixed conditionals;
  - **+ participle clauses**;
  - **+ inversion and cleft sentences**;
  - **+ hedging** (IELTS Writing Task 2).

## Phases and gates (each gate is measured)
| | What | Gate |
|---|---|---|
| A | This spec and the study | The owner decides (done 17 Nov; the path additions are still open) |
| B1 | Action language, schema and checks; the player (board, spotlight, English voice, EN and VI subtitles, controls) with one fixture lesson written for tests, labelled as a sample, never shown as real | Player tests, a Playwright test, phone screenshots |
| B2 | Source library: the owner verifies at least one grammar source; fetch, chunk, embed and index it | Chunks with licence and page recorded; retrieval hit rate on 20 labelled node queries |
| B3 | Three pilot lessons generated from the library (present perfect vs past, conditionals 1 and 2, articles) and reviewed | The owner rates each 1–5 for clarity; the checks pass; 2–3 minutes each |
| C | Every node and milestone of the roadmap; review queue | Share accepted without edits, with an interval; blind-check disagreement rate |
| D | "Hỏi Sena" (grounded in the lesson and its chunks, hint-leak check, within the plans); engine-chosen scenes | No key leaks on a planted set; every replay shown in the trace |
| E | Later: the same player for other subjects (topic research with figure specs and cited chunks) | Decided then |

**Does it help?** We compare first-try accuracy on a node's questions with the lesson seen versus skipped, count
remediation loops per node, and record where in the lesson learners stop. With one or a few learners the numbers will
be too small to prove anything; the report says so.

## Cost
- Playback costs nothing per learner.
- Generating all the lessons offline costs a few cents of model calls (the vocabulary import used US$0.12 for 92 calls).
- "Hỏi Sena" is bounded by the plans.
- No new dependency is planned for B1.

## Still open for the owner
- [ ] The path (`path.md`): which new milestones go live first
- [ ] The source gaps, articles above all: look for one more source (recommended), write lessons ourselves labelled as
  such, or leave those nodes without a lesson
- [x] Licences of the grammar sources read (17 Nov, by the agent at the owner's request)
- [x] The blind checker for B3 and later (owner, 17 Nov: free Ernie with dots as backup instead of a Gemini key;
      passed the 40-item test on 18 Nov)
