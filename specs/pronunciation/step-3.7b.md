# Step 3.7b: say the word, guidance from repeated attempts and sounds to focus on (spec, plan, tasks)

Builds on step 3.7. The owner's requests (19 Nov 2026):
- show the word's IPA, coloured from red to green, instead of boxes of numbers;
- when the same sound stays wrong over attempts, show how to say it right;
- keep the sounds most often missed, so practice can focus on them.

## What the learner sees (owner, pronunciation service on)
- **The word's IPA**, each sound coloured red, amber or green by closeness (0–100, from GOP). A dropped sound is red
  and struck through. Tapping a sound shows its number, what was heard instead, and how to say it. Colour is never the
  only signal.
- **A guide when a sound stays low**: in 2 of the word's last 3 analysed attempts (closeness under 70, or dropped). It
  shows:
  - what was heard instead;
  - what to change, from the confusion's tip (for example /ɔː/ heard as /ɑː/: round the lips);
  - how to say the sound;
  - a minimal pair to listen to (caught / cart).
- **"Âm cần tập trung"** on `/phat-am`: across all words in the last 30 days, the sounds most often low. A sound must
  have been seen at least 3 times. Each shows its share, what it was usually heard as, how to say it, and an example
  word.

## Rules
- **Kept: the per-sound scores only, never the audio** (`say_attempts`, migration `0035`; a test checks that no audio
  column exists).
  - It is used for guidance and focus only, never as evidence: no mastery moves until the pronunciation gate.
  - The page calls the numbers an unverified estimate of closeness, not right or wrong.
  - "Under 70" is a practice threshold for choosing what to show, not a mark.
- **Tips are a draft** (`data/pronunciation/phone-tips.yaml`), written by the agent for Vietnamese learners of British
  English. They cover how to say each of the 46 sounds, 25 common confusions with minimal pairs, and dropped sounds.
  Each guide says "bản nháp, chưa được giáo viên duyệt" until a teacher reviews them; this is on `dolater.md`'s
  reviewer list.
- A tip exists for every sound the recogniser can return for the word list, and every confusion names known sounds.
  Tests check both.

## Routes
- `POST /vocab/say` now also returns, per phone, `closeness` and `how`, plus
  `guide: [{index, phone, times, of, heard, dropped, how, change, minimal}]`.
- `GET /vocab/say/focus?learner_id` returns `{days, attempts, sounds: [{phone, low, seen, share, heard, how,
  example}]}`.

## Tasks
- [x] T1 `closeness`, `repeated` and `focus` in `app/pronunciation/word.py` (pure); the tips file; `say_attempts`;
  the service and route changes.
- [x] T2 Web:
  - the coloured IPA with tap-for-details;
  - the guide card with minimal-pair voice buttons;
  - `components/pronunciation/say-focus.tsx` on `/phat-am`;
  - decoders and strings.
- [x] T3 Tests:
  - repeated: the window, a different sound sequence, dropped;
  - focus ranking and its minimum;
  - the tips file;
  - attempts kept without audio, guiding the third try;
  - Vitest;
  - Playwright: coloured IPA, tap detail, guide.
- [ ] T4 A teacher reviews `phone-tips.yaml` (with the `tip_vi` work already on `dolater.md`).

## Fix (20 Nov): one attempt per recording
The owner analysed the same recording twice and the guide counted it as two attempts ("2/2"), and a reply lost on
the way back and retried would count twice too. Each recording now gets a random id in the browser (`take`), sent with
every analysis of it; `say_attempts.take_id` (migration `0037`) is unique per learner, word and take, so analysing
the same recording again replaces its row instead of adding one. Requests without a take (older clients) still add a
row each. Tests: `test_analysing_the_same_recording_again_is_one_attempt`; Playwright checks a new id per recording
and the same id on "Phân tích lại".
