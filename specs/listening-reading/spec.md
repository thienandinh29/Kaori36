# Spec: Listening and Reading (phase 4 of `docs/v2/plan-english-pack.md`)

Document only: nothing here is built. IELTS-style Reading and Listening practice from **open-licensed texts**, with questions
generated ahead, **answered blind by a model of a different family**, and **reviewed by the owner** before any learner sees them.
The pack's principle holds: the LLM writes and explains, code and a second model check, the engine decides what comes next.

## What the learner sees
Reading: a text (levelled), then questions of one type at a time. Listening: audio (played once or twice, as chosen), then the
questions. After each answer: right or wrong from the answer key (never from a model), the passage sentence that decides it
highlighted, and a Vietnamese explanation drawn from that sentence. Everything generated is labelled "Bản nháp tự động" until the
owner has reviewed it.

## Question types (start with what code can grade)
True / False / Not Given; multiple choice; sentence and short-answer completion (typed, graded exactly after normalisation, as in
vocabulary); matching headings to paragraphs. Later: summary completion, form and note completion for Listening. **Not planned:**
map and diagram labelling, matching sentence endings. Skills tagged per question (detail, main idea, inference, writer's view,
skimming) become the hidden nodes of a Reading and a Listening milestone (the owner's roadmap work).

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
