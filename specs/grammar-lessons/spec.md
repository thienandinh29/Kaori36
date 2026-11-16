# Spec: a lesson before the exercises and the test (grammar map)

The owner's request (16 Nov 2026): on the grammar map, "a teacher teaches me first, then gives me exercises and a test".
Each step should open with an introduction: what the grammar is, **why and when you need it**, then how it works.
Document only: nothing is built until the owner decides the points at the end.

## What exists now
The map has 10 milestones with 19 hidden nodes under them (`data/courses/english-ielts.yaml`), 76 authored questions
(`data/items/english-ielts.yaml`) and a Vietnamese explanation per misconception (`data/items/misconceptions.vi.yaml`).
A learner can take a milestone test at once ("test to unlock"); explanations appear only after a wrong answer.
There is no teaching before the first question.

## The lesson (one per hidden node, a short overview per milestone)
Shown in Vietnamese, with English examples, about 2–3 minutes of reading:
1. **Vì sao cần học?** One or two sentences: what this grammar lets you say that you could not say before, and where
   it matters in IELTS. For example, conditionals type 2 are for imagining and proposing in Writing Task 2 ("If
   governments invested more…") and for hypotheticals in Speaking Part 3.
2. **Khi nào dùng?** The uses, each with one short example and its Vietnamese meaning.
3. **Công thức.** The form as a small table (positive, negative, question), with time words where they help
   (already, yet, since, for…).
4. **So với tiếng Việt.** Where Vietnamese works differently, which is why learners slip (no verb endings, no articles,
   tense shown by time words). Each point links to the misconceptions that the questions already name, so the
   lesson warns about exactly the mistakes the test checks.
5. **Ví dụ.** 3–4 sentences, with listen buttons (the Piper voice), each with a Vietnamese translation.
6. **Tự kiểm tra nhanh.** 2 worked examples: a question, then the answer with the reason. They are read, not
   graded.

A milestone gets a shorter overview: what its parts are, why they belong together, and the IELTS use.

## Order on the map
For a milestone or part the learner has not started: **Bài học → Luyện tập → Kiểm tra**. The panel opens on the
lesson; "Tôi đã biết, kiểm tra luôn" remains, so a learner who already knows the grammar is not forced through it
(the "test to unlock" rule stays). After a wrong answer, the explanation links back to the matching section of the
lesson.

## Rules the engine keeps
- **Reading is not evidence.** Opening a lesson never changes mastery (BKT) and never unlocks anything: only answers
  do. Sena does not praise reading, only mastery. The app records "lesson seen" only so the owner can measure
  whether lessons help (below).
- **No lesson sentence is a test sentence.** Code checks that no example or worked example repeats a question's
  sentence or gives its answer, so reading the lesson does not leak the test.

## Where the content comes from
- **Now: authored drafts.** `data/lessons/english-ielts.yaml` (CC BY-NC-SA, like the items), drafted by the agent
  and labelled "Bản nháp — chưa được giáo viên duyệt" until the owner reviews each lesson. This is the same route as
  the items and misconception explanations; the grammar facts are basic and checkable.
- **Later: cited.** Once a grammar source's licence is verified (`wikibooks-grammar` or an open ESL textbook in
  `data/sources/english-candidates.yaml`), each lesson cites its source, through the same chunk citations as step 1.3b.
- **Checked by code:** every hidden node and milestone has a lesson; required sections are present and within
  length; misconception references exist; each example contains the form the lesson teaches (a declared target
  phrase); Vietnamese is NFC; no overlap with question sentences.

## API and web
- `GET /lessons/{slug}?course=english-ielts` returns the lesson and whether this learner has seen it;
  `POST /lessons/{slug}/seen` records it (a new table `lesson_views`, migration 0021, additive).
- The web: a lesson page `/hoc/{slug}` with sections, listen buttons and the worked examples behind "Xem đáp án";
  the milestone panel gets "Học bài" first; the explanation after a wrong answer gets "Xem lại bài học".

## How we know it helps (measured, not assumed)
For the owner's own use, then testers: first-try accuracy on a node's questions, **with versus without** the lesson
seen, and the number of remediation loops per node. Reported with intervals once there are enough answers. Too few
learners for a fair comparison is said plainly, not hidden.

## Size
19 node lessons plus 10 milestone overviews. Writing and checking the drafts takes one PR; API and web take a
second PR. No model calls at run time.

## Decisions for the owner
- [ ] Lesson first but skippable ("Tôi đã biết, kiểm tra luôn") **(recommended)**, or required before the test
- [ ] Authored drafts now, citations once a grammar source is verified **(recommended)**, or wait for a verified
  source
- [ ] Lesson length: short, about 2–3 minutes **(recommended)**, or longer with more examples
