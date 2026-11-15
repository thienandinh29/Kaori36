# Step 2.5: Task 1 (describe a chart)

Part of `specs/writing/`. A Task 1 prompt is a **chart built from data** (`curriculum/figures.py`), never a picture a model drew, so
the numbers a learner writes can be checked against the same data the chart is drawn from (`curriculum/facts.py`). Task 1 gets
no band (the scorer is Task 2 only, step 2.3), no mastery evidence from numbers, and no rewrites in this step.

## Prompts
- `data/writing/prompts.yaml`: a prompt with `task: 1`, `type: chart` carries a `figure` (a `ChartFigure`: line, bar, pie or table).
  A Task 1 prompt must have a figure; a Task 2 prompt must not. Authored by the project, `status: draft` until the owner reviews
  (draft prompts are listed for `DRAFT_ITEM_LEARNERS` only). Starter set: one line chart, one bar chart, one pie chart, one table,
  with invented data (no real survey, no past-paper figure).
- `GET /writing/prompts` and `GET /essays/{id}` return the figure; the web app draws it as plain SVG (no library, with the
  figure's own `alt_vi` for screen readers).

## Checks by code (`app/writing/task1.py`, pure; stored in `result.task1`)
1. **Numbers.** Every number the essay writes is looked up in what the chart can support: a data value (as written, or rounded),
   a category label (years), a difference between two values of one series, a pie share (one decimal or rounded), or a total.
   A number nothing supports is shown as **"không tìm thấy trong biểu đồ"**. This is a flag for the learner to re-read, not a
   verdict: the code does not understand sentences, so "a quarter" or "twice" are not checked, and a coincidence can pass.
2. **Key features.** For each series, the highest point, the lowest point and the overall change (pie: the largest share),
   from `chart_facts`. A feature counts as covered when the essay names the series and gives its value or its category.
   The page lists which key features were not mentioned.
3. **Overview.** Whether the essay contains an overview marker ("overall", "in general", "as a whole", "it is clear that", ...).
   Reported as present or absent; whether it is a good overview is the model's judgement, not code's.
4. Direction of change ("rose", "fell") is **not** checked by code: sentences are too varied. The model's feedback sees the facts.

## Feedback (model, task `writing_feedback`)
Same pipeline as Task 2 (exact quotes checked by code, the model never sees a band), with a Task 1 system prompt and the chart's
data table plus its facts in the user message. The four criteria are Task Achievement (key `tr`), Coherence and Cohesion, Lexical
Resource, Grammatical Range and Accuracy. The prompt tells the model that a number is correct only if it is in the data table.
No LLM corrections change; LanguageTool and ERRANT run as for Task 2.

## Not in this step
A band for Task 1; rewrites of Task 1 paragraphs (the rewrite could introduce wrong numbers; it answers 422 for Task 1 essays);
maps, processes and diagrams (the figure models exist; the checks would need their own facts); real exam charts.

## Acceptance
Pure tests on each check (numbers, rounding, years, differences, shares, features, overview); prompts load and validate; the worker
stores `task1` for a Task 1 essay and none for Task 2; the Task 1 feedback prompt contains the facts and not a band; rewrite 422;
web unit tests for the figure decoder and the SVG; a Playwright test writes a Task 1 essay and sees the chart and the number flag.
