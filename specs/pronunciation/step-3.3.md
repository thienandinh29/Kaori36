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
- If the service cannot be reached (still starting, down or overloaded: no connection, a timeout, HTTP 5xx or
  429), nothing changes. The recording stays queued with its audio, and the worker tries again 30 s later. On first
  start the service downloads its weights for several minutes, so this is the normal case.
  **Fix (28 Nov 2026):** when the service was reachable but failed on the recording (HTTP 5xx or 429, or a hang past
  the timeout), the failure is counted in `speech_recordings.attempts` (migration `0052`); the third marks the recording
  `failed` (audio cleared unless kept) and a recording with fewer failures is tried first, so one bad recording never holds
  up the rest. A service that is not there (a refused connection, still loading its weights) is not counted: that says
  nothing about the recording, and failing recordings during the first-start download would lose them.
- If the recording itself cannot be scored (HTTP 4xx, such as "cannot align"), it stores a short reason with the status
  `failed`. It is not retried.

Either way, **the audio is cleared at once unless the learner chose to keep it** (the strict voice policy): the scores
stay, the voice does not. Purging after 24 hours still removes the row.

**Route.** `GET /recordings/{id}?learner_id=` returns one of the learner's own recordings with `analysis`, or 404.

**Checked for real (17 Nov).** Piper (`en_GB-cori-high`, the model voice) read all 12 prompts. The audio went through
the real service and `summarise`, which is the worker's path. 85 of 86 target positions scored above 0 (median +4.05).
The exception is /l/ in *really* (p12): it scored −2.06 and was heard as /d/. The owner should listen to it. This only
shows that the canonical phones, alignment and target rules fit a clean model voice. It says nothing about thresholds or
learners' speech.

## 3.3b: the owner's labels and thresholds
**Labelling.** Only kept recordings can be labelled, because labelling needs the audio. The page says so and suggests
ticking "keep". Under "Xem điểm từng âm", a kept, analysed recording shows each target sound with three things:
- a play button for that sound's aligned segment, with 150 ms either side;
- the whole sentence;
- three buttons: **Đúng**, **Sai**, **Không chắc**.

The owner labels by ear: "is this the sound the sentence asks for?". The score is hidden while labelling, so it cannot
sway the label. Labels can be changed at any time.

**Storage.** Migration `0023` adds `speech_labels`: recording, target index, label (`right` | `wrong` | `unsure`) and
time. Deleting the recording deletes its labels.

**Routes.** All of them are for the owner's own recordings only:
- `GET /recordings/{id}/audio`: the WAV of a kept recording, `Cache-Control: no-store`. 404 if the recording is not
  kept or its audio was cleared.
- `POST /recordings/{id}/labels {labels: [{target, label}]}`: saves labels. 422 for a target index that is not in the
  analysis.
- `GET /recordings/{id}` also returns `labels`.

**Thresholds** (`app/pronunciation/thresholds.py`, pure and tested). Each threshold is chosen per sound group in
`sounds.yaml`.
1. **Split.** Recordings, not phones, are split into a *tune* half and a *check* half by a hash of the recording id, so
   one take's sounds never sit in both halves. The same prompt read on another day can land in either half. With 12
   prompts, a split by prompt would leave some sound groups with no examples in one half, so the check measures new
   takes of the same sentences, not new sentences. `unsure` labels are left out.
   Thresholds stay at or below 0. Below 0 the recogniser always heard a competing phone somewhere, so the check
   measures exactly the product's mark rule (3.4).
2. **Choose.** On the tune half, a sound is flagged when its GOP is below the threshold. The threshold chosen is the one
   that catches the most `wrong` labels while keeping the false-alarm share at 10% or less. The false-alarm share is
   flagged-but-right divided by flagged.
3. **Check.** On the check half, the report gives:
   - the false-alarm share, with a Wilson 95% interval;
   - recall;
   - the false-positive rate among `right` sounds.

**Verdict per group.**
- **`pass`**: the share is at most 10% and at least 10 sounds were flagged in the check half.
- **`fail`**: the share is above 10%.
- **`too_few`**: fewer flags than that, or no threshold could be chosen.

Only `pass` groups get marks in 3.4. The CLI writes `evals/baselines/pronunciation-thresholds.json`, which holds
metrics only and no audio:
`uv run python -m app.pronunciation.thresholds --out ../../evals/baselines/pronunciation-thresholds.json`

## Not in this step
Marks or colours, a learner-facing verdict, stress or intonation, other learners recording.
