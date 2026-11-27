# Step 4.3e (plan CP4b): skill tags on Reading questions, and time per question

Proposed 27 Nov 2026, approved by the owner the same day. It comes from the owner's research on cognitive diagnostic assessment
(CDA; Bronze, citations to check). Today each question type moves **one** Reading competency (`reading-detail`, `-main-idea`,
`-inference`, `-writers-view`, `-skimming`), so the app knows which *types* go wrong but not which *skill* inside a question
failed. This step adds a skill tag to each question (the "Q-matrix" of the CDA literature) and records time and answer changes in
the timed test. Both are measured before anything is diagnosed from them. The statistical model (CDM) is research, not product:
`research/experiments/DIAG-001.yaml`.

## (a) Skill tags (the Q-matrix)
**The sub-skills** (a closed list; code refuses any other):

| Tag | Vietnamese name | What the question needs |
|---|---|---|
| `scan_detail` | Tìm chi tiết | finding the sentence that holds a name, number or fact |
| `paraphrase` | Nhận ra cách nói khác | matching the question's wording to different words in the passage |
| `inference` | Suy luận | a conclusion the passage implies but does not state |
| `vocab_context` | Từ vựng trong ngữ cảnh | knowing a word or phrase as used in this passage |
| `fng_logic` | Phân biệt SAI và KHÔNG CÓ THÔNG TIN | telling "the passage says the opposite" from "the passage does not say" |
| `main_idea` | Ý chính của đoạn | the point of a paragraph, as opposed to a detail in it |

Each question gets **1 to 3 tags**.
- **Bank questions:** the generator proposes the tags in the same DeepSeek call as CP4b's explanations (step 1 there), so this
  costs no extra call. The blind checker (Ernie, `reading_check`) gets the passage, the question and the tag list (not the
  proposed tags) and picks the tags it thinks apply. Where both agree, the tag is kept. Agreement is Silver only for
  *serving*. It never makes a tag true.
- **Pasted tests (4.3d):** code proposes tags from the question type (T/F/NG → `scan_detail`, `paraphrase`, `fng_logic`;
  completion → `scan_detail`, `vocab_context`; …). On the check step the learner may untick one. No model call.
- **Tier:** every tag is **Bronze** until a teacher labels a sample of 50 questions blind on the portal (`/kiem-duyet`, a new
  task kind `reading_skills`). Agreement with the teacher is per tag, with Cohen's kappa and an exact interval. Below κ 0.6 on a
  tag, that tag is dropped from the learner's summary until it is redefined.

**What the tags change for the learner:** only the summary across tests (4.3d part 2) and "Theo dạng câu hỏi" (CP4b step 3). They
gain a line per sub-skill ("Nhận ra cách nói khác: sai 6/11"), from 8 tagged answers, with an exact 95% interval and the label
"đề xuất, chưa được giáo viên kiểm tra".

**What they do not change (owner's decision, 27 Nov):** BKT. A question still moves exactly one competency, as today. Letting one
question update several skills is an engine change: it would need its own spec, a rule for splitting the evidence, and the
recommendation simulation gate. It is reconsidered only after the teacher's sample shows the tags agree.

## (b) Time and answer changes in the timed test (`/doc/{slug}/thi`)
- The test page records, for each question, the seconds it was in view and how many times the answer changed before submit.
  It sends them with the submission. The server stores them and does not trust them for anything but description (the clock
  that decides "late" stays the server's).
- `reading_answers` gains nullable `seconds_on` (integer) and `changes` (smallint) in an additive migration (`0041`, at build
  time). Practice answers leave them empty.
- **Shown:** nothing, until 3 timed tests exist. Then the result page shows seconds per question next to the key, with no
  judgement. No rule reads them yet: they are the data that DIAG-001 and KT-001 need later.
- Pasted tests (4.3d) were taken outside the app, so they have no time data. They use the learner's own marks instead
  (4.3d part 2, "Position and pacing").

## Not claimed
That the six sub-skills can be told apart. Studies of CDMs on reading tests often find the sub-skills so correlated that the
data behaves almost like one skill. With one learner, nothing here can test that. DIAG-001 tests it on a public dataset. Until
then the per-skill lines are descriptive counts, not a diagnosis.

## Build order (one PR each)
1. The tag list, code's checks, tags in CP4b's generation call and the blind pick; the tag proposal for pasted tests.
2. The per-skill lines in the summaries.
3. Time and answer changes in the timed test (migration `0041`).
4. The portal task for the teacher's 50 labels (when a teacher is found).
