# Step 4.2f: faster review by passage (spec, plan, tasks)

Plan: `plan.md` (CP3). Builds on `step-4.2c.md`. The rule does not change: a question reaches a learner only when the
owner approved it and it is Silver (`step-4.3.md`). What changes is how long that approval takes. With about 260
questions waiting (19 Nov) and about 12 per new text, reviewing one question at a time, re-reading its passage each
time, would take the owner 2-3 hours per 30 texts.

## What the owner does
`/duyet-doc` opens on **Theo bài đọc** (by passage); the old status view stays as a second tab.
- A list of texts with questions waiting: title, how many the checker agreed with and how many it flagged.
- A text page: the passage once, its paragraphs numbered (headings questions refer to them), then its waiting
  questions in order: those the checker agreed with first, flagged ones after. For the current question:
  - its deciding sentences highlighted in the passage;
  - the question, the key, and the checker's answer next to the key when they differ ("Máy kiểm tra trả lời …");
  - **Duyệt** / **Loại** (a reason, then confirm) / **Bỏ qua** (skip to the next, no decision).
- **Keyboard:** `A` approve, `R` reject (then `1`-`5` choose the reason and `Enter` confirms), `S` or `→` skip,
  `←` back. Shortcuts are ignored while typing in the note field. The buttons show their key.
- After the last question of a text, the next text with questions waiting opens.

## Measured
Each decision sends the seconds the question was on screen (capped at 600), stored in the owner's label `detail`
(`{"seconds": n}`; no migration). `GET /reading/review/texts` also returns, over all the owner's decisions:
how many, the median seconds per decision, and how often the owner overturned the checker (approved a flagged
question, or rejected one it agreed with). This is the owner's own speed and agreement: Bronze, learner-side
feedback, never a correctness measure (the teacher's sample stays the gate, `step-v3.md`).

## Routes (owner only; 403 for anyone else)
- `GET /reading/review/texts?learner_id=` → `{texts: [{slug, title, agreed, flagged}], stats: {decisions,
  median_seconds, overturned}}`; only texts whose passage is unchanged, so every listed question can be approved.
- `GET /reading/review/texts/{slug}?learner_id=` → `{slug, title, passage, items: [...]}`: the waiting items in
  the order above, each as in the status queue (question, key, evidence, checker answer and model) plus
  `agreed: bool`.
- `POST /reading/review/{item_id}` takes an optional `seconds` (0-600) beside the decision.

## Tasks
- [x] T1 Service and routes: the text list with stats, a text's waiting items, `seconds` on a decision.
- [x] T2 Web: the by-passage view, shortcuts, auto-advance; decoder, client, proxy rules, strings.
- [x] T3 Tests: API (ordering, only current passages, seconds stored, stats, other learners refused), Vitest
  (decoder, shortcut mapping), Playwright (the real API's empty state; a mocked text reviewed with the keyboard).
