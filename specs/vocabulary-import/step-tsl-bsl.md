# Step: TOEIC Service List and Business Service List (about 1,860 new words)

The owner's request (27 Nov 2026): more words, from the same project as the NGSL and NAWL. Decisions were made by the owner on
27 Nov 2026 with the recommended options (end of page).

## The sources (licences read on each list's own page, 27 Nov 2026)
- **TSL 1.2**, TOEIC Service List, https://www.newgeneralservicelist.com/toeic-service-list: "TOEIC Service List by Browne, C.
  and Culligan, B., is licensed under a Creative Commons Attribution-ShareAlike 4.0 International License". 1,250 headwords
  with easy-English definitions (`TSL_12_definitions.xlsx`), inflected forms and frequency statistics.
- **BSL 1.20**, Business Service List, https://www.newgeneralservicelist.com/business-service-list: "Business Service List by
  Browne, C. and Culligan, B., is licensed under a Creative Commons Attribution-ShareAlike 4.0 International License".
  1,744 headwords with inflected forms and statistics, **no definitions**.
- Same licence as the NGSL and NAWL, so the output goes to `data-sa/` (CC BY-SA 4.0) with the attribution; recorded in
  `data/sources/english-candidates.yaml` (read by the agent at the owner's request).

Not already in our list (3,663 words): TSL 1,020, BSL 1,239, 399 in both, **1,860 together**. A word in both lists is
imported from the TSL (it has an official definition).

## The import (`python -m app.vocabulary.importer extra`, additive)
The NGSL/NAWL run is **not** repeated: its cached replies live on the owner's laptop, and a new run would rewrite the 3,533
reviewed-sample entries. This step reads the imported file, appends new words only, and never changes an existing entry.
A later NGSL/NAWL `run` keeps the TSL/BSL words already in the file.

1. **Download** the TSL and BSL files from the official `.com` site, plus `NGSLwithSFI-31K.xlsx` (already used for the NAWL);
   SHA-256 of each in `sources.json`.
2. **From the lists, unchanged:** the headword, the TSL definition, the inflected forms (the example's answer must be one of
   them). Same drop rules as before: not a plain lowercase headword, a definition that contains the word, a prefix
   (`non`, `anti`, `multi`...), function words, a word already in the list.
3. **Level, estimated from general-English frequency** (the SFI of the 31K file, as for the NAWL, never the lists' own
   TOEIC or business frequencies, which are not comparable): at or above the SFI where the NGSL's A1, A2 or B1 band ends,
   that level; otherwise, per list, the more frequent half B2 and the rest C1; no figure C1. Labelled "ước lượng theo tần
   suất".
4. **Written by the model (DeepSeek, `vocab_import`, 40 words a call, marked draft):** as for the NGSL (part of speech,
   Vietnamese, example, topic, collocation, IPA), and **for BSL-only words also the easy-English definition** (at most 15
   words, must not contain the word or its forms). Code checks every entry with the existing rules.
5. **Blind check of the model's BSL definitions** (task `vocab_check`, free Ernie with dots as backup, never DeepSeek's
   family; allowed for free models because the input is a public list's headwords, never a learner's data): the checker sees
   only the definition and four headwords (the word and three other BSL words of the same part of speech, in a shuffled
   order) and names the word it defines, or "cannot tell". Kept only when it names the right word. A wrong answer or "cannot
   tell" drops the word; **no reply leaves it unchecked and out of the list, retried on the next run** (lessons.md: a failed
   call is not a judgement). TSL definitions are the list's own and are not checked; a TSL word whose definition is missing or
   contains the word gets a model definition and the same check.
6. **IPA** as before: only where espeak-ng (`en-gb-x-rp`) and the model agree. The tsl and bsl lists include American
   spellings (`vacation`, `elevator`); the headword is kept as the list has it.
7. **Bands:** new words get `origin: tsl` or `origin: bsl` and their own vocabulary band nodes (`vocab-tsl`, `vocab-bsl`),
   like `vocab-nawl`, so the B2 and C1 band estimates are not diluted. No competency links them yet (Bronze links are the
   owner's call), so "Hôm nay" never recommends them; they are practised through `/tu-vung` by level and found in `/tu-dien`.
8. **Report** `import-report-tsl-bsl.json`: read, kept, dropped by reason, by level and source, IPA agreement, blind-check
   counts (right, wrong, cannot tell, no reply), calls, tokens, cost.

## Cost
About 50 generation calls and about 21 check calls (40 definitions a call). Hard cap: US$1.00 with the configured
(deliberately high) prices; the last import's real spend was US$0.12 for 3,533 words.

## Result (run 27 Nov 2026, `import-report-tsl-bsl.json`)
- **1,825 words added** (TSL 1,008, BSL 817): the list is now **5,488 words** (130 authored, 5,358 imported).
  Levels: B1 2, B2 914, C1 909 (frequency estimates).
- **Model definitions:** 836 written (BSL words and TSL words without a usable one); the blind check picked the right
  word for 835 and the wrong one for 1 (`widen`, dropped). The free checker failed on 4 of 25 calls across three runs;
  those words were asked again until every one had an answer (none left unchecked). The report's checker counts are the
  last run's only.
- **Dropped:** 35 in all: 10 prefixes, 3 not plain headwords, 5 function words, 9 model definitions that failed code's
  rules, 7 examples that failed code's rules, 1 by the blind check.
- **IPA:** shown for 1,162 of the 1,825 new words (64%), where espeak-ng and the model agreed; lower than the NGSL's 72%,
  which fits American spellings and business terms.
- **Cost:** 47 generation calls, 55,927 input and 175,812 output tokens, US$0.76 at the configured (deliberately high)
  prices, under the US$1.00 cap; the checker is a free model.
- **Seen in the data:** the TSL's own definitions are copied unchanged, typos included (for example "memo": "a written
  reminder to do somethng"); a few model definitions start with a capital and end with a full stop. Neither is fixed
  by hand.

## Not claimed
The blind check shows that a definition picks out its word among four, not that it is good English or the best sense. The
Vietnamese, examples and IPA stay Bronze drafts, as for the NGSL. Like the rest of the list, the new words stay draft until a
teacher checks a sample (the owner's 50-entry check covers NGSL/NAWL only).

## Decisions (owner, 27 Nov 2026)
- [x] BSL definitions written by the model and blind-checked by another family (not code-only, not skipping BSL)
- [x] Levels by the NAWL rule (frequent half B2, rest C1), with NGSL cut-offs for the few common words
- [x] Cost cap US$1.00
