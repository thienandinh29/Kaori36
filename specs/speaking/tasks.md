# Tasks: Speaking (phase 5)

**Owner's decisions, before 5.1 starts:**
- [x] The recognition model (27 Nov): Whisper small.en, int8, with the verbatim prompt; size measured on the laptop by the owner (`step-5.1.md`). Was: the recognition model and its size (after reading its card and measuring speed and memory on your machine). Study with measurements: `docs/v2/asr-candidates.md` (19 Nov; recommended: Whisper small.en via faster-whisper with a verbatim prompt, silence trimmed, grammar flags shown as hints until measured)
- [ ] The voice policy from phase 3 (audio and transcripts), and the consent wording for transcripts sent to a model
- [x] The band (20 Nov 2026, changed 27 Nov 2026): never from an LLM, never a point or per criterion; a CEFR level with its IELTS range, labelled an estimate, only from a model trained on human-rated speech that passes SPK-001's bar; the owner's band comes from the progress study's rated mocks (`spec.md`, "The band")
- [ ] The Speak & Improve Corpus 2025 licence read in full and signed on Cambridge's ELiT site; answer the three questions in `research/experiments/SPK-001.yaml` (`data.licence`)
- [ ] Accounts and limits for testers (the project has one learner and no login today)

**Owner's hands-on work:**
- [ ] Record 20 answers and type what you said, word for word, for the word error rate; mark the grammar flags right or wrong
- [ ] Write the cue cards and Part 1 and Part 3 questions (authored, not copied from past papers)
- [ ] Recruit 10 testers and run the 2-week retention measure; collect later essays to see old errors fall
- [ ] SPK-001 (after 5.1–5.2 and the licence): fit the models, evaluate on held-out speakers, write the report (negative results kept)

**Build (agent), in order:**
- [x] 5.4a the examiner test before transcription (`step-5.4a.md`, owner's go-ahead 27 Nov): voice examiner, real timing, answers recorded, replay; no model call
- [x] 5.1 recognition service `asr/`, transcripts of the examiner test's answers, word error rate tool (`step-5.1.md`, 27 Nov)
- [x] 5.2 fluency measures, with pauses between and inside clauses (`step-5.2.md`, 28 Nov)
- [x] 5.3a transcript checks by code (`step-5.3.md`, 28 Nov): grammar hints, endings apart, vocabulary numbers, the memorised-phrase check
- [ ] 5.3b the model's feedback with checked quotes: waits on the owner's transcript consent wording
- [x] 5.4b guided mode (`step-5.4b.md`, 28 Nov; the strict mock is 5.4a): idea building for Part 2/3 (no scripts), the same question up to three times with shrinking time, numbers side by side; was: 5.4 mock test flow (no band); guided mode: idea building for Part 2/3 (no scripts), the same question up to three times with shrinking time
- [x] 5.5 invite links, limits, tester report (`step-5.5.md`, 28 Nov; shut until the privacy review: `TESTERS_MAY_RECORD`); the cost cap applies from 5.3b
- [ ] 5.6 SPK-001's corpus loader and measures on its audio; the level on the result page only after the bar
