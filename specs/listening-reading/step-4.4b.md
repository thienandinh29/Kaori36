# Step 4.4b: Listening from the Reading bank, dictation and gap-fill (spec, plan, tasks)

Plan: `plan.md` (CP5). Source decision: none needed. The 30 bank texts are OpenStax (CC BY-NC-SA 4.0, owner-checked
19 Nov), and the voice is the self-hosted Piper `cori` already in use (`specs/speech/`). This is part a of CP5. Parts 1–3
scripts wait for the owner's source decision (`docs/v2/listening-sources.md`). The Part 4 mini-lecture, with approved
Reading questions on audio, is step 4.4c.

## What the learner does
`/nghe` lists the texts. A text gives a few short exercises, each heard from the server voice ("giọng đọc máy"):
- **Dictation** (`listening-dictation`): hear one sentence and type it.
  - It is marked right only when every word matches after normalisation. A misspelling is wrong, as in IELTS.
  - The result shows each word as right, wrong or missed.
- **Gap-fill** (`listening-detail`): hear one sentence, read it with one word blanked, and type the word.
  - Exact after normalisation (`graders/typed.py`).

Each answer is one BKT observation on its Listening competency, logged in `listening_answers`. Listening becomes an
available skill in "Hôm nay" while the voice is configured, and is measured after 3 answers.

## Rules
- **Built by code, keys by construction.** The answer is the sentence the voice read, so no model writes or checks
  anything, and the label tier is construction.
- **Safe sentences only.** The voice must say exactly what is written, and the audio check of step 4.4a needs a
  recogniser the owner has not chosen yet. So a sentence qualifies only if it:
  - has 6–18 words;
  - uses ASCII letters with basic punctuation only;
  - has no digits, brackets, quotes, colons, semicolons or dashes;
  - has no capital letter after the first word (no names or acronyms);
  - has at most 300 characters.
- **Selection.** Up to 3 dictation and 3 gap-fill sentences per text, spread across the text, chosen deterministically.
  The gap is the longest word of 5 or more letters that is not a function word.
- **The text never reaches the browser before answering.** Audio comes from `GET /listening/items/{id}/audio`, which
  synthesises the item's sentence on the server and caches it in memory. The item view holds only what the learner
  may see: a gap-fill sentence with its blank, and nothing for dictation.
- **No voice, no Listening.** Without `TTS_URL` the routes answer 503 and "Hôm nay" does not offer Listening.

## Routes
- `GET /listening/texts?learner_id=` returns `{available, texts: [{slug, title, dictation, gaps}]}`.
- `GET /listening/texts/{slug}?learner_id=` returns `{slug, title, items: [{id, kind, prompt}]}`. The `prompt` is the
  gap sentence, or null for dictation.
- `GET /listening/items/{id}/audio?pace=normal|slow` returns `audio/wav`.
- `POST /listening/items/{id}/answer {learner_id, answer}` returns `{correct, score, key, words, competency, trace}`.
  `words` lists `[{word, status: right|wrong|missed|extra}]` for dictation.

Migration `0034_listening_answers.sql` (additive): `listening_answers`, one row per answer.

## Tasks
- [x] T1 `app/listening/items.py`: safe sentences, selection, dictation and gap items, word-level marking (pure).
- [x] T2 Migration, `app/services/listening_practice.py`, `app/api/listening_practice.py`, audio cache, wiring in
  `main.py` and `/today`.
- [x] T3 Tests:
  - selection rules on the real bank;
  - marking: misspelling wrong, punctuation and case ignored, word diff;
  - the sentence never sent;
  - evidence and competencies;
  - 503 without a voice;
  - "Hôm nay".
- [x] T4 (PR 2) The web page `/nghe` and `/nghe/{slug}`: play and slow play (3 plays before answering; free after),
  type, word-by-word result with a legend that does not rely on colour, strings in `vi`; proxy rules; Vitest decoders;
  Playwright (no voice on the real API, a mocked dictation and gap).
- [ ] T5 (4.4c) The Part 4 mini-lecture: a whole passage voiced, with its approved Reading questions.
- [ ] T6 (after the recogniser decision) The audio check of step 4.4a on every sentence before serving.
