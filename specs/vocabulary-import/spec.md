# Spec: importing NGSL 1.2 and NAWL 1.2 (about 3,770 words)

The owner's request: a full word list instead of the 130-word starter. Both lists were verified by the owner on 16 Nov 2026
as **CC BY-SA 4.0** (`data/sources/english-candidates.yaml`). Document only: nothing is built until the owner approves.

## Where the data lives (licence)
- `data-sa/vocabulary/ngsl-nawl.yaml`, with `data-sa/LICENSE.md` (CC BY-SA 4.0) and `data-sa/ATTRIBUTION.md`:
  "New General Service List and New Academic Word List by Browne, C., Culligan, B., and Phillips, J., CC BY-SA 4.0,
  https://www.newgeneralservicelist.com". Not in `data/` (CC BY-NC-SA), because ShareAlike material cannot be relicensed
  as NonCommercial. The app's code stays Apache-2.0. The Giới thiệu page carries the same credit.
- The learner sees **one list** (slug `core-seed`, so progress is kept): the loader combines the authored file and the imported
  file; on a duplicate word the authored entry wins. Topics are shared (the 11 IELTS topics).

## The import (`python -m app.vocabulary.importer`, run once on the owner's laptop; the result is committed)
1. **Download** from the official `.com` site only: NGSL 1.2 with basic statistics (frequency ranks), NGSL 1.2 with definitions
   in easy English, NAWL 1.2 with definitions in easy English. Each file's SHA-256 is recorded in a manifest on the first run and
   checked on every later run. The downloads are not committed.
2. **From the lists, unchanged:** the headword and the easy-English definition. A definition that contains its own headword is
   not used (the card must not give the word away); that word is listed in the report for the owner.
3. **Level, estimated from frequency** (labelled "ước lượng theo tần suất", never presented as an official CEFR level):
   NGSL ranks 1–500 A1, 501–1,200 A2, 1,201–2,000 B1, 2,001–2,809 B2; NAWL by its own rank: first half B2, second half C1.
4. **Written by the AI (DeepSeek, budgeted, about 40 words per call), marked draft:** the part of speech when the list gives none,
   the Vietnamese meaning, one example sentence containing the word exactly once, a topic from the 11, and a collocation or word
   form when natural. **Code checks every entry with the same rules as the authored list** (example contains the word once,
   collocation blank once, no definition giving the word away); an entry that fails is dropped and listed in the report, never
   repaired by hand-waving.
5. **IPA (British), only where two independent sources agree:** espeak-ng (the rule-based engine already inside the `tts`
   container, behind a small `/phonemize` endpoint so the GPL code stays in that service) and the AI's transcription. Code
   normalises notation (for example ɹ→r, ɐ→ʌ, ᵻ→ɪ, syllable dots removed; stress marks kept, because stress is the error that
   matters) and compares. **Agree: the AI's form is kept, labelled "phiên âm tự động". Disagree: no IPA, ever filled by the AI
   alone (the owner's rule)**; the word goes on the report's list for a trusted source (Wiktionary after its licence check) or
   the owner.
6. **Report** (`data-sa/vocabulary/import-report.json`, numbers only): words read, kept, dropped with reasons, IPA agreement rate,
   calls, tokens and cost.

## Cost and time (estimate, to be measured)
About 95 calls for the entries and 95 for IPA, each a few thousand tokens: well under the daily cap at DeepSeek's prices. The
owner runs it as the `owner` plan; the import stops cleanly at the cost cap and resumes where it stopped.

## Before learners rely on it (the gate)
- The owner checks **50 random imported entries** (Vietnamese meaning, example, topic, IPA where shown) as right or wrong;
  precision with an exact interval goes in the report. Until then the list stays `draft` and the page shows "bản nháp".
- The IPA agreement rate is reported; the share of words with IPA is shown honestly (no IPA is better than wrong IPA).

## Not in this step
Wiktionary (licence not checked yet), more lists from the NGSL project (TSL, BSL), words beyond NAWL by frequency, audio files.

## Decisions for the owner
- [ ] The frequency-to-level bands above (or other cut-offs)
- [ ] One combined list (recommended) or a separate "NGSL + NAWL" list the learner chooses
- [ ] Run the import with DeepSeek on your laptop (it sends the 3,770 headwords, not any learner data, to DeepSeek)
