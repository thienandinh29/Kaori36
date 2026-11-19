# Step 4.3 (plan CP4): Reading practice (spec, plan, tasks)

Plan: `plan.md` (CP4). Built ahead of CP1 and CP2b on test data, like CP3: it serves nothing until real questions
exist and pass the rule below.

## What the learner does
`/doc` lists the texts that have questions ready. A text page shows the passage, then its questions one at a time,
grouped by type (True/False/Not Given, multiple choice, completion, headings). After each answer:
- right or wrong **from the key** (never a model), with the correct answer;
- the passage sentence(s) that decide it, highlighted.

The Vietnamese explanation from the deciding sentence is **cut from this step** (CP4b). It has to be generated and
checked like everything generated, and that needs the checker's daily budget. The highlighted sentence is the
explanation for now.

## Which questions are served
Validation spec: learner-facing content needs **Silver**. A question is served only when:
- it is `approved` (the reviewed bank);
- its `item_ok` labels are Silver or Gold with the value "right". Code checks plus the blind checker agreeing make
  Silver; a teacher makes Gold. The owner's own approval adds nothing, so an approved item the checker doubted stays
  out until a teacher says it is right;
- its passage is still the one it was written for, and it still passes the code checks.

## Evidence
Each item is tagged with one skill (detail, main idea, inference, writer's view, skimming). The plan's separate
`english-reading` course is not needed: the two-map design (`specs/two-layer-map/`) already has these five Reading
competencies. Each answer is one BKT observation on that competency, with the multiple-choice observation model.
Headings count as right only when every paragraph is right. Answers are logged in `reading_answers` (migration
`0031`).

The engine then sees Reading:
- "Hôm nay" counts a Reading competency as measured after 3 answers;
- Reading becomes an available skill (diagnostics and practice link to `/doc`) only while at least one question is
  served.

## Routes
- `GET /reading/texts?learner_id=`: texts with served questions (title, level features, count).
- `GET /reading/texts/{slug}?learner_id=`: the passage and its served questions in the learner's view (no key, no
  evidence).
- `POST /reading/items/{id}/answer`: grades from the key, stores the answer, moves the competency, and returns the
  result, the key as text, the evidence sentences and the trace.

## Tasks
- [x] T1 Migration `0031_reading_answers.sql`.
- [x] T2 `app/services/reading_practice.py`: the serving rule, texts, a text, answers with evidence; routes.
- [x] T3 `/today`: Reading evidence counts, and Reading is available while questions are served.
- [x] T4 Web `/doc` and `/doc/[slug]`, proxy rules, strings; Vitest; Playwright (the real API with no served
  questions; the flow on mocked calls).
- [x] T5 Tests on the database: the Silver rule (approved but doubted is not served; Gold makes it served), grading,
  evidence and the trace, other learners and bad ids.
