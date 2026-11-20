# Web handoff: redesigning the UI

For a new session (or person) who will redesign NodeTrail's web app. Read this first, then `CLAUDE.md`. The owner designs; the
agent builds what the owner decides. The backend is worked on in another session, so **stay inside `apps/web/`** (plus this
file) unless the owner says otherwise.

## What exists
Next.js App Router (`apps/web`), TypeScript strict, React 19, Tailwind 4, one shadcn-style `components/ui/button.tsx`,
`lucide-react` icons, React Flow + dagre for the knowledge map. Phone first: the browser tests run at Pixel 7 size.

| Route | Page | Main component(s) | API paths (every call is in `lib/english/client.ts`) |
|---|---|---|---|
| `/` | Today (home) | `english/home.tsx` | `vocab/session` |
| `/kiem-tra` | Level test | `english/level-test.tsx`, `question-card.tsx`, `feedback.tsx` | `level-tests`, `level-tests/{id}/answers` |
| `/lo-trinh` | Roadmap | `english/roadmap-view.tsx` | `roadmap`, `milestones/{slug}/tests` |
| `/on-tap/[kind]/[slug]` | A milestone test or grammar practice | `english/run-page.tsx`, `run-view.tsx` | `milestones/{slug}/tests`, `nodes/{slug}/practice`, `grammar-runs/{id}/answers` |
| `/tu-vung` | Vocabulary and saved phrases | `english/vocab-session.tsx`, `word-card.tsx`, `phrase-review.tsx` | `vocab/session`, `vocab/answers`, `phrases/session`, `phrases/answers` |
| `/viet` | Writing: pick a prompt, past essays | `english/writing-home.tsx` | `writing/prompts`, `essays` |
| `/viet/[prompt]` | Write an essay | `english/essay-editor.tsx`, `chart-figure.tsx` (Task 1) | `essays` (POST) |
| `/bai-viet/[id]` | Essay result | `english/essay-view.tsx`, `essay-feedback.tsx`, `self-correct.tsx`, `rewrite-panel.tsx`, `task1-checks.tsx` | `essays/{id}`, `.../corrections`, `.../rewrites`, `phrases` |
| `/gioi-thieu` | About | `english/about.tsx` | none |
| `/kham-pha` | The original any-subject explorer (contest) | `workspace.tsx`, `knowledge-map.tsx`, `trace-panel.tsx` | the non-English routes |

Every English page is wrapped in `english/shell.tsx` (header, brand with Sena, nav). Shared bits: `async-state.tsx` (loading
and error), `english/problem.tsx`, `english/trace-note.tsx` (the "Vì sao?" note). **Styles live in two places:**
`app/globals.css` (about 2,400 lines, mostly from the contest explorer) and `app/english.css` (about 700 lines, `en-*`
classes), with Tailwind utilities in some components. There is no shared design system yet; that is the main job.

## Rules the redesign must keep
1. **All UI text in Vietnamese, in `messages/vi.ts`** (`en.ts` is secondary). Never type a string into a component.
2. **TypeScript strict, no `any`.** Every API response is read through the strict decoders in `lib/english/decode.ts`
   (types in `lib/english/types.ts`); a changed shape must fail loudly, not render wrong.
3. **The browser only talks to `/api/backend/...`**, the same-origin proxy (`app/api/backend/[...path]/route.ts`), which
   allows a fixed list of paths. A new API call needs its path added there (and a test in `lib/server-proxy.test.ts`).
4. **Honesty rules from the product (do not design them away):**
   - No band is shown while the scorer is uncalibrated. When the API says "không chắc", show that, not a number.
   - The level test result is an estimate, never a score or grade.
   - Generated content keeps the label "Bản nháp tự động — chưa được giáo viên duyệt". AI corrections keep "gợi ý từ AI".
   - Feedback points show their quotes from the essay; nothing the API dropped is brought back.
   - Sena praises real mastery only: no streaks, timers or speed rewards.
5. **Accessibility:** keyboard reachable, visible focus, labels on inputs, colour never the only signal (right/wrong has
   text or an icon too), charts keep their `alt_vi` text.
6. **Learner identity:** one learner per browser, kept in `localStorage` (`lib/english/learner.ts`). There is no login.

## Running it
- Whole stack (from the repo root): `docker compose up -d --build --wait`, then open http://localhost:3000. Add
  `--profile writing` for the grammar checker (essay results need it). Your own learner sees draft items only if its id is in
  `DRAFT_ITEM_LEARNERS` in `.env` (the owner's file; never commit it).
- Fast UI work: `cd apps/web && npx pnpm@10.20.0 install && npx pnpm@10.20.0 dev` against the running API.
- Checks before every PR (the CI `web` job): `pnpm lint`, `pnpm typecheck`, `pnpm test` (Vitest), `pnpm format:check`.
- Browser tests (the CI `stack` job): with the stack running and `E2E_LEARNER_ID` set, `npx playwright test`. They find
  elements by role and Vietnamese text (`e2e/english.spec.ts`, `e2e/keys.ts`), so **renaming a button's text breaks them**:
  change the test with the text, in the same PR.

## How to work
- A branch per change (`feat/ui-...`), a PR into `main`, merged only when CI is green.
- Start with the design system (colours, type scale, spacing, card, button, form field, feedback states, Sena's place),
  as CSS variables or Tailwind theme tokens, then move pages onto it one PR at a time.
- Do not change API shapes or add routes from the web session; ask the backend session (via the owner) instead.
- New dependencies (a component library, a font) need the owner's yes first.
- Avoid editing `MAP.md` and `PLAN.md` while the backend session has a PR open that touches them; if
  both must, merge `main` into your branch before opening the PR.

## Coming soon from the backend
Reading practice (step 4.3): question types True/False/Not Given, multiple choice, completion and headings already exist in
the API code (`apps/api/app/reading/items.py`) without routes. The page will need a passage view, one question type at a
time, the answer key's verdict, and the deciding sentence highlighted.
