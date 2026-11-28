# Spec: Speaking (phase 5 of `docs/v2/plan-english-pack.md`)

Document only: nothing here is built. IELTS-style Speaking practice: the learner speaks, a model transcribes, tools measure how they
spoke and what they said, a model explains with quotes checked against the transcript. **No band in the first version** (see "The
band", below): the honest first product is measures and feedback; a level estimate comes only after research track SPK-001
passes its bar.

## What the learner sees
A part of the test (Part 1 short questions; Part 2 a cue card with one minute to prepare and up to two minutes to speak; Part 3
discussion), a timer, a record button. Then: the transcript, how they spoke (speech rate, pauses, fillers), what to improve with
quotes from their own words, and a retry. Voice data follows the policy decided in phase 3.

## Two modes (added 20 Nov 2026 from the owner's research, Bronze)
- **Luyện có hướng dẫn (guided):** one question at a time; after the turn, hints and words to use, then a retry; shadowing a model
  answer on read-aloud prompts.
- **Thi thử (strict exam):** the real timing (Part 1 about 4–5 minutes, Part 2 one minute to prepare and up to two to speak, Part 3
  about 4–5 minutes), no hint or pop-up while recording, everything shown only after the part ends.
Two reasons from the report: live hints during speech raise load and anxiety in the studies it cites, and practice that never feels
like the exam leaves the exam's pressure untrained.

**Inside guided mode (added 20 Nov 2026, owner's decision):**
- **Idea building for Part 2 and Part 3, never scripts.** Before speaking, the learner gets a way to build an answer, not an answer:
  a shape (point → reason → example → link back to the question; for Part 3 also compare, give the other side, say why it
  matters), two or three questions that open the topic up (who, why, what changed, what if), and topic words from the vocabulary
  list. Then the learner answers in their own words. NodeTrail never writes a model answer to memorise: memorised answers are
  discounted by examiners, and the memorised-phrase check (writing step 2.7) runs on the transcript here too. Part 3, where
  Vietnamese candidates are reported to stall on abstract opinions, gets the most of this help.
- **The same question again, to build fluency.** After an answer and its feedback, the learner can answer the same question again,
  up to three times, with the time allowed shrinking (for example 2 minutes, then 1.5, then 1; a task-repetition technique from
  language teaching, Bronze until measured on the owner's own recordings). Each try shows its fluency measures next to the last
  (speech rate, pauses per minute, longest fluent run), as numbers, never a verdict. Only the first try on a question counts as
  evidence of fluency; repeats are practice, because a rehearsed answer is not spontaneous speech.
- **What is measured for these two:** whether answers reach the time asked and run out of ideas less often (answer length against
  time, long pauses near the end), and whether pauses fall between the first and third try. Reported on the owner's data as an
  N-of-1 check, not as a claim that the technique works. Feedback in both separates what the audio shows (pace, pauses) from what the
transcript shows (words, grammar).

**Priority (for the owner):** the report cites IELTS's 2024–2025 test-taker data with Speaking as the lowest Academic skill for
Vietnamese candidates (mean 5.61; to be checked on IELTS's own test-taker performance page). Since the overall band is the mean of
the four skills rounded to the nearest half, the weakest skill caps it, which argues for starting phase 5 right after phase 4's
CP6 report rather than after exam-format Listening.

## Pipeline (worker or a service; never in a request)
browser audio (16 kHz mono WAV, as in phase 3) → quality gate → **speech recognition with word timestamps** → measures by code →
grammar and vocabulary checks on the transcript (the writing tools) → feedback by a model that sees only the transcript →
quotes checked to be exact substrings of the transcript. The model never hears the audio and never produces a number.
- **Recognition (candidates, the owner decides):** Whisper through `faster-whisper` (CTranslate2). The Hugging Face cards read on
  15 Nov 2026: `openai/whisper-small` and `openai/whisper-large-v3` list Apache-2.0; `Systran/faster-whisper-small` lists MIT.
  Model size against speed and memory on the owner's machine is a measurement, not a guess (the Docker VM was measured at about 4 GB).
  Measured candidates and the recommendation (small.en, int8, with a verbatim prompt): `docs/v2/asr-candidates.md`.
- **Recogniser settings (added 20 Nov from the owner's Speaking research, Bronze; each checked in 5.1):** an English-only model
  (multilingual models sent accented English into other languages in a cited study); the verbatim prompt; no conditioning on
  the previous window (`condition_on_previous_text=False`, against repeated loops); voice activity detection so nothing is
  transcribed over silence; words shorter than 50 ms dropped (looping artefacts). No PyTorch in this service (CTranslate2 only).
- **Pauses come from the raw audio, before voice activity filtering.** The filter that stops invented text also removes the
  silences the fluency measures need, so the pause timeline is taken first and the recogniser gets the filtered audio.
- **Checks before any feedback:** the recording-quality check from phase 3 (quiet, clipping, noise); a minimum answer length
  (proposed 15 s; shorter answers get measures only, no language feedback); the prompt-word overlap and memorised-phrase
  checks of writing step 2.7 on the transcript, shown first, as for essays.
- **Measures by code** from word timestamps: speech rate (words per minute), articulation rate (excluding pauses), the number and
  length of pauses (a pause is a gap above a set length, proposed 0.5 s, and a long pause 2 s), filler words ("um", "uh", "er",
  "you know", "like" as a filler is not detectable by code and is not claimed), the longest fluent run, answer length against
  the time asked. These are numbers about speaking, never a verdict on quality.
- **Where the pauses fall (added 27 Nov 2026, owner's decision):** each pause counted as between clauses or inside a clause,
  from the word timings and a parse of the transcript. Studies of second-language fluency link pauses inside a clause to
  searching for a word or a structure, the hesitation the band descriptors hold against a speaker, and pauses between
  clauses to planning content (Tavakoli 2011; de Jong and colleagues; Bronze, citations to check). Shown as two counts per
  minute, never labelled "language-related": code cannot know why someone paused. **The clause ends come from a parse of
  the words only, not from the recogniser's punctuation** (28 Nov, found on the real recogniser: it writes a full stop at a
  long pause, so a pause would decide its own class); fillers are skipped; run-on speech parses unreliably, so boundaries are
  missed and the split is approximate until the owner has checked it on their own answers (`step-5.2.md`).
- **Grammar and vocabulary on the transcript:** LanguageTool and ERRANT as for writing, with two honest problems to measure:
  spoken grammar is not written grammar (false alarms), and the recogniser may "correct" the learner's errors or mishear a
  non-native accent (missed and invented errors). The owner types the reference for 20 recordings; report the word error rate
  with an interval, and the rate of grammar flags the owner judges wrong. Until then these flags are hints, shown as such.
  Grammar flags on speech **never move mastery**. A missing ending (-s, -ed) is the clearest case: Vietnamese speakers often drop
  final /s/, /z/, /t/, /d/ as a sound, so a missing ending in the transcript may be pronunciation, grammar or the recogniser.
  It is shown as "có thể thiếu đuôi -s/-ed" with the audio, never as a grammar error.
- **Uncertain words:** where Whisper and the phone recogniser (phase 3, no language model, so it keeps learner errors better)
  disagree on a word, the word is marked uncertain and gets no grammar feedback. Built after 5.3 if the 20 typed references
  show Whisper hiding errors.
- **Pronunciation:** only on read-aloud prompts, from phase 3. In free speech the intended phones are unknown, so phone-level marks
  would be guesses; free-speech pronunciation is not marked.

## The band (owner's decision, changed 27 Nov 2026)
IELTS Speaking has four criteria (Fluency and Coherence, Lexical Resource, Grammatical Range and Accuracy, Pronunciation). There is
no public set of speaking recordings with IELTS examiner bands to calibrate against. The owner's research confirms there is no
open dataset of Vietnamese learners' speech with IELTS ratings, and no consumer Speaking app publishes a validation against
examiners. A band from a model reading the transcript has nothing behind it: it cannot hear the speech, and its number moves
between runs. It is never shown. A band calibrated on IELTS ratings directly would need 100–200 full tests rated by two trained
raters, balanced by level, region and microphone, with held-out QWK ≥ 0.75 and no bias between groups (the report's bar).

**20 Nov 2026:** no Speaking band before the owner's exam. **27 Nov 2026, owner's decision, replacing it:** a **Speaking level
estimate** may be shown, but only when all of these hold:
- it comes from a model trained on human-rated speech: the Speak & Improve Corpus 2025 (Cambridge University Press & Assessment,
  CEFR-level holistic scores by trained assessors, non-commercial licence), research track SPK-001
  (`research/experiments/SPK-001.yaml`);
- that model reached QWK ≥ 0.75 against the human scores on held-out speakers, with the interval reported, and its errors at B2
  and C1 (where the 7.0 target lies) are reported;
- it is shown as a CEFR level with the IELTS range IELTS publishes for that level (read on IELTS's own page first), labelled
  "ước tính", next to the latest independent rated mock. Never a point such as "7.5", never per criterion (the corpus has
  holistic scores only), never from an LLM;
- only for a full mock test (all three parts) whose recordings pass the quality check and hold enough speech;
- it is checked against the owner's rated mocks as they come (N-of-1). Proposed: if the rater's band falls outside the shown
  range on 2 of the first 3, the estimate is hidden until the cause is known.

Until all of that holds, no level is shown. The corpus's tasks are not IELTS's three parts and its speakers are not chosen to be
Vietnamese, so the check on the owner's rated mocks is the only evidence that the estimate carries over. The owner's Speaking
band still comes from the progress study (`specs/validation/step-v4.md`: an independent mock with a trained rater every 4
weeks). Measures and feedback stay the product; the level is an extra line, and the page says how it was made.

## Limits and privacy
Cost: the model sees transcripts only (a few hundred words), so the writing budget applies; transcription runs on our machines.
Privacy: the phase 3 voice policy covers audio; a transcript is personal text and needs the same consent as an essay (sent to a model
provider). Children and recording environments: as in phase 3.

## The phase gate (from the plan)
Per-user limits and a daily cost cap working; at least 5 of 10 testers still using it after 2 weeks; old errors falling in later
essays over 4 weeks (the writing and speaking loop working); the word error rate and grammar-flag measurements above.

## What the research says practice can and cannot do (Bronze, citations to check)
A meta-analysis the report cites (Ngo et al. 2023, *ReCALL*, 15 studies) found a medium effect of speech-recognition
pronunciation training, larger with explicit corrective feedback and with peers, smaller for solo practice and for stress,
rhythm and intonation. A Vietnamese university study (HNUE) found no gain in the overall IELTS Speaking band from such practice,
with a slight fluency drop while learners monitored their grammar. So: corrections stay explicit and short; the strict mock
mode shows nothing while speaking; and NodeTrail is one part of Speaking practice, next to speaking with a partner or teacher.

## Steps
| Step | Work |
|---|---|
| 5.1 | Recording and prompts for the three parts, the recognition service, transcript and timestamps; word error rate on the owner's recordings. Built 27 Nov (`step-5.1.md`): Whisper small.en in `asr/`, transcripts on `/noi/thi/{id}`, the WER tool; the owner's references and laptop numbers pending |
| 5.2 | Fluency measures and the pause analysis (pauses from the raw audio, before voice activity filtering). Built 28 Nov (`step-5.2.md`): rates, pauses between and inside clauses, fillers, the longest run, shown as numbers under each transcript and pooled for the test; the owner's check on five answers pending |
| 5.3 | Grammar and vocabulary checks on the transcript; feedback with quotes checked against it |
| 5.4a | The examiner test before transcription (`step-5.4a.md`): a voice examiner reads authored Part 1–3 questions with the real timing, each answer recorded, replay afterwards; no model call. Built 27 Nov (owner's go): `/noi/thi` |
| 5.4 | The mock test flow with timing; guided mode with idea building and repeated answers; no band (see "The band") |
| 5.5 | Opening to testers: accounts, per-user limits, the daily cost cap, the tester report |
| 5.6 | Level estimate (SPK-001), after 5.1–5.2 and the corpus licence: the corpus loader and the same measures on its audio (agent); the model and its report (owner); the level on the mock test's result page only after the bar in "The band" |

Not in this phase: a native-like or accent score, intonation, a band from a model's opinion, a band per criterion.

## The owner's direction (17 Nov 2026)
First help learners pronounce correctly (phase 3). Then a **simulated IELTS Speaking test** that uses both: pronunciation from
phase 3 and what the learner says (transcript, grammar, vocabulary, the answer to the question), in the three parts of the test.
The band rule above holds: a level only from a model trained on rated speech, after its bar (changed 27 Nov).
