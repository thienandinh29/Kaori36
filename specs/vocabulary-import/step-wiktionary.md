# Step: how much of the word list Wiktionary covers (a measurement)

**What.** Before anything from Wiktionary goes into the word list, measure what it could add to the 3,663 words (130
authored + 3,533 NGSL/NAWL). Source: the wiktextract dump that kaikki.org publishes (`raw-wiktextract-data.jsonl.gz`,
2.9 GB, every language, rebuilt about weekly). The command `python -m app.vocabulary.wiktionary scan` keeps only the
English entries with one of the list's headwords, caches them in git-ignored `data/private/wiktionary/en-entries.jsonl`,
and writes `coverage.json` next to them (the dump's SHA-256 included). `report` recounts from the cache.

**Why.** The owner wants Wiktionary as a vocabulary source (26 Nov 2026). Wiktionary has no word frequencies, so it cannot
choose the words or estimate their levels: NGSL/NAWL stay the list. What it may add: a British IPA written by people (the
import keeps an IPA only where the model and espeak-ng agree, so many words have none), Vietnamese translations by people
(today's `vi` is the model's draft), real recordings, usage examples.

**What is measured.** Per word, with the list's part of speech (another part of speech only when that one is missing):
found; a British-tagged IPA (tags UK, Received-Pronunciation, British, England, Southern-England) or only an untagged one;
a Vietnamese translation (`code: vi`); a British recording, any recording; a usage example (not a dated quotation); and, for
words that already show an IPA, how often a British Wiktionary IPA agrees with it under `ipa.agree` (optional sounds in
brackets such as `(ɹ)` left out). A sample of disagreements and the missing words go in the report for the owner to look at.

**Not claimed.** That Wiktionary is right: it is one source (Bronze). A translation's existence is counted, not its fit to
the sense the card teaches. Agreement with our IPA says two sources agree, not that either is right.

**Licence: verified by the owner on 26 Nov 2026** (Wiktionary's text is dual-licensed, CC BY-SA 4.0 used here; recorded in `data/sources/english-candidates.yaml`). Before: kaikki.org states no licence of its own and asks for a citation
(Ylonen, LREC 2022). The text's licence is Wiktionary's, believed CC BY-SA 4.0 (and GFDL), still `to_check` in
`data/sources/english-candidates.yaml`; if confirmed, adapted data would live in `data-sa/` beside NGSL/NAWL. Each
recording on Wikimedia Commons has its own licence, which the dump does not carry. Nothing from the dump is committed in
this step: only the code and, later, the numbers.

**Result (26 Nov 2026, run on the owner's laptop).** Dump of 30 Oct 2026 (from the 1 Oct Wiktionary dump), SHA-256
`5ff2c072…cb5291` (full hash in `coverage.json`); 8,261 English entries kept; the scan took 5.5 minutes. These are counts
over the whole list, not a sample, so no interval:

| What Wiktionary has, for the list's 3,663 words | Words |
|---|---|
| An English entry (with the list's part of speech) | 3,663 (3,652, 99.7%) |
| A British-tagged IPA | 2,538 (69.3%); 1,060 more have only an untagged IPA |
| A British IPA for a word that shows **no IPA today** | 713 of 981 (72.7%): IPA on the list would go from 73.2% to 92.7% |
| Its British IPA agrees with the IPA the list shows | 1,699 of 1,825 (93.1%) after notation folds; 82.2% before |
| A Vietnamese translation | 2,490 (68.0%) |
| A British recording / any recording | 1,411 (38.5%) / 3,649 (99.6%, mostly American) |
| A usage example (not a quotation) | 3,111 (84.9%) |

What the disagreements are (the 40 sampled, read by the agent, Bronze): mostly notation conventions, not pronunciation:
the weak vowel in *-ity*, *-ism* (`ɪ`/`ə`), `ʊ`/`u` before a vowel, and the newer British notation some pages use (`a`
for `æ`, `ɛː` for `eə`); a few are other accents tagged British (*breakfast* `/ˈbreɪkˌfɑːst/`, *out* `/ˈuːt/`). So
Wiktionary's British IPA cannot be shown as it is: it would need the dictionary convention (`æ`, `eə`) and a filter on
dialect tags first. Not measured: whether a Vietnamese translation fits the sense the card teaches.

**Next, if the numbers earn it (the owner decides).** An enrichment step: British IPA where the list has none, Wiktionary's
Vietnamese next to the model's, recordings after a per-file licence check. The list, levels and progress stay as they are.
