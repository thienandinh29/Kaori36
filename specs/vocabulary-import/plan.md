# Plan: NGSL/NAWL import

| Part | Where | Notes |
|---|---|---|
| Official files → headwords, levels, forms | `apps/api/app/vocabulary/headwords.py` | Stdlib only: CSV and a small `.xlsx` reader (zip + XML), no new dependency |
| IPA agreement | `apps/api/app/vocabulary/ipa.py` | Pure; notation folded, sounds and primary stress compared |
| espeak-ng IPA | `tts/nodetrail_tts/phonemes.py`, `POST /phonemize` | GPL engine stays in the `tts` service; voice `en-gb-x-rp` |
| Importer CLI | `apps/api/app/vocabulary/importer.py` | `download`, `run`, `sample`, `score`; cache in `data/private/vocab-import/`; `--max-usd` cap |
| One list for the learner | `load_wordlist(path, imported_dir)`; `Settings.vocab_imported_dir` | Authored entry wins; vocab and grammar services load the merged list once |
| Labels | `Word.origin` → `WordCard.origin` → web `originLabels` | "ước lượng theo tần suất", "phiên âm tự động", list and licence on the card; credit on Giới thiệu |
| Data and licence | `data-sa/` (CC BY-SA 4.0), `NOTICE`, `README.md`, API image copies `data-sa/` | |

Run on a laptop (after `git pull`; uses the API image, the `tts` service and the DeepSeek key in `.env`):

    docker compose --profile speech up -d --build tts
    docker compose run --rm --no-deps -v ./data-sa:/srv/data-sa -v ./data/private:/srv/data/private \
      -e TTS_URL=http://tts:8030 api python -m app.vocabulary.importer run --max-usd 1

Then `... importer sample`, mark `data-sa/vocabulary/review-sample.yaml`, `... importer score`.
