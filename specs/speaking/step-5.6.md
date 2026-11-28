# Step 5.6: SPK-001's feature extraction (the agent's part: the loader and the measures on its audio)

Spec: `spec.md` ("The band"); experiment: `research/experiments/SPK-001.yaml`. Owner's go-ahead: 28 Nov 2026 ("build 5.6").
**Split in two, and only the first is built here.** The experiment says the corpus licence is read in full and signed by the
owner **before** anything starts, and nothing is downloaded before that (`dolater.md`). So this step builds what needs no corpus:
a command that turns *any* manifest of recordings into one row of features per recording, with the code the app already uses.
It is tested on synthetic audio and run for real on synthetic speech. **No corpus is touched, none is read, and the corpus's own
file layout is unknown to us (only its abstract was read), so no corpus adapter is written.**

**Not built, and why:** the corpus adapter (needs the corpus's documentation, after the licence); the model, the evaluation and
the report (the owner's hands-on work: `PLAN.md`); the CEFR→IELTS range mapping (to be read on IELTS's own page first); and
**anything a learner sees**: the level appears on the result page only after the model passes QWK ≥ 0.75 on held-out speakers and
the owner's rated mocks agree (`spec.md`, "The band"). Nothing in this step changes the app.

## What it does
`python -m app.speaking.spk001 check MANIFEST` validates a manifest and counts it. `python -m app.speaking.spk001 extract
MANIFEST [--out …] [--asr-url …] [--no-language]` writes one JSON line per recording to `data/private/spk-001/features.jsonl`
(git-ignored), resumable: a finished id is skipped on the next run, a failed one is tried again.

**The manifest** is a CSV, one row per recording: `id`, `audio` (16 kHz mono 16-bit WAV; convert others first with
`ffmpeg -i in.mp3 -ar 16000 -ac 1 -c:a pcm_s16le out.wav`), `source` (`own` or `corpus`), and optionally `speaker`, `split`
(`train`/`dev`/`eval`), `test`, `part`, `score` (the human score, passed through untouched), `question`, `asked_seconds`, `words`
(a transcript JSON with word timings, which skips recognition).

**Per recording, the features** are exactly the numbers the app already makes, nothing new: from 5.2 (speech and articulation rate,
pauses per minute, long pauses, pauses between and inside clauses, the longest fluent run, fillers per 100 words, words, speaking
time, the share of the time asked) and from 5.3a (MTLD from 50 words, the share above B1, the unknown share, grammar hints per 100
words with a missing -s/-ed ending counted apart, the memorised-phrase and repeated-word shares). A number that cannot be measured
is `null`, never 0 (no grammar rate without LanguageTool; no vocabulary numbers under 15 s of speech).

## Rules
- **Held-out speakers are the premise:** a manifest in which a speaker is in two splits is refused.
- **The licence gate:** a manifest with `source=corpus` is refused unless `data/private/spk-001/LICENCE.txt` exists and is not empty
  (the owner writes it after reading the licence in full and answering its three questions). Output outside `data/private/` is
  refused for every source.
- **Recordings never leave the machine they are on**: recognition runs on the recognition service at the URL given (our own
  `asr/` service); nothing goes to a model provider. The corpus audio is never committed, copied into the repository or put in a
  notebook (that is the owner's open question (b)).
- A failed recording is a row with its reason; a recognition service that is down stops the run and everything done is kept.

## What is measured
Unit tests: the feature row (every field, `null` where unmeasured, endings apart from grammar), the manifest rules (each refusal,
the leaking speaker, the licence note, output outside `data/private/`), extraction (one row each, resume skips done ids, a bad
recording is a failed row and is redone, a refusal fails one row, a service that is down stops the run and keeps what was done,
a supplied transcript skips recognition, the command's checks). A run for real with the real recogniser, spaCy and the real word and
phrase lists on four **synthetic** clips. **Not measured:** anything about speakers or levels; how long 300 hours takes; LanguageTool
(not run here: its image cannot be built in this sandbox).

## Not claimed
That these features can predict a speaking level (that is the experiment); anything about the corpus.

## Tasks
- [x] T1 Features, manifest, extraction, command; tests
- [x] T2 Run for real on synthetic speech; docs
- [ ] T3 (after the owner's licence note) the corpus adapter: the corpus's metadata to this manifest
- [ ] T4 (owner) the model, the evaluation and the report; then the level on the result page only after the bar

## Built (28 Nov 2026)
- `app/speaking/spk001/` (`features.py`, `manifest.py`, `extract.py`, `__main__.py`); `app/speaking/language.py` gains `build_step`,
  which the worker now uses too (one place builds the language step); 16 tests in `tests/speaking/test_spk001.py`.
- **Run for real** (the recogniser Whisper small.en natively, spaCy, the real word and phrase lists, LanguageTool not configured) on
  four **synthetic** clips (espeak speech, 5 to 25 s): 4 rows in about 12 s, a second run skipped all four; the 25 s clip had MTLD
  34 over 67 words, the three shorter ones had no vocabulary numbers (under 15 s of speech, as in the app); `data/private` stayed
  out of git. These are plumbing numbers only.
