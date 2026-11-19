# Step 3.7: say the vocabulary word (spec, plan, tasks)

The owner's request (19 Nov 2026): on a word card, the learner says the word and gets feedback.

## What the learner does
On a vocabulary card's back (`/tu-vung`), **Nói từ này** records the learner saying the word, up to 5 s.
- **Everyone** plays the take back and compares it by ear with the model voice (the speaker buttons beside it). This
  stays in the browser: nothing is uploaded.
- **The owner, with the pronunciation service on**, can also press **Phân tích từng âm**, after one consent note. They
  then see each sound of the word with:
  - a raw closeness from 0 to 100 (from its GOP score);
  - "nghe giống …" when another sound competed;
  - "bỏ mất âm" when the sound was not said at all (the same rule as step 3.6b).
  - Nothing is marked right or wrong, and the page says so.

## Rules
- **The voice policy holds** (SPEC.md): analysis is for owners only until a privacy review, with consent `voice-v1`.
  The audio is analysed in memory and never stored: no row, no file, no 24-hour copy.
- **No marks and no mastery.** Thresholds wait for the pronunciation gate, so a word's sounds move nothing.
- **The sounds come from the word list's own IPA** (British, agreed with eSpeak where imported), converted to the
  recogniser's phones (`app/pronunciation/word.py`):
  - stress marks and slashes are dropped;
  - two-letter phones are kept whole;
  - e becomes ɛ, r becomes ɹ, g becomes ɡ, and ɪə becomes iə.
  - Every phone of the 2,682 words with IPA was checked against the pinned model's vocabulary (`vocab.json`, the
    SHA-256 in docker-compose). The test keeps that inventory.
  - A word without IPA says so and is not analysed.
- **The quality check is for a word:** at least 0.6 s of recording and 0.15 s of speech, against 1.0 s and 0.5 s for
  a sentence. Bad audio gets the usual advice.

## Routes
- `GET /vocab/say/status?learner_id` returns `{analysis, owner, consent}`.
- `POST /vocab/say?learner_id&word=<lemma:pos>&consent` takes `audio/wav` (16 kHz mono) and returns
  `{ok, problems, ipa, phones: [{phone, gop, heard, dropped}], heard}`.

## Tasks
- [x] T1 `app/pronunciation/word.py` (IPA to phones, per-phone output); `quality.check` with word minimums;
  `app/services/word_say.py`, `app/api/word_say.py`.
- [x] T2 Web: `components/english/say-word.tsx` on the word card, `lib/english/say-word.ts`, proxy rules (600 KB, the
  `word` parameter), strings.
- [x] T3 Tests:
  - IPA cases and the inventory against the recogniser;
  - per-phone output;
  - owner-only, consent, service off, unknown word;
  - bad audio and a refused alignment;
  - Vitest decoders;
  - Playwright: a fake microphone, take, consent, analysis (mocked), and by ear only for a learner who is not the
    owner.
- [ ] T4 (the owner) Try it with the `pronunciation` profile on. The real service was not run in the build
  environment for lack of disk.
