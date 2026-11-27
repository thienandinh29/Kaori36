# Spec: Listening and Reading (phase 4 of `docs/v2/plan-english-pack.md`)

Document only: nothing here is built. IELTS-style Reading and Listening practice from **open-licensed texts**, with questions
generated ahead, **answered blind by a model of a different family**, and **reviewed by the owner** before any learner sees them.
The pack's principle holds: the LLM writes and explains, code and a second model check, the engine decides what comes next.

## What the learner sees
Reading: a text (levelled), then questions of one type at a time. Listening: audio (played once or twice, as chosen), then the
questions. After each answer: right or wrong from the answer key (never from a model), the passage sentence that decides it
highlighted, and a Vietnamese explanation drawn from that sentence (CP4b below: why the key is right and why the chosen
answer was tempting). Everything generated is labelled "Bản nháp tự động" until the
owner has reviewed it.

## Why the wrong answer tempted you (CP4b; specified 20 Nov 2026, not built)
From the owner's research on IELTS platforms (20 Nov 2026, Bronze: a report with citations to check). Learners rate a bare key
("Correct: C") as the weakest feedback and ask for the trap to be named: NOT GIVEN against FALSE, a word copied from the passage, a
paraphrase missed. Whether naming the trap raises *later* accuracy, rather than satisfaction, is not shown by any trial the report
cites, so it is a hypothesis we record, never a promise.

**What the learner sees**, after answering (practice, a timed test's results, "Nghe cả bài" results):
- **Wrong:** the trap their choice fell into, by its Vietnamese name; one or two Vietnamese sentences on why it is wrong, quoting
  the passage words it rests on; then why the key is right, quoting the deciding sentence.
- **Right:** why the key is right, in a sentence; the other options' explanations one tap away ("Vì sao các lựa chọn khác sai?").
- Labelled "Giải thích tự động, đã kiểm tra chéo bằng máy; chưa được giáo viên duyệt". "Giải thích này sai?" hides it for the
  learner and records a flag (Bronze feedback; a flag can hide an explanation, never promote one).
- **No explanation passed its checks:** the question is still served, with the deciding sentence only (as today).

**The traps** (a closed list; code refuses any other):

| Kind | Trap | Vietnamese name | Who names it |
|---|---|---|---|
| T/F/NG | the pair chosen/key, e.g. FALSE chosen, NOT GIVEN key | "Nhầm SAI với KHÔNG CÓ THÔNG TIN" (and the other five pairs) | code, from the answer and the key |
| Multiple choice | `word_match` | Lặp từ trong bài nhưng sai nghĩa | the generator, checked |
| | `partly_true` | Đúng một phần | |
| | `wrong_part` | Đúng ở chỗ khác trong bài, không trả lời câu này | |
| | `opposite` | Ngược với bài | |
| | `not_stated` | Bài không nói điều này | |
| | `outside_knowledge` | Đúng ngoài đời nhưng bài không nói | |
| | `extreme` | Quá tuyệt đối (all, never, only…) | |
| Completion | `too_many_words`, `wrong_form`, `spelling`, `other` | Quá số từ cho phép, Sai dạng từ, Sai chính tả, Khác | code, from the typed answer (word count; a shared stem with the key; edit distance ≤ 2) |
| Headings | `detail_not_main`, `word_match`, `wrong_part` | Chỉ là một chi tiết, không phải ý chính… | the generator, checked |

**Generation** (offline, a worker CLI like 4.2b; never in a request): one DeepSeek call per **approved** question through the
gateway (a new task `reading_explain`), given the passage, the question in the stored order, the key and its evidence. It returns,
for the key, `why_vi` and `quotes`; for each wrong option (multiple choice) or paragraph (headings), `trap`, `why_vi` and `quotes`;
for T/F/NG and completion only the key's part (code names the trap). Every call in `llm_calls`, capped by `--max-cost`. An
explanation stores the passage's and the question's fingerprints: if either changes, it is dropped.

**Code checks:** every quote is in the passage (the same normalisation as question evidence); the key's quote is, or overlaps, the
question's evidence (for a NOT GIVEN key there is no deciding sentence: the closest related sentence is quoted, and the text must
say what the passage does *not* state); the trap is on the list and allowed for the kind; the key is never given a trap; `why_vi`
is 20–400 characters and in Vietnamese apart from quotes.

**Check by another family** (free Ernie, task `reading_check`, like the questions): one request per question. The checker gets the
passage and the explanations as numbered claims, is not told the key, and marks each claim *supported* or *not supported* by the
passage alone. A wrong option's claim not supported drops that explanation; the key's not supported drops them all. Code checks plus
this check agreeing is Silver, enough to show with the label above. Whether Ernie can judge Vietnamese explanations is the first
thing measured (the gate below); if it cannot, this stops and comes back to the owner with options (an English claim checked
instead, or the dots model).

