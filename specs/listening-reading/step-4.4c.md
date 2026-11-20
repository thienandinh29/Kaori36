# Step 4.4c — Listening to a whole passage (plan CP5b)

The second half of CP5: "the same approved items on audio". The server voice reads a whole Reading passage; the
learner answers that passage's served questions by ear, then reads the passage.

## What is served
- **Questions:** exactly the ones Reading serves (approved, `item_ok` Silver or Gold "right", passage unchanged, code
  checks passing), so their keys are already checked by code, the blind checker and the owner. Headings questions are
  left out: they need the paragraphs on screen. TRUE/FALSE/NOT GIVEN, multiple choice and completion stay, shown in
  the fixed shuffled order of step 4.3c.
- **Never the passage before submitting:** the page gets the questions and how many audio parts there are. The
  passage (as `transcript`) comes back only with the results.
- **Audio:** the voice takes at most 300 characters, so the passage is read sentence by sentence, a longer sentence
  cut at a semicolon, a comma, else between words (`app/listening/passages.py`, pure). Joined, the parts give every
  word of the passage in order (tested on all 30 bank texts). Each part is voiced on request and cached (128 parts
  in memory, a day in the browser); the browser loads the next part while one plays.
- **Plays:** at most twice per visit (IELTS plays once); kept by the page, not the server: this is practice.
- **Read before:** a passage whose Reading questions the learner answered is marked "bạn đã đọc bài này", since
  listening to it is easier.

## Evidence
One BKT observation per answered question: `detail` questions on `listening-detail`, every other skill on
`listening-main-idea`, with Reading's MCQ parameters (objective, a guess is possible). Kept in `listening_answers`
with kind `passage` (migration `0036` widens the kind check; nothing else changes). A blank is wrong in the score
but gives no evidence. Listening answers never count as Reading.

## Routes
`GET /listening/passages`, `GET /listening/passages/{slug}`, `GET /listening/passages/{slug}/audio/{n}?pace=`,
`POST /listening/passages/{slug}/submit {learner_id, answers}`; without the server voice the list says unavailable
and the rest answer 503. Web: "Nghe cả bài" on `/nghe`, the page `/nghe/bai/{slug}`.

## Measured (20 Nov, Piper `en_GB-cori-high`, the bank's 30 texts)
| | shortest (160 words) | median (737 words) | longest (895 words) |
|---|---|---|---|
| Parts | 6 | 35 | 45 |
| Audio | 0.9 min | 4.3 min | 5.4 min |
| WAV size | 2.4 MB | 11.3 MB | 14.3 MB |
| Time to voice it all | 9 s | 41 s | 53 s |
| First part | 1.9 s | 0.8 s | 1.5 s |

A part takes about a second to voice and several seconds to play, so with the next part fetched ahead playback does
not wait. Median parts per text: 35.5 (max 52).

## Not claimed
One synthetic British voice reading textbook prose is not IELTS Listening (dialogues, accents, forms). This trains
listening comprehension with trusted keys; exam-format audio is the next Listening step (own scripts, two voices,
the audio check of step 4.4a). The owner's CP5 decision: whether this voice is good enough to keep.

## Checks
pytest: every bank passage read whole in parts under the limit; long sentences cut; the competency map; the passage
never in the view; audio cached and out-of-range parts refused; answers move Listening (never Reading), blanks give no
evidence, foreign answers refused; without the voice nothing is offered. Vitest: the decoder refuses a view with the
passage or a headings question. Playwright: the parts play in order, the passage appears only after submitting.
