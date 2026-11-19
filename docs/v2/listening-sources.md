# Listening sources (phase 4, CP5)

For the owner's decision before CP5 (`specs/listening-reading/plan.md`). Read and measured on 19 Nov 2026. Licences are **the
publishers' claims**, mostly from catalogue pages and search results, because several source sites are outside this
environment's network (VOA's own terms page could not be opened here). The owner reads each licence page before choosing, as
for every source in this project.

## What IELTS Listening asks for
Four parts, about 40 questions, each heard once:

| Part | What it is | Typical questions |
|---|---|---|
| 1 | An everyday conversation, two people (a booking, an enquiry) | Form and note completion: names spelled, numbers, prices, dates |
| 2 | An everyday monologue (a tour, an announcement, a talk about facilities) | Multiple choice, map/plan labelling, matching |
| 3 | An academic discussion, two to four people (students and a tutor) | Multiple choice, matching opinions to speakers |
| 4 | An academic lecture, one speaker | Note, summary or table completion |

The spec's honest line stands (`specs/listening-reading/spec.md`): open sources barely offer real recordings of these, so
early Listening is practice in understanding spoken English at the learner's level, not a mock of the exam.

## The candidates
| Source | What it is | Licence (claimed) | Fits | Problems |
|---|---|---|---|---|
| **Our own scripts, voiced by Piper** | Scripts written for each part (by DeepSeek from a scenario, checked like Reading questions), read by the self-hosted voices | Scripts: ours. Voices: per voice, below | All four parts, at any level, with answers designed in | Synthetic voices; scripts need the same verification as Reading questions, plus an audio check (below) |
| **OpenStax passages, voiced** | The 30 bank texts read aloud as mini-lectures | CC BY-NC-SA 4.0 (owner-checked 19 Nov) | Part 4 | Written prose read aloud, not a lecture's spoken style |
| **VOA Learning English** | Graded news for learners, real voices, transcripts | Learning English texts and MP3s stated public domain by VOA; content licensed from others (AP, Reuters, some photos and clips) is excluded; credit asked | Parts 2 and 4 (real speech, slower) | US English; each item must be checked for third-party credits; the site is outside this environment's network, so fetching runs on the owner's laptop |
| **AMI Meeting Corpus** | 100 hours of real meetings (design-team role play), transcripts and speaker labels | CC BY 4.0 for signals and transcripts on the current Edinburgh download page; the older OpenSLR mirror shows a NonCommercial-ShareAlike licence: use the current release and read its LICENCE.txt | Part 3, for C1 practice | Spontaneous and overlapping, many non-native speakers, hard to follow; excerpts need cutting by hand |
| **ICSI Meeting Corpus** | 75 real research meetings (Berkeley, 2000–2002) | CC BY 4.0 for signals and transcription (official page); some third-party annotations differ | Part 3, C1 | As AMI, harder (technical talk); mostly American |
| **Spoken Wikipedia Corpus (English)** | Volunteers reading Wikipedia articles, time-aligned | CC BY-SA 4.0 (Hamburg repository; one metadata export also says CC BY: read the record) | Part 4 | Read speech; recording quality varies; ShareAlike |
| **MIT OpenCourseWare lectures** | Real university lectures with transcripts | CC BY-NC-SA by default; copyright stays with MIT | Part 4, the most exam-like | NonCommercial; mostly American; video downloads; long lectures need cutting |
| **DailyDialog** | 13,000 short everyday dialogues, text only | CC BY-NC-SA 4.0 (dataset card), "research purposes only" | Part 1 scripts, voiced by Piper | NonCommercial and research-only; written by non-experts, short |

**Excluded:** TED talks (CC BY-NC-ND: NoDerivatives, which the project never uses); BBC Learning English and British Council
materials (copyrighted, not open); real past IELTS papers (a SPEC non-goal). **Not useful here:** LibriVox (public-domain
audiobooks, old literary English), Common Voice (CC0, single sentences: dictation only).

