# Step 4.1: the text bank, licences and level features

Part of `specs/listening-reading/`. First build step of phase 4. **No model call, no network, no new dependency, no
migration.** It builds the container the later steps fill: texts the owner has added, each tied to a source whose licence
the owner has read, with measured features. It does not fetch anything, and it ships no text.

## What the owner does
Adds a text as a small YAML file under `data/english/texts/` (committed only when its source is verified and its licence
allows it; otherwise keep it in `data/private/`):
`slug, title, source (a slug from data/sources/english-candidates.yaml), url (the page of this text), author?, retrieved_on, text`.

## What the code does (`app/texts/`)
- **`bank.py`**: loads a folder of such files and checks each against the candidates file.
  - The source must exist and be `verified` (licence page and date recorded by the owner); otherwise the text is refused with
    the reason. A NoDerivatives licence is already impossible for a verified source (`sources/candidates.py`).
  - The licence, check date, ShareAlike and NonCommercial flags are **copied from the source at load**, never typed per text,
    so a text cannot claim a licence its source lacks.
  - Text is NFC-normalised; 80 to 1,200 words; duplicate slugs and duplicate texts are refused.
- **`features.py`**: pure functions. Words, sentences, mean sentence length, share of long words (7+ letters), type-token ratio
  over the first 100 words (a fixed window, so length does not distort it), and the share of words **not** in a given known-word
  set (`None` when no set is given). It makes **no CEFR claim**: the owner labels 30 texts later to see how well these features
  track a level (spec "Texts and licences").
- **CLI** `python -m app.texts.bank [folder]`: prints one line per text (slug, source, licence, words, features, flags) and the
  refusals, exit 1 if any text was refused.

## Not in this step
Fetching texts, audio, questions, any model call, a CEFR level label, a web page.

## Acceptance
Tests with inline fixtures: a text from a verified source loads and carries its licence and flags; unverified, rejected and
unknown sources are refused; NFC and word bounds; duplicates; every feature on small texts with known answers; the unknown-word
share with and without a set; the CLI exit code and its output; the repository's own `data/english/texts/` loads (empty is fine).
