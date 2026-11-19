# Step 3.7c — "Nói từ này" that works every time, faster

A fix inside step 3.7/3.7b (no new route, field or module). The owner reported that the word analysis
"sometimes works, sometimes not, and is a bit long".

## What was measured (19 Nov)

80 random words from the list, each voiced by the native British Piper voice (cori) in three takes:
`tight` (0.05 s of room around the word), `normal` (0.4 s) and `slowtap` (1.6 s before, 0.8 s after,
like a learner who waits after tapping). Every take went through `WordSay.say` and the real
pronunciation service (pinned model). Scripts in the session scratchpad; the voice is clean and
native, so every sound shown as low is a false alarm.

| | before | after |
|---|---|---|
| Analysed (of 240) | 237: 2 "too quiet" (slowtap), 1 "too short" (tight) | 240 |
| Sounds shown low on the native voice | 283 of 1,344 (21%) | 158 of 1,353 (12%) |
| First call after the service starts | about 5 s | warmed up before serving |
| Later calls (median) | 0.2 s | 0.2 s |

## Causes and fixes

1. **Silence judged as part of the word.** Loudness was the 90th-percentile frame of the whole take,
   so a long wait made a word "too quiet", and the 0.6 s minimum refused a word said quickly. Now
   the silence before and after the speech is cut first (`quality.trim`: frames 30 dB under the
   loudest, 0.25 s margin kept), the minimum length (0.3 s) applies to what is left, and the clip is
   padded with silence to 1 s for the aligner (`quality.pad`).
2. **A cold model.** The first inference initialises the runtime (about 5 s). The service now runs
   one inference on a second of silence before it starts serving (`warm_up`).
3. **Notation, not pronunciation.** The recogniser writes five British vowels with its own symbols:
   on the native voice /ɒ/ was heard as ɔ (24 of 24 low), /ɔː/ as oː (18/18), /əʊ/ as oʊ (15/15),
   /ɑː/ as a or aː, /eə/ as ɛ. These sounds are now sent to the aligner as the model's symbols
   (`MODEL_FORM`, all in the pinned vocab) and shown with the dictionary's (what was heard is
   mapped back). After the fix: /ɔː/ 2 of 18 low.
4. **Native variants.** A weak schwa heard as ɐ, ɪ or ɨ, or dropped, is normal speech, as are a few
   other weak variants (`ACCEPTED`): shown close (85), never dropped. Real confusions (/ɪ/–/iː/,
   /æ/–/ɛ/, /ɔː/–/ɑː/, th) are never in that list.
5. **What the recogniser cannot tell.** English /b d ɡ/ are often voiceless unaspirated, which this
   model hears as p t k (low in 13/30, 25/51, 15/27 on the native voice, mostly inside words), and
   the Southern British /uː/ is fronted, heard as iː (10/21). Those readings are shown as unsure
   (70, amber), are not counted low, and give no guide. A learner's real error of that kind is hidden
   too: the price of no false alarms until Gold labels measure the detector (`UNSURE`).
6. **One tap less.** Once the owner has agreed, a take is analysed as soon as it stops; agreeing
   analyses the current take; the button then reads "Phân tích lại".

## Not changed

No marks and no mastery: closeness stays a raw reading (step 3.7). The remaining false alarms (12%:
/ə/ heard as a or ɛ, /ɪ/ as eɪ or ɛ, /m/ as n) stay visible; tuning more on one synthetic voice would
fit the benchmark, not learners. The trimmed audio is never stored. Attempts saved before this step
have no `closeness` field; guidance computes it from the GOP as before.

## Checks

`tests/pronunciation/test_word_say.py` (model symbols and back, accepted variants, unsure readings,
trimming and padding, guidance with model symbols on the database); `pronunciation/tests/test_server.py`
(warm-up); `apps/web/e2e/say-word.spec.ts` (consent analyses the take; the next take is analysed on
stop).
