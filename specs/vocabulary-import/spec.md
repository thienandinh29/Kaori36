# Spec: importing NGSL 1.2 and NAWL 1.2 (about 3,770 words)

The owner's request: a full word list instead of the 130-word starter. Both lists were verified by the owner on 16 Nov 2026
as **CC BY-SA 4.0** (`data/sources/english-candidates.yaml`). Approved by the owner on 16 Nov 2026 with the recommended
options (decisions at the end); built as described below, with the changes noted **As built**.

## Where the data lives (licence)
- `data-sa/vocabulary/core-seed.yaml` (the same slug as the authored list), with `data-sa/LICENSE.md` (CC BY-SA 4.0 and
  the attribution, so no separate ATTRIBUTION file):
  "New General Service List and New Academic Word List by Browne, C., Culligan, B., and Phillips, J., CC BY-SA 4.0,
  https://www.newgeneralservicelist.com". Not in `data/` (CC BY-NC-SA), because ShareAlike material cannot be relicensed
  as NonCommercial. The app's code stays Apache-2.0. The Giới thiệu page carries the same credit.
- The learner sees **one list** (slug `core-seed`, so progress is kept): the loader combines the authored file and the imported
  file; on a duplicate word the authored entry wins. Topics are shared (the 11 IELTS topics).

## The import (`python -m app.vocabulary.importer`, run once; the result is committed)
1. **Download** from the official `.com` site only: NGSL 1.2 with basic statistics (frequency ranks), NGSL 1.2 with definitions
   in easy English, NAWL 1.2 with definitions in easy English. **As built:** also the NGSL and NAWL "lemmatized for
   teaching" files (each word's inflected forms, used to check the example) and "NGSL with SFI 31K" (frequencies that
   order the NAWL, whose own files have no rank); the hashes are in `data-sa/vocabulary/sources.json`. Each file's SHA-256 is recorded in a manifest on the first run and
   checked on every later run. The downloads are not committed.
2. **From the lists, unchanged:** the headword and the easy-English definition. A definition that contains its own headword is
   not used (the card must not give the word away); that word is listed in the report for the owner.
3. **Level, estimated from frequency** (labelled "ước lượng theo tần suất", never presented as an official CEFR level):
   NGSL ranks 1–500 A1, 501–1,200 A2, 1,201–2,000 B1, 2,001–2,809 B2; NAWL by frequency (the SFI in the 31K file): the more frequent half B2, the rest C1, no figure C1.
4. **Written by the AI (DeepSeek, `vocab_import` task in `routing.yaml`, 40 words per call, 4 calls at a time), marked
   draft:** the part of speech when the list gives none,
   the Vietnamese meaning, one example sentence containing the word exactly once, a topic from the 11, and a collocation or word
   form when natural. **As built:** no word-form items (their base word is hard to check by code); the example's answer
   must be the headword or one of its listed inflections; a bad collocation or unknown topic is dropped and the word kept;
   function words (the model's `other`) and NAWL prefixes are not practised. **Code checks every entry with the same rules as the authored list** (example contains the word once,
   collocation blank once, no definition giving the word away); an entry that fails is dropped and listed in the report, never
   repaired by hand-waving.
5. **IPA (British), only where two independent sources agree:** espeak-ng (the rule-based engine already inside the `tts`
   container, behind a small `/phonemize` endpoint so the GPL code stays in that service; voice `en-gb-x-rp`) and the AI's
   transcription (asked in the same call as the entry; espeak is the independent source). Code
   normalises notation only (`app/vocabulary/ipa.py`: ɹ→r, ɐ→ə, ɛ→e, ᵻ→ɪ, iə→ɪə, length marks, the final happY vowel,
   secondary stress, syllable dots; the primary stress is compared by syllable, because stress is the error that matters).
   Against the 130 authored IPA strings espeak agrees on 111 (85%); the rest are real differences such as noun/verb stress and compares. **Agree: the AI's form is kept, labelled "phiên âm tự động". Disagree: no IPA, ever filled by the AI
   alone (the owner's rule)**; the word goes on the report's list for a trusted source (Wiktionary after its licence check) or
   the owner.
6. **Report** (`data-sa/vocabulary/import-report.json`, numbers only): words read, kept, dropped with reasons, IPA agreement rate,
   calls, tokens and cost.

## Cost and time
About 95 calls of about 1,300 input and 3,700 output tokens. **As built:** the import has its own cap (`--max-usd`, default
US$1.00, computed with the configured prices, deliberately high by default) instead of a learner's plan; it stops starting
batches at the cap, every reply is cached in git-ignored `data/private/vocab-import/`, and a second run resumes for free.
The run's real figures are in the report.

## Before learners rely on it (the gate)
- The owner checks **50 random imported entries** (Vietnamese meaning, example, topic, IPA where shown) as right or wrong;
  precision with an exact interval goes in the report. Until then the list stays `draft` and the page shows "bản nháp".
- The IPA agreement rate is reported; the share of words with IPA is shown honestly (no IPA is better than wrong IPA).

## Not in this step
Wiktionary (licence not checked yet), more lists from the NGSL project (TSL, BSL), words beyond NAWL by frequency, audio files.

## Decisions for the owner
- [x] The frequency-to-level bands above (owner, 16 Nov 2026: "go with your recommendations")
- [x] One combined list
- [x] Send the headwords (no learner data) to DeepSeek. **As built:** run from the development session with the owner's key;
  the same command runs on the laptop (`docs` in the plan below).