**The gate before anything is shown:** a planted test from real generated explanations: 20 with a planted fault (a claim the passage
contradicts, a quote from another paragraph, a trap that does not fit, a key explanation that argues for a wrong option) and 20
good ones. Bar: the checker catches ≥ 18/20 with ≤ 2/20 false alarms (the bar the lesson checker met), exact intervals
(`evalkit/stats.py`). The faults are planted by construction; the owner only confirms each one is really a fault. Later, a
teacher's sample of 30 shown explanations (Gold, the portal) gives the escape rate with its upper bound (`validation/gate.py`).

**Question types and traps over time:**
- `reading_answers` and `listening_answers` gain a nullable `trap` (the trap of the chosen wrong answer, by code from the stored
  explanation or the rules above). Additive migration with the new `reading_explanations` table.
- "Theo dạng câu hỏi" on `/doc`: per type (T/F/NG, multiple choice, completion, headings), last 30 days: answers, right, the share
  with an exact 95% interval, and the most frequent trap ("Bạn hay nhầm SAI với KHÔNG CÓ THÔNG TIN: 5 trong 8 lần sai"). From 5
  answers per type; fewer is "chưa đủ dữ liệu".
- **Hôm nay:** the engine's choice of skill is unchanged (the engine and its simulation gate are not touched). The Reading
  activity's link opens the text with the most unanswered questions of the learner's weakest type (lowest share, at least 8
  answers, at least 15 points below their other types), and "Vì sao?" says so.

**Not claimed:** that the explanations improve later accuracy. The trap rate on later questions of the same type is recorded;
with one learner it is learner feedback (Bronze), not a result. A real test of it goes to `research/` with a hypothesis first.

**Cost:** about one DeepSeek call per approved question (passage-sized prompts; estimated under US$0.50 per 100 questions, capped)
and one free Ernie request per question, sharing the 50-a-day limit with the questions' blind checks, so it runs after those
finish (182 left on 20 Nov, about four daily batches) or on alternate days.

**Steps, one PR each:** (1) migration, generation, code checks, the planted-test tooling, run on the approved questions;
(2) explanations on the learner pages and the flag; (3) "Theo dạng câu hỏi" and the Hôm nay link.

**Step 1 split in two (27 Nov 2026, to keep each PR spec-sized):** (1a) migration, generation, code checks and the run;
(1b) the blind check by another family and the planted-test tooling. **1a built:** `app/reading/explain.py` (pure: output
shape, prompt, checks), `app/reading/explain_run.py` (`python -m app.reading.explain_run [--max-cost 0.10]
[--include-verified N]`), gateway task `reading_explain` (DeepSeek), migration `0047` (`reading_explanations`: one row per
question version, `checked` or `dropped` with its problems, and the 4.3e skill tags). Choices made while building:
- **Headings are not explained yet** (a trap per paragraph needs its own design); T/F/NG, multiple choice and completion are.
- **An explanation never names an option by letter** (learners see options shuffled, 4.3c): code refuses "đáp án A" and the like.
- **The skill tags come in the same call** (`step-4.3e.md`), checked against the closed list; no blind pick yet.
- `--include-verified N` explains verified, not-yet-approved questions too, only to build the planted test of 1b. Nothing in
  this step reaches a learner.
