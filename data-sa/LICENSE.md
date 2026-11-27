# Licence of the `data-sa/` directory

Everything under `data-sa/` is licensed under the **Creative Commons Attribution-ShareAlike 4.0
International** licence (CC BY-SA 4.0):

- Summary: https://creativecommons.org/licenses/by-sa/4.0/
- Full legal code: https://creativecommons.org/licenses/by-sa/4.0/legalcode

## Why this directory is separate

It holds material adapted from sources licensed CC BY-SA 4.0. ShareAlike requires adaptations to keep that licence,
so this material cannot go in `data/` (CC BY-NC-SA 4.0) or under the code's Apache-2.0 licence.

## Attribution

- `vocabulary/` — adapted from the **New General Service List 1.2** and the **New Academic Word List 1.2** by
  Browne, C., Culligan, B., and Phillips, J., licensed CC BY-SA 4.0, https://www.newgeneralservicelist.com
  (licence checked by the project owner on the lists' own pages on 16 November 2026; see
  `../data/sources/english-candidates.yaml`).
  Taken from the lists: the headwords, their easy-English definitions, their inflected forms and the frequency
  figures used to estimate a level. Changes: definitions were whitespace-normalised; words were left out as listed
  in `vocabulary/import-report.json`; levels were estimated from frequency (not official CEFR levels); the part of
  speech (NGSL), Vietnamese meaning, example sentence, topic, collocation and IPA were added. The added parts were
  written by an AI model (DeepSeek), checked by code, and are a draft that has not been reviewed by a teacher. IPA is
  present only where the model's transcription and espeak-ng's agreed after notation was normalised.
  `vocabulary/sources.json` records the SHA-256 of each official file used.
- `vocabulary/` also holds words adapted from the **TOEIC Service List 1.2** and the **Business Service List 1.20** by
  Browne, C. and Culligan, B., licensed CC BY-SA 4.0, https://www.newgeneralservicelist.com (licence read on each
  list's own page by the agent at the owner's request on 27 November 2026; see
  `../data/sources/english-candidates.yaml`). Taken from the lists: the headwords, the TSL's easy-English definitions and
  the inflected forms. Changes: as above, plus: the BSL has no definitions, so its definitions (and those of TSL words
  whose definition was missing or contained the word) were written by an AI model (DeepSeek) and kept only when a
  model of another family, shown the definition and four words, picked the right word. Words left out are listed in
  `vocabulary/import-report-tsl-bsl.json`.