## Voices for our own scripts (Piper, pinned at `rhasspy/piper-voices` e9ab671f2a0e)
| Voice | Dataset licence (model card) | Note |
|---|---|---|
| `cori` (in use) | LibriVox, public domain | Female |
| `alba` medium | CC BY 4.0 (University of Edinburgh) | Female, Scottish; fine-tuned from the US Hi-Fi TTS reader 92 voice |
| `northern_english_male` medium | CC BY-SA 4.0 (OpenSLR 83) | **The only clean British male voice found**; fine-tuned from Piper's US "lessac" voice, whose base dataset licence must also be read |
| `southern_english_female` medium | CC BY-SA 4.0 (OpenSLR 83) | Female |

## Measured: a two-voice Part 1 conversation
A 15-turn booking call written for this study (`docs/v2/listening-sources/dialogue.json`), voiced by `alba` and
`northern_english_male` with a 0.45 s gap between turns, then transcribed by the recommended recogniser (Whisper small.en, the
speech study) as a stand-in for "can the answers be heard":
- **Speed:** 67.5 s of audio in 3.7 s on this container's 4 CPUs (about 18 times faster than real time); a 5-minute part
  would take about 20 s.
- **Answers:** the two times, four prices, the 10% discount, "15 minutes", the surname and its spelling (H-E-N-D-E-R-S-O-N)
  were all recovered. **The phone number was not:** "oh seven seven, double four, five one, two nine three" came back as
  "077-44-5123", a digit lost. Two small slips elsewhere ("this Saturday" → "the Saturday", "now" → "out").
- **What this says:** synthetic dialogue is fast and mostly clear, but an answer present in the script is not always
  recoverable from the audio, and dense digit strings are the weak point. Naturalness, turn-taking and whether it sounds like
  a real call are for the owner's ears (the sample was sent with this study).

## Recommendation
**Start CP5 with our own scripts voiced by Piper, and add real recordings as a second, harder tier later.**
1. **Parts 1 and 2 from scenario scripts.** DeepSeek writes a script and its questions from a scenario (a booking, a tour);
   every answer must appear in the script word for word (code check); another model family answers the questions blind from
   the script (as for Reading); the owner reviews, as for Reading.
2. **An audio check, new in this study:** after synthesis, the recogniser transcribes the audio and every answer must be
   recovered from the transcript; if not, that line is synthesised again more slowly (Piper's slow pace) and checked again,
   and dropped if it still fails. The phone number above would have been caught.
3. **Part 4 from the bank:** OpenStax passages voiced by `cori` as mini-lectures, using the Reading questions already
   approved for them (no new generation).
4. **Part 3 and real speech later, as a C1 tier:** short AMI excerpts (CC BY 4.0 current release) and, if the owner reads
   and accepts VOA's terms, VOA Learning English for real, slower speech. Both need fetching on the owner's laptop and
   cutting by hand.
5. **Everything synthetic is labelled "giọng đọc máy"**, as the plan already says.

## Decisions for the owner
| Decision | Options | Recommended |
|---|---|---|
| The first source | Own scripts + Piper; real recordings first (VOA/AMI) | Own scripts + Piper, real recordings as a later tier |
| The male voice | `northern_english_male` (read OpenSLR 83 and the lessac base licence); female voices only | Read both licences; use it if they hold |
| The audio check | Required for every generated item; only for numbers and names | Required for every item |
| VOA | Read its terms on the owner's laptop and decide; skip for now | Read when convenient; not needed to start |
| NonCommercial sources (MIT OCW, DailyDialog) | Allowed for the owner's own study, flagged; avoided | Avoid while open alternatives exist; DailyDialog is also research-only |

## Sources consulted
VOA Learning English request and terms pages (via search results; the site is outside this environment's network):
learningenglish.voanews.com/p/6021.html, direct.usagm.gov/terms_and_conditions. AMI: groups.inf.ed.ac.uk/ami/download,
openslr.org/16. ICSI: groups.inf.ed.ac.uk/ami/icsi/license.shtml. Spoken Wikipedia: nats.gitlab.io/swc,
fdr.uni-hamburg.de/record/1875. MIT OpenCourseWare: ocw.mit.edu terms (default CC BY-NC-SA). DailyDialog: Hugging Face dataset
card. Piper voices: model cards under huggingface.co/rhasspy/piper-voices at e9ab671f2a0e.
