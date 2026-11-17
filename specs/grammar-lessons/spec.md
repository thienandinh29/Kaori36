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
- **Two subtitles under the board**: English (the target form highlighted) and Vietnamese. Each can be switched off;
  both are on by default.
- **The narration is graded English, checked by code.** Every word is in the word list (`core-seed` with the
  NGSL/NAWL import) at or below the lesson's level, apart from the grammar terms the lesson introduces. Sentences are
  short (at most 15 words for A1–A2 lessons, 20 for B1+).
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
1. **Sources.**
   - Candidates are listed in `data/sources/english-candidates.yaml` (study, section 9).
   - The owner reads each licence on its own page and marks it `verified`.
   - NoDerivatives sources are never used. NonCommercial sources are flagged. CC BY-SA material goes in `data-sa/`.
   - The first candidates are Al Haider (CC BY, B2–C1 academic), Explorations 1 (CC BY-NC-SA, A1–A2) and Wikibooks
     English Grammar.
2. **Library.**
   - Fetch only from the source's own site, with the licence and URL recorded per chapter (`app/sources/`).
   - Chunk with chapter and section kept, then embed with bge-m3. Embedding runs where it can: the GPU notebook route
     in `specs/cited-items/`, or TEI on a machine that can run it.
   - The library is indexed per source.
3. **Generation (offline, through the gateway).** For each node, retrieve the chunks that explain it. The generator
   (DeepSeek) writes the scenes, and every study scene cites the chunk ids that support its rule. The output is
   JSON-validated and repaired, and retried with a delay ceiling.
4. **Checks by code:**
   - actions come from the closed list;
   - spotlight targets exist in their examples;
   - examples contain the form taught;
   - narration is graded English (word list, sentence length);
   - Vietnamese is NFC;
   - misconception references exist;
   - every study scene has a citation to a verified source;
   - no overlap with test items;
   - the length estimate is 90–240 s.
5. **Blind check by a different model family (Gemini).** It answers each scene's concept questions from the cited
   chunks only; a mismatch makes the lesson `needs_review`. This needs the Gemini key, which is still pending.
6. **Owner review.** Lessons stay labelled "Bản nháp — chưa được giáo viên duyệt" until the owner accepts them.
7. **On the page:** "Nguồn: <book>, chương <n> (<licence>)" under each study scene.

## The grammar path (proposed, from the study's section 5)
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
- [ ] The proposed path additions (all, some, or later)
- [ ] Verify the licence of at least one grammar source; Al Haider (CC BY, B2–C1) is recommended first
- [ ] The Gemini key for the blind check (B3 and later)
