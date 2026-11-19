# Step 3.6b: dropped sounds and the pronunciation benchmark (spec, plan, results)

Builds on `step-3.6a.md`. Part 1 (built 19 Nov) needs nothing from the owner: dropped sounds and a synthetic benchmark.
Part 2 adds the L2-ARCTIC Vietnamese speakers once the owner has read its licence and confirmed they are there.

## Part 1: dropped sounds
Forced alignment gives every canonical phone at least one frame, even one never said. The service now reports, for each
phone, `peak` (the highest probability of the canonical phone in its frames) and `other_peak` (the highest probability of
any other phone there, blank and the neighbouring canonical phones left out). A sound is **dropped** when both are below
`DROPPED_PEAK` (0.1, `evidence.py`). A dropped sound is `wrong` whatever its GOP, in the product and in the 3.3b report
alike, and `/phat-am` says "có vẻ bị bỏ mất âm /k/" instead of "máy nghe giống /j/". Analyses from before this step have no
peaks and are judged as before.

## Part 1: the synthetic benchmark (`app/evalkit/pron_bench.py`, `evals/pronunciation/synthetic.yaml`)
28 words for the 14 target sounds, said by the self-hosted Piper voice inside "say … again" from exact phonemes
(`/speak-phonemes` on the voice service, not forwarded to learners): as written, with the target swapped for the error the
phase 3 spec lists for Vietnamese learners, or with it left out. Each recording is resampled to 16 kHz and scored against
the word's canonical phones, as a learner's would be; clean copies get white noise at 5 and 30 dB SNR for the quality gate.
The voice varies between syntheses, so each case is said 5 times (`--repeats`).

**What it can show:** whether the pipeline reacts to a controlled error, and false alarms on a clean voice. **What it
cannot:** anything about Vietnamese accents or real learners (one native British voice). Truth: construction.

## Results (19 Nov, 315 recordings, `evals/baselines/pronunciation-synthetic.json`)
| | n | result |
|---|---|---|
| Swapped sound marked (GOP < 0, competitor heard) | 110 | 99; the heard phone is the swap in 90 |
| Dropped sound, dropped rule at 0.1 | 65 | 53 (0.2: 57, but 3 of 140 clean sounds called dropped) |
| Dropped sound, GOP < 0 with a competitor | 65 | 58, but the "heard" phone is meaningless (ə, j, ɹ) |
| Clean sound marked | 140 | 18 |
| Clean sound called dropped at 0.1 | 140 | 0 |
| Noise: refused at 5 dB / accepted at 30 dB | 140 each | 140 / 140 |

By sound: most groups are clean (no or one false alarm in 10) with swaps caught 10/10 to 20/20. **/æ/–/ɛ/ fails on a
clean native voice:** the /æ/ of *bad, man* was marked 10 of 10 times. Natural British speech from text (Piper's own
pronunciation: `bˈæd`, `mˈan`, `blˈak`, `hˈat`) was marked 12 of 15 times against canonical /æ/ and 9 of 15 against /a/,
so changing the canonical symbol does not fix it: this recogniser does not judge the TRAP vowel reliably. Final /z/: 3 of
10 clean ones marked (natural devoicing is a plausible cause). Long /uː/: 2 of 10.

**What this changes.** The dropped rule ships at 0.1. The /æ/–/ɛ/ group should not go live on plain GOP; a hypothesis to
test later is a constrained comparison (the expected confusion only, /æ/ against /ɛ/). The 3.3b gate on Gold labels stays
the decision for every group; this benchmark only says where to expect trouble.

## Tasks
- [x] T1 Service: `peak` and `other_peak`; tests (a dropped phone peaks nowhere, a swap lets another peak, a neighbour's
  spike does not count). Voice service: `/speak-phonemes`, unknown symbols refused.
- [x] T2 API: peaks kept in the analysis; `is_dropped`, dropped = wrong in `outcome` and in the 3.3b report; `dropped`
  indexes on a recording; the page's wording.
- [x] T3 Benchmark: cases, resampling and noise in plain Python (no new dependency), repeats, the report; run and baseline.
- [ ] T4 (part 2) L2-ARCTIC Vietnamese speakers: substitutions, deletions and false alarms per group with intervals, by
  speaker; then 3.6c calibration on two speakers, checked on the other two.
