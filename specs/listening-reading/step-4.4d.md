# Step 4.4d: shadowing, v1 (spec, plan, tasks)

Owner's request (19 Nov 2026): shadowing, and practising from a YouTube or podcast link. Evidence, as remembered (not
re-checked here): Hamada 2016 and 2019 (Japanese EFL learners) found shadowing improves listening, mostly sound and
word-boundary perception, most for lower and intermediate learners. Gains in speech are smaller and the studies are
small (Foote & McDonough 2017). So v1 is a practice tool: it does not measure or mark correctness.

## What the learner does (`/noi-duoi`, "Nói đuổi")
- **Câu mẫu.**
  - Pick a bank text; its shadowing sentences are shown one at a time.
  - Hear the model from the server voice, at normal or slow pace.
  - Record yourself, then play your take back to compare by ear.
  - Two timing measures from the audio alone: speech time with silence trimmed, and pauses of at least 0.25 s. The
    page compares your pace with the model's.
- **Video YouTube.**
  - Paste a link; the official embedded player (`youtube-nocookie.com`) plays it.
  - Set points A and B, loop A–B, play at 1, 0.75 or 0.5 speed, and record yourself.
  - Nothing is downloaded, which keeps within YouTube's terms.

## Rules
- **The voice stays on the device.** Recordings are made and played in the browser and never uploaded. There is no
  consent step or deletion rule because nothing is kept (`SPEC.md`: a voice is personal data). A test checks that
  nothing is posted.
- **No marks, no mastery.** The measures describe timing only, and the page says so. Shadowing writes no evidence:
  Sena praises only mastery, and nothing here is validated.
- **Sentences of their own.** Shadowing shows the sentence, so it never uses a dictation or gap sentence, which would
  give those answers away. Shadowing sentences have 5–25 words, no brackets, quotes, colons, semicolons or links, and
  there are up to 8 per text: 214 on the bank, at least one per text.
- **The voice is machine-made**, with flatter intonation than a person, and the page says so. Real speech comes from
  the learner's own videos, and later from VOA if the owner accepts its terms.

## Routes (API)
`GET /shadowing/texts`, `GET /shadowing/texts/{slug}` (sentences with their text). The audio comes through
`GET /listening/items/{id}/audio`, cached like Listening's. 503 without a voice; the YouTube tab works without one.

## Tasks
- [x] T1 `shadow_sentences` in `app/listening/items.py`; service and routes; API tests (never a dictation sentence,
  voice, 503).
- [x] T2 Web: the page and its two tabs; recording in the browser (`components/shadowing/recorder.tsx`); timing
  (`lib/shadowing/measure.ts`); YouTube link parsing and loop span (`lib/shadowing/youtube.ts`); strings; Vitest;
  Playwright (fake microphone with nothing posted; a stand-in YouTube player with loop and speed).
- [ ] T3 (after the recogniser decision) Podcasts: an episode link fetched by the server with guards and transcribed
  locally, then sentence-by-sentence shadowing and dictation marked "chưa kiểm chứng", never moving mastery.
- [ ] T4 (option) SHADOW-001, an N-of-1 experiment: shadowed against listened-only sentences, then dictation a week
  later.
