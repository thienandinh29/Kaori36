# Step 3.3: target sounds in the owner's recordings

Part of `spec.md` (phase 3). 3.3a is built here; 3.3b (labels and thresholds) follows.

## 3.3a: canonical phones and analysis (built)
**What the learner sees.** On `/phat-am`, each stored recording shows "Đang chờ phân tích" until the worker has
analysed it. After that, "Xem điểm từng âm" shows one row per target sound: the sound, the word, a raw score and the
phone the model heard instead, if any. The page says the scores are raw and **not verified**: there is no right/wrong
mark and nothing is red. Owner only, as in 3.1.

**Canonical phones** (`data/pronunciation/canonical.yaml`). Each prompt is listed word by word in the recogniser's phone
set (`model-phones.txt`, from the pinned model's vocabulary). British RP with weak forms for function words (*the* /ðə/,
*to* /tə/, *of* /əv/), because the Piper model voice is British and the check on Piper's speech in 3.2 showed that
American expected phones caused every mismatch. Drafted from eSpeak (`en-gb-x-rp`) and corrected by hand; **draft until
the owner reviews it**. No LLM wrote any phone (the owner's rule).

**Target positions come from rules** (`app/pronunciation/canonical.py`), not from hand marks:
- final consonants (`final-t`, `-k`, `-p`, `-s`, `-z`): the last phone of a word of two phones or more;
- single sounds (`th`, `sh`, `ch/j`, `r/l`, long vowels, `æ`): every occurrence;
- clusters: two or more consonants at the start or end of a word.

A position is judged once, by the first rule that names it.

**Checked at start-up and in CI.** For every prompt, the words match the prompt text, every phone is in the model's
set, and each target sound occurs at least once. The API and the worker refuse to start otherwise.

**The worker** (`app/pronunciation/analysis.py`) runs only when `PRONUNCIATION_URL` is set (compose profile
`pronunciation`). It works through one recording at a time, oldest first, using `for update skip locked`:
- It sends the audio and the prompt's phones to `POST /score`.
- It keeps only the target positions: phone, GOP, competitor, start and end in ms.
- It stores the result in `speech_recordings.analysis` (migration `0022`) with the status `analysed`.
- If the service fails, it stores a short reason with the status `failed` and does not retry.

Either way, **the audio is cleared at once unless the learner chose to keep it** (the strict voice policy): the scores
stay, the voice does not. Purging after 24 hours still removes the row.

**Route.** `GET /recordings/{id}?learner_id=` returns one of the learner's own recordings with `analysis`, or 404.

## 3.3b: thresholds (next)
1. The owner records 50–100 prompts.
2. The owner labels every target position right or wrong on a labelling page that plays the aligned segment.
3. Per sound group, a threshold on GOP is chosen on one half of the labels; its false-alarm rate (with a Wilson
   interval) is measured on the other half.
4. A sound gets marks in 3.4 only if its false alarms are at most 10%; the other sounds stay "chưa kiểm chứng".

## Not in this step
Marks or colours, a learner-facing verdict, stress or intonation, other learners recording.
