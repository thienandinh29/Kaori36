# Plan: lesson player, phase B1

Two PRs. No new dependency, no migration, no model call.

| Part | Where | Notes |
|---|---|---|
| Word forms for the narration check | `apps/api/app/vocabulary/headwords.py` (`form_index`), `importer forms` → `data-sa/vocabulary/forms.yaml` | Every NGSL/NAWL headword (function words and the supplementary list included) with its level and inflected forms, from the official files already pinned in `sources.json` |
| Lesson format | `apps/api/app/lessons/model.py` | Lesson → scenes → actions (closed, discriminated by `do`), checkpoints, sources |
| Checks | `apps/api/app/lessons/checks.py` | Pure; every rule of the spec's "Checks by code" that does not need RAG; graded narration in `apps/api/app/lessons/graded.py` |
| Loading and serving | `apps/api/app/lessons/store.py`, `apps/api/app/api/lessons.py` | `GET /lessons`, `GET /lessons/{node}` (no answer keys), `POST /lessons/{node}/checkpoints` (graded by key, not evidence yet); sample and draft lessons only for `DRAFT_ITEM_LEARNERS` |
| Lessons | `data/lessons/english-ielts/*.yaml` | One **sample** lesson (present perfect or past simple), written by the agent to exercise the player, labelled "Bài mẫu" on the page, never shown to other learners |
| Player (PR 2) | `apps/web/app/hoc/[slug]`, `components/lesson/`, `lib/lesson/` | Pure playback reducer (idle, playing, paused), board (table, timeline, lines), example cards with spotlight, EN/VI subtitles with level defaults, the server voice, controls, checkpoints; "Học bài" on the milestone panel |
