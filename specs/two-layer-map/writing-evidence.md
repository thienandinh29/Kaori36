# Writing evidence for the competency map (spec, plan, tasks)

Part of `spec.md` (layer 2, Writing: "code checks on each essay"). Without it, the "Hôm nay" list asks for a Writing
diagnostic and nothing an essay shows ever reaches the engine. This step closes that loop.

## What an essay gives
The worker already measures each essay: length, paragraphs, linking words by function, sentence length, grammar
errors (LanguageTool), sentence complexity, and for Task 1 the numbers, key features and overview checked against the
chart. Draft rules in `data/writing/competency-rules.yaml` turn these into checks per Writing competency:

| Competency | Checks |
|---|---|
| Task 1 (Task 1 essays only) | long enough; an overview; every number supported by the chart; at least half the key features |
| Task 2 response (Task 2 essays only) | long enough; at least 4 paragraphs; an opinion or concluding phrase |
| Coherence and cohesion | linking words from at least 3 functions; at least 3 paragraphs; average sentence 10–30 words |
| Lexical resource | at least 10% of words beyond the A1–B1 forms of NGSL/NAWL; long enough |
| Grammatical range and accuracy | at most 3 grammar errors per 100 words; at least 30% of sentences with more than one clause |

A check whose input is missing (no grammar check, no chart, no number in a Task 1 essay) gives nothing.

## One observation per competency per essay
A competency **passes for an essay when more than half of its checks pass**. That is one BKT observation, with a noisy
observation model (slip 0.25, guess 0.35). The first version updated once per check: one good essay took Coherence
from 0.23 to 0.80, which overstates what one essay shows. Every check is still logged with the estimate before and
after (`competency_observations`, migration `0030`), and "Vì sao?" lists them. A retried essay job counts nothing
twice.

Competencies are concepts of the subject `ielts-competencies`, so they use the same mastery table and traces. A
competency counts as **measured after 3 different essays**, and the engine then stops asking for its diagnostic.

## What this is not
These checks are what a script can see. They are **not band descriptors**: passing them all does not mean band 7, and
no band is shown. The rules are a **draft (Bronze)**, so they count only for the owners (`DRAFT_ITEM_LEARNERS`) until a
teacher or IELTS rater checks them against rated essays. The lexical bar in particular may be too high: the first real
essay had 5.3%. The band model's per-criterion outputs stay out until the phase 2 gate.

## Tasks
- [x] T1 `data/writing/competency-rules.yaml`, `app/writing/competency.py` (pure) with unit tests.
- [x] T2 Migration `0030`; `app/services/competency_evidence.py` (one update per competency per essay, logged,
  idempotent); wired into the essay worker for owners.
- [x] T3 `/today` reads competency estimates (measured after 3 essays).
- [x] T4 Tests: rules, the worker (owners only, once), and the loop (three essays with failing grammar: Writing
  grammar falls, the others rise, the list traces Writing grammar to a weak grammar foundation).
- [x] T5 A real run on the stack with LanguageTool; MAP and spec status.
