# Step 4.4a: the audio check for synthetic Listening (spec, plan, tasks)

Plan: `plan.md` (CP5). Source: the Listening sources study (`docs/v2/listening-sources.md`, 19 Nov). A 15-turn Part 1
call voiced by Piper and transcribed by Whisper small.en lost one digit of the phone number: **an answer present in
the script is not always recoverable from the audio.** A Listening question whose answer cannot be heard must never
reach a learner. This step builds the check itself, pure and tested; wiring it into a generation pipeline waits for
the owner's choice of source (own scripts or recordings), and it applies to any synthetic audio either way.

## The rule
Each answer is a span of one script line (the Reading rule: the answer appears in the script word for word). That line
is voiced and transcribed. The answer is **recovered** when its normalised words appear, in order and contiguous, in
the normalised transcript of its line. Not recovered: that line is synthesised again more slowly and checked again;
still not recovered after the second attempt: the item is dropped (`MAX_ATTEMPTS = 2`). An answer not found in its
script is a generation fault, reported, never "recovered".

## Normalisation (both sides, the same function)
NFC, lower case, punctuation removed, then:
- **Numbers as digits:** "eleven", "twenty-one", "three hundred and five" → 11, 21, 305; ordinals ("fifth", "5th") → 5;
  "double four" → 44, "triple 0" → 000; "oh"/"nought" are 0 only next to another digit.
- **Digit runs joined:** consecutive digit groups become one token, so "oh seven seven, double four" and "077 44" both
  read 07744, and "eleven thirty" and "11.30" both read 1130. A lost or extra digit therefore fails, as it should.
- **Money and percent:** "£8.50" → 8 pounds 50; "10%" and "ten percent" → 10 per cent.
- **Spelled words:** three or more single letters in a row are joined ("H, E, N, D…" and "H-E-N-D…" → henderson).

**Known limits** (not handled; such answers fail safe, i.e. the line is re-voiced or the item dropped, never served
wrongly): dates in a different order ("5 May" vs "May 5"), "a hundred", decimals other than money, homophones the
recogniser may choose ("two" vs "too" is fine as a digit only next to other digits), and spelling of names the
recogniser writes differently. A false "not recovered" costs an item; a false "recovered" would serve an unhearable
answer, so every rule errs towards "not recovered".

## Tasks
- [x] T1 `apps/api/app/listening/audio_check.py`: `normalise`, `recovered`, `check` (per answer: its line and
  `recovered`, `not_heard` or `not_in_script`), `decide` (lines to re-voice slower, answers dropped).
- [x] T2 Tests: the study's dialogue with a constructed Whisper-style transcript (the phone number with a lost digit
  fails; prices, times, the spelled name, the discount pass), number words, digit runs, "oh" only next to digits, an
  answer missing from the script, the retry decision.
- [ ] T3 (CP5, after the owner's source decision) The generation pipeline calls it after synthesis, slower pace through
  Piper's `length_scale`, the outcome recorded per item.
