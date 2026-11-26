# Tasks: NGSL/NAWL import

- [x] T1 `/phonemize` in the tts service with tests (fake and real espeak)
- [x] T2 `ipa.py` with agreement and disagreement tests; measured on the 130 authored words
- [x] T3 `headwords.py`: parse the official formats, levels by the owner's bands, drop reasons, tests on small files
- [x] T4 `importer.py`: model batches, code checks, IPA rule, cache and cap, report, owner's sample and score; tests
      with a fake model
- [x] T5 Merged list (`origin`, `vocab_imported_dir`), services, API card field, web labels and credit, tests
- [x] T6 `data-sa/` licence, NOTICE, README, API image
- [x] T7 Run the import; commit the list, report and source hashes
- [ ] T8 Owner: mark the 50-entry sample (`review-sample.yaml`), then `score`; until then the list stays a draft

## Wiktionary coverage (`step-wiktionary.md`)
- [x] W1 `wiktionary.py`: filter the kaikki.org dump to the list's headwords, count coverage, cache; tests
- [x] W2 Run on the owner's laptop (26 Nov); the numbers are in the step page
- [x] W3a Owner: Wiktionary's licence read (26 Nov): CC BY-SA 4.0 (dual with GFDL)
- [ ] W3b Owner: decide whether an enrichment step follows