- **First real run (27 Nov, deepseek-flash, scratch database):** the 2 approved questions and 8 verified ones (5 T/F/NG, 2
  completion, 2 multiple choice); 9 passed code's checks first time. The one drop was code's false alarm: "không hề nói" and
  "không được đề cập" were not in the NOT GIVEN pattern (fixed, with a test), then 10 of 10. 11 calls, about 12,000 tokens in
  and 2,800 out (US$0.024 at the configured prices, which are set above DeepSeek's). Two things this run shows for 1b: a
  multiple-choice explanation places a quote "in the last paragraph", which code does not check; and the explanation of the
  approved `os-introduction-sociolo-elements-of-culture-tfng-2` (key NOT GIVEN) quotes "will likely be fired" against "reward",
  which reads like FALSE: a question for a teacher (Bronze), not changed here. The run's rows stay in the scratch database:
  explanations are not exported to the item files yet, so the daily batch's laptop run makes its own.

## Question types (start with what code can grade)
True / False / Not Given; multiple choice; sentence and short-answer completion (typed, graded exactly after normalisation, as in
vocabulary); matching headings to paragraphs. Later: summary completion, form and note completion for Listening. **Not planned:**
map and diagram labelling, matching sentence endings. Skills tagged per question (detail, main idea, inference, writer's view,
skimming) become the hidden nodes of a Reading and a Listening milestone (the owner's roadmap work).

**Skill tags and time per question** (`step-4.3e.md`, approved 27 Nov 2026): each question also carries 1–3 sub-skill tags from
a closed list of six (the Q-matrix of cognitive diagnosis), Bronze until a teacher labels 50. They feed the summaries only and
never BKT, where a question still moves one competency. The timed test records seconds on each question and answer changes,
shown without judgement. A cognitive diagnosis model is research on a public dataset (`research/experiments/DIAG-001.yaml`), not
a product feature: one learner cannot calibrate it.

## Texts and licences
- Candidates (all marked "to check" in `data/sources/english-candidates.yaml`; the owner reads each licence on its own page, and
  `app/sources/licence.py` refuses NoDerivatives): Simple English Wikipedia and Wikinews, Wikibooks, OpenStax (CC BY), Project
  Gutenberg (public domain, but old-fashioned English), LibriVox (public-domain audio), Common Voice (CC0, short sentences only).
  VOA Learning English is a plausible source whose terms I have not checked: it is a question for the owner, not an assumption.
- **ShareAlike (CC BY-SA) is not free of strings**: a bank built from such texts must itself be shared alike. Fine for a free
  study tool; a decision before any paid tier. NonCommercial sources are flagged the same way.
- Every text carries its source, licence and the date the owner checked it (the existing source catalogue records this).
- **Level of a text:** measured features (sentence length, share of words outside the A1–B1 list once a licensed word list exists)
  plus the owner's CEFR label on 30 texts to see how well the features track it. No claim of CEFR accuracy beyond that measurement.

## Audio
- **Text to speech** (candidate: Piper, a local engine; its Hugging Face repository `rhasspy/piper-voices` is MIT, **but each voice has
  its own model card and training-data licence, to be read per voice**). Cheap and unlimited, but the voices are uniform and unlike
  real conversations or the accents of the exam (British, Australian, New Zealand, North American). Labelled "giọng đọc máy".
- **Real recordings:** LibriVox (read books) and Common Voice (one sentence each) are natural speech but not exam-like dialogue.
- A realistic Listening bank needs real recordings of conversations and lectures, which open sources barely offer; so early
  Listening is honest practice in **understanding spoken English at the learner's level**, not a mock of the exam's four sections.

## Pipeline (worker, through the gateway; never in a request)
text → generator (DeepSeek) writes questions citing the passage sentences they rest on → **verifier of a different family** gets
only the passage and the question, answers blind, answer compared with the key → mismatch or "unanswerable" = `needs_review`, not
served → owner's review queue → only `verified` **and** approved items enter the bank. This reuses the verification gate already
specified (`SPEC.md`) and built for the contest content (`app/guardrails/`, `app/content/`).
- **The verifier needs a key the owner does not have yet** (Gemini was the contest choice; `.env.example` has the slot). The gateway
  refuses `:free` OpenRouter models on purpose (their prompts may be logged or trained on). A different-family verifier is a
  decision: a Gemini key on the paid tier, or another provider; until then items stay `needs_review`.

## The gate (from the plan)
1. **Blind-verifier catch rate:** the owner plants errors in 50 items (wrong key, answer not in the passage, two defensible
   answers); report how many the verifier catches and how many correct items it wrongly rejects, with exact intervals.
2. **Agreement:** the owner labels 50 generated items as good or not; report agreement with the verifier and Cohen's kappa
   (`evalkit/stats.py` has both).
3. **Answerability and review:** every banked item passed the verifier and was reviewed; the bank's size per type and level.
4. Per-skill mastery nodes use the same BKT as grammar; item difficulty (Elo) stays parked.

## Steps
| Step | Work |
|---|---|
| 4.1 | Licence checks and a text bank: fetch with the source catalogue, record licence per text, level features |
| 4.2 | Reading items: generation, blind verification, the owner's review queue (a page), the planted-error test |
| 4.3 | Reading practice in the browser; skill nodes and BKT evidence; explanations from the deciding sentence |
| 4.4 | Listening: audio from TTS or recordings, the same items on audio, dictation and gap-fill |
| 4.5 | The gate report `docs/v2/reading-listening-eval.md` |

## Risks
Questions that are answerable from outside knowledge (the blind verifier catches some); two defensible answers; leaking the answer in
the question stem; level mismatch; share-alike obligations; TTS that teaches a robotic accent; the owner's time to review (budget:
about 10 items an hour, so a 200-item bank is 20 hours).
Not in this phase: Speaking (phase 5), a Reading or Listening band, real exam passages.
