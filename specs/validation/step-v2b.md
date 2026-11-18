# Step V2b: pronunciation, grammar and vocabulary in the reviewer portal

Builds on V2 (`step-v2.md`). This adds three queues to `/kiem-duyet`. Essay bands, for an IELTS rater, are a later
step: they need the four-criterion form and touch the owner's essays.

| Queue | Content id | Who | What the reviewer sees and does |
|---|---|---|---|
| `speech_target` / `phone_ok` | `<recording>:<n>` | Phonetics-trained reviewer by default; an English teacher with `--role expert_teacher` | The sentence, the target word and sound, the recording (whole, or just the part with the sound); right / wrong / not sure |
| `grammar_item` / `item_ok` | the item id | English teacher | The question with its options in a fixed shuffled order (so the key is not always first); answers blind, then judges the key: right / wrong (wrong key, two answers, unclear, other) / not sure |
| `vocab_entry` / `entry_ok` | `<lemma>-<pos>` | English teacher | The entry: definition, Vietnamese gloss, examples, collocations, word forms, IPA; right / wrong (which part) / not sure |

## The voice rule
A recording reaches a reviewer only when all of these hold:
- it is **kept**;
- it is analysed;
- it belongs to an **owner** (`DRAFT_ITEM_LEARNERS`);
- the owner put it in a batch with an explicit command: `make-batch --content speech_target --learner <owner id>`.

Anyone else's recordings are refused. The audio is fetched with the reviewer's token and played from memory, never
from a plain URL. A recording that is deleted, or no longer kept, stops being served at once. `SPEC.md` records this.

## Commands
```
uv run python -m app.validation.cli make-batch --content speech_target --learner <your id> --name "Âm đợt 1"
uv run python -m app.validation.cli make-batch --content grammar_item --size 40 --name "Ngữ pháp đợt 1"
uv run python -m app.validation.cli make-batch --content vocab_entry --size 50 --name "Từ vựng đợt 1"
```

## Tasks
- [x] T1 The queues, views, reason sets per type, and the audio route in the portal service; role override for sounds.
- [x] T2 CLI `make-batch` for the three types; `random_sample`; owner-only recordings.
- [x] T3 Database tests:
  - only kept owner recordings are served;
  - audio is refused across roles and once a recording is no longer kept;
  - grammar options are shuffled and keyed;
  - vocabulary ids are unique.
- [x] T4 Web: the three views, the audio player, the proxy rules, strings; Vitest and Playwright.
- [x] T5 SPEC, MAP, `dolater.md`.
