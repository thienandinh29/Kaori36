# Spec: Speaking (phase 5 of `docs/v2/plan-english-pack.md`)

Document only: nothing here is built. IELTS-style Speaking practice: the learner speaks, a model transcribes, tools measure how they
spoke and what they said, a model explains with quotes checked against the transcript. **No band in the first version** (see "The
band", below): the honest first product is measures and feedback.

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
like the exam leaves the exam's pressure untrained. Feedback in both separates what the audio shows (pace, pauses) from what the
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
- **Measures by code** from word timestamps: speech rate (words per minute), articulation rate (excluding pauses), the number and
  length of pauses (a pause is a gap above a set length, proposed 0.5 s, and a long pause 2 s), filler words ("um", "uh", "er",
  "you know", "like" as a filler is not detectable by code and is not claimed), the longest fluent run, answer length against
  the time asked. These are numbers about speaking, never a verdict on quality.
- **Grammar and vocabulary on the transcript:** LanguageTool and ERRANT as for writing, with two honest problems to measure:
  spoken grammar is not written grammar (false alarms), and the recogniser may "correct" the learner's errors or mishear a
  non-native accent (missed and invented errors). The owner types the reference for 20 recordings; report the word error rate
  with an interval, and the rate of grammar flags the owner judges wrong. Until then these flags are hints, shown as such.
- **Pronunciation:** only on read-aloud prompts, from phase 3. In free speech the intended phones are unknown, so phone-level marks
  would be guesses; free-speech pronunciation is not marked.

## The band (a decision, with a limit stated up front)
IELTS Speaking has four criteria (Fluency and Coherence, Lexical Resource, Grammatical Range and Accuracy, Pronunciation). I know of
no public set of speaking recordings with examiner bands to calibrate against, and without one a band would be an unvalidated guess.
Proposal: **no band until the owner has 30 or more recordings rated by a qualified teacher or examiner**; then the same method as
writing (a held-out split set aside first, QWK with an interval, a range never a point, "không chắc" when wide). If no such ratings
can be had, the product stays measures and feedback, which is a legitimate product.

## Limits and privacy
Cost: the model sees transcripts only (a few hundred words), so the writing budget applies; transcription runs on our machines.
Privacy: the phase 3 voice policy covers audio; a transcript is personal text and needs the same consent as an essay (sent to a model
provider). Children and recording environments: as in phase 3.

## The phase gate (from the plan)
Per-user limits and a daily cost cap working; at least 5 of 10 testers still using it after 2 weeks; old errors falling in later
essays over 4 weeks (the writing and speaking loop working); the word error rate and grammar-flag measurements above.

## Steps
| Step | Work |
|---|---|
| 5.1 | Recording and prompts for the three parts, the recognition service, transcript and timestamps; word error rate on the owner's recordings |
| 5.2 | Fluency measures and the pause analysis |
| 5.3 | Grammar and vocabulary checks on the transcript; feedback with quotes checked against it |
| 5.4 | The mock test flow with timing; the band decision once ratings exist |
| 5.5 | Opening to testers: accounts, per-user limits, the daily cost cap, the tester report |

Not in this phase: a native-like or accent score, intonation, an automatic band without ratings.

## The owner's direction (17 Nov 2026)
First help learners pronounce correctly (phase 3). Then a **simulated IELTS Speaking test** that uses both: pronunciation from
phase 3 and what the learner says (transcript, grammar, vocabulary, the answer to the question), in the three parts of the test.
The band rule above still holds: no band until rated recordings exist.
