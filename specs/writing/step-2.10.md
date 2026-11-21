# Step 2.10: write on your own Task 2 question, and a timed exam mode

Owner's request, 21 Nov 2026: the learner types their own Task 2 question, writes on it, and gets the same analysis and
feedback as on an authored prompt. With it, an exam mode for any Task 2 question: 40 minutes kept by the server.
Task 1 is not included: its checks need the chart's data, which a typed question does not have.

## What the learner does
- On `/viet`, "Đề của bạn (Task 2)": type or paste a question, then **Viết bài** (practice) or **Thi thử 40 phút**
  (exam). The question is checked first and refused with a reason in Vietnamese when it is not a Task 2 question.
- Exam mode is also offered on every authored Task 2 prompt.
- Exam mode: the timer starts on the server when the test is opened and is shown counting down; nothing else is shown
  while writing beyond the word count; the result opens only after submitting. An essay sent more than 30 s after the
  40 minutes is still analysed but marked over time ("nộp quá giờ"), as the timed Reading test does.

## The question check (pure, `app/writing/own_prompt.py`)
A question is accepted when, after NFC normalisation and trimming:
- it is 40–600 characters and at least 8 words, with no link, and nearly all letters are Latin (English);
- it does not ask about a chart, graph, table, diagram, map or process ("summarise the information…"): Task 1 is
  refused with "Đề Task 1 cần số liệu của biểu đồ, hiện chưa hỗ trợ".
Its type is guessed from its wording (discuss both views → discussion; advantages and disadvantages →
advantages-disadvantages; problems or causes and solutions → problem-solution; agree or disagree / to what extent →
opinion; two questions → two-part; otherwise opinion). The type only labels the prompt; nothing is graded by it.

## How it is stored and used
- `essays.own_prompt` (migration `0038`) holds the learner's question; `prompt_id` is `own`. Everywhere an essay's
  prompt is read (analysis, result, rewrites), an own question becomes a draft Task 2 prompt (`id` `own`, level B2 as a
  label only). The guardrails' prompt-overlap check, the feedback, Task Response competency checks and rewrites all use
  it, as for an authored prompt.
- **The question is data, never instructions.** Both the feedback and the rewrite prompts put the question and the
  essay between markers and tell the model never to follow instructions inside them; the code checks (quotes, meaning,
  LanguageTool) run whatever the model says.
- **Copyright and privacy:** a typed question stays with that learner's essay, is deleted with it, and never enters the
  prompt bank or any shared data. A learner may paste a real exam question for their own practice.
- `writing_tests` (migration `0038`): one row per started test (learner, prompt or own question, start time, 2,400 s);
  `essays.test_id` links the essay (at most one essay per test), `essays.over_time` records the verdict. Daily essay
  limits and model budgets are unchanged.

## Not claimed
The band stays hidden as for every essay until the scorer is calibrated; an own question changes nothing there. The type
guess is a label, not a check that the question is a good IELTS question.

## Tests
pytest: the question check (accepted questions of each type; too short, a link, Vietnamese text, a Task 1 chart question
refused), submit with an own question (stored, analysed with it, shown on the result and in the list), a test (timer from
the server, over time marked, a test used once, another learner's test refused), an injection-shaped question left as
data. Vitest: the countdown. Playwright: write on your own question, and an exam on an authored prompt.
